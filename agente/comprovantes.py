"""
comprovantes.py — Processamento de comprovantes de pagamento via OCR.

Fluxo:
    1. Baixa anexo (imagem/PDF) via baixar_anexo()
    2. Extrai texto via OCR (Tesseract). PDF -> pdf2image -> Image -> pytesseract.
    3. Procura valor (R$ XXX,XX) e data (DD/MM/AAAA) no texto extraido.
    4. Compara com o valor esperado do boleto (tolerancia 1%).
    5. Move arquivo pra /data/comprovantes/{telefone}/{timestamp}_{nome}.{ext}
    6. Registra resultado no SQLite.

Importacao de pytesseract/PIL/pdf2image e LAZY — se nao tiver instalado,
validar_comprovante retorna {"valido": False, "motivo": "ocr_indisponivel"}
e a aplicacao segue funcionando (escala pra humano).
"""

from __future__ import annotations

import os
import re
import shutil
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import requests
from loguru import logger


# ============================================================
# Util
# ============================================================
def _normalize(texto: str) -> str:
    if not texto:
        return ""
    t = unicodedata.normalize("NFKD", texto)
    t = "".join(c for c in t if not unicodedata.combining(c))
    return t.lower()


def _extensao_da_url(url: str, content_type: Optional[str] = None) -> str:
    """Detecta extensao a partir da URL ou do content-type."""
    try:
        path = urlparse(url).path
        ext = Path(path).suffix.lower()
        if ext in (".pdf", ".jpg", ".jpeg", ".png", ".webp"):
            return ext
    except Exception:
        pass

    if content_type:
        ct = content_type.lower()
        if "pdf" in ct:
            return ".pdf"
        if "png" in ct:
            return ".png"
        if "webp" in ct:
            return ".webp"
        if "jpeg" in ct or "jpg" in ct:
            return ".jpg"

    return ".bin"


# ============================================================
# Download
# ============================================================
def baixar_anexo(url: str, destino: Path) -> Path:
    """
    Baixa arquivo da URL pra destino. Cria pastas se preciso.

    Returns:
        Path do arquivo baixado (pode ter extensao corrigida pelo content-type).
    """
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)

    logger.info(f"[comprovantes] baixando {url} -> {destino}")
    r = requests.get(url, timeout=60, stream=True)
    r.raise_for_status()

    # Se a extensao do destino esta como .bin, tenta corrigir pelo content-type
    if destino.suffix.lower() == ".bin":
        ct = r.headers.get("Content-Type", "")
        ext = _extensao_da_url(url, ct)
        destino = destino.with_suffix(ext)

    with open(destino, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)

    logger.success(f"[comprovantes] baixado: {destino} ({destino.stat().st_size} bytes)")
    return destino


# ============================================================
# OCR
# ============================================================
def _ocr_imagem(path: Path) -> str:
    """OCR de imagem unica. Retorna texto bruto. Lanca excecao se OCR indisponivel."""
    import pytesseract  # noqa
    from PIL import Image  # noqa

    # Permite override do binario do Tesseract via .env (util no Windows)
    tess_cmd = os.getenv("TESSERACT_CMD")
    if tess_cmd:
        pytesseract.pytesseract.tesseract_cmd = tess_cmd

    img = Image.open(path)
    # PT-BR + ENG (fallback caso o pacote por-traineddata nao esteja instalado)
    try:
        return pytesseract.image_to_string(img, lang="por+eng")
    except Exception:
        return pytesseract.image_to_string(img)


def _ocr_pdf(path: Path) -> str:
    """OCR de PDF — converte cada pagina em imagem e roda OCR."""
    from pdf2image import convert_from_path  # noqa

    paginas = convert_from_path(str(path), dpi=200)
    textos = []
    for i, pagina in enumerate(paginas):
        tmp_path = path.with_name(f"{path.stem}_pg{i}.png")
        try:
            pagina.save(tmp_path, "PNG")
            textos.append(_ocr_imagem(tmp_path))
        finally:
            try:
                tmp_path.unlink()
            except Exception:
                pass
    return "\n\n".join(textos)


def _ocr_extrair_texto(arquivo: Path) -> str:
    """Roteia pro OCR correto baseado na extensao."""
    ext = arquivo.suffix.lower()
    if ext == ".pdf":
        return _ocr_pdf(arquivo)
    return _ocr_imagem(arquivo)


# ============================================================
# Parsers
# ============================================================
# R$ 1.234,56   |   R$1234,56   |   RS 850,00
_RE_VALOR = re.compile(
    r"(?:R\$|RS|reais?)\s*([0-9]{1,3}(?:\.[0-9]{3})*(?:,[0-9]{2}))",
    re.IGNORECASE,
)
# Fallback: numeros isolados com virgula
_RE_VALOR_FALLBACK = re.compile(r"\b([0-9]{1,3}(?:\.[0-9]{3})*,[0-9]{2})\b")
_RE_DATA = re.compile(r"\b(\d{2}/\d{2}/\d{2,4})\b")


def _parse_valor(texto: str) -> Optional[float]:
    """Extrai primeiro valor monetario do texto. Retorna float ou None."""
    if not texto:
        return None

    for regex in (_RE_VALOR, _RE_VALOR_FALLBACK):
        m = regex.search(texto)
        if m:
            raw = m.group(1)
            # "1.234,56" -> 1234.56
            try:
                return float(raw.replace(".", "").replace(",", "."))
            except ValueError:
                continue
    return None


def _parse_data(texto: str) -> Optional[str]:
    """Extrai primeira data DD/MM/AAAA do texto."""
    if not texto:
        return None
    m = _RE_DATA.search(texto)
    return m.group(1) if m else None


# ============================================================
# Validacao
# ============================================================
def validar_comprovante(arquivo: Path, boleto_esperado: dict) -> dict:
    """
    Roda OCR e valida se o comprovante bate com o boleto esperado.

    Args:
        arquivo: Path do PDF/imagem ja baixado
        boleto_esperado: dict com chaves esperadas:
            { "valor": float, "vencimento": str, "tolerancia": float (opcional) }

    Returns:
        {
            "valido": bool,
            "valor_extraido": float | None,
            "data_extraida": str | None,
            "motivo": str,         # explicacao curta (sucesso ou falha)
            "raw_text": str,       # primeiros 2000 chars do OCR
        }
    """
    arquivo = Path(arquivo)
    resultado = {
        "valido": False,
        "valor_extraido": None,
        "data_extraida": None,
        "motivo": "",
        "raw_text": "",
    }

    if not arquivo.exists():
        resultado["motivo"] = "arquivo_nao_encontrado"
        return resultado

    # 1. OCR
    try:
        raw = _ocr_extrair_texto(arquivo)
    except ImportError as e:
        logger.warning(f"[comprovantes] OCR indisponivel ({e}) — pulando validacao")
        resultado["motivo"] = "ocr_indisponivel"
        return resultado
    except Exception as e:
        logger.exception(f"[comprovantes] erro OCR: {e}")
        resultado["motivo"] = f"erro_ocr: {e}"
        return resultado

    resultado["raw_text"] = (raw or "")[:2000]

    if not raw or not raw.strip():
        resultado["motivo"] = "ocr_sem_texto"
        return resultado

    # 2. Parse valor + data
    valor_extraido = _parse_valor(raw)
    data_extraida = _parse_data(raw)
    resultado["valor_extraido"] = valor_extraido
    resultado["data_extraida"] = data_extraida

    if valor_extraido is None:
        resultado["motivo"] = "valor_nao_encontrado_no_comprovante"
        return resultado

    # 3. Compara com boleto
    valor_esperado = boleto_esperado.get("valor")
    if valor_esperado is None:
        # Sem valor de referencia — nao da pra validar, mas confirma que e comprovante
        resultado["motivo"] = "sem_boleto_referencia_mas_ocr_ok"
        resultado["valido"] = False
        return resultado

    try:
        valor_esperado = float(valor_esperado)
    except Exception:
        resultado["motivo"] = "valor_esperado_invalido"
        return resultado

    tolerancia = float(boleto_esperado.get("tolerancia", 0.01))  # 1% default
    delta = abs(valor_extraido - valor_esperado) / max(valor_esperado, 0.01)

    if delta <= tolerancia:
        resultado["valido"] = True
        resultado["motivo"] = (
            f"valor_bate (extraido=R${valor_extraido:.2f} "
            f"esperado=R${valor_esperado:.2f} delta={delta * 100:.2f}%)"
        )
    else:
        resultado["motivo"] = (
            f"valor_divergente (extraido=R${valor_extraido:.2f} "
            f"esperado=R${valor_esperado:.2f} delta={delta * 100:.2f}%)"
        )

    return resultado


# ============================================================
# Persistencia (mover + registrar)
# ============================================================
def salvar_evidencia(
    arquivo: Path,
    telefone: str,
    intent: str,
    validacao: dict,
    base_dir: Optional[str] = None,
    state=None,
    boleto_id_associado: Optional[str] = None,
) -> Path:
    """
    Move o arquivo pra /data/comprovantes/{telefone}/{timestamp}_{nome}.{ext}
    e registra no SQLite (se state for passado).

    Returns:
        Path final do arquivo (depois do move).
    """
    arquivo = Path(arquivo)
    base = Path(base_dir or os.getenv("COMPROVANTES_DIR", "/data/comprovantes"))
    pasta = base / re.sub(r"\D", "", telefone or "desconhecido")
    pasta.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    nome_seguro = re.sub(r"[^a-zA-Z0-9._-]", "_", arquivo.name)
    destino = pasta / f"{ts}_{nome_seguro}"

    try:
        shutil.move(str(arquivo), str(destino))
    except Exception as e:
        logger.error(f"[comprovantes] erro movendo arquivo: {e} — copiando")
        try:
            shutil.copy2(str(arquivo), str(destino))
        except Exception as e2:
            logger.error(f"[comprovantes] copia tambem falhou: {e2}")
            destino = arquivo  # fallback: mantem na origem

    # Registra no SQLite
    if state is not None:
        try:
            state.registrar_comprovante(
                telefone=telefone,
                arquivo=str(destino),
                intent=intent,
                valido=bool(validacao.get("valido")),
                valor_extraido=validacao.get("valor_extraido"),
                data_extraida=validacao.get("data_extraida"),
                boleto_id_associado=boleto_id_associado,
                raw_text=validacao.get("raw_text", ""),
            )
        except Exception as e:
            logger.exception(f"[comprovantes] erro registrando no SQLite: {e}")

    logger.success(f"[comprovantes] evidencia salva: {destino} (valido={validacao.get('valido')})")
    return destino


# ─── Test rapido ───
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Uso: python -m agente.comprovantes <arquivo> <valor_esperado>")
        sys.exit(1)

    arq = Path(sys.argv[1])
    valor = float(sys.argv[2])
    r = validar_comprovante(arq, {"valor": valor})
    print(f"\nResultado:\n  valido: {r['valido']}\n  valor_extraido: {r['valor_extraido']}")
    print(f"  data_extraida: {r['data_extraida']}\n  motivo: {r['motivo']}")
    print(f"\n--- OCR raw ---\n{r['raw_text'][:500]}")
