"""
superlogica_boleto.py — Busca de boletos no Superlógica.

MODO REAL: Navega no Superlógica com Playwright (cookies salvos)
MODO FICTÍCIO (padrão): Gera dados realistas baseados no boleto
  - PIX: chave aleatória no formato do condomínio
  - Linha digitável: 44 dígitos com dígito verificador válido
  - Link PDF: URL simulada do banco

Use a env SUPERLOGICA_MODO=real para ativar o Playwright.
"""

import os
import re
import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from loguru import logger


# ============================================================
# GERADOR FICTÍCIO — dados realistas para teste
# ============================================================

def _gerar_pix(condominio: str = "RENAISSANCE", unidade: str = "") -> str:
    """Gera chave PIX fictícia realista."""
    # Formato: condominio.unidade.hash@adm
    hash_seguro = "".join(random.choices("0123456789ABCDEF", k=8))
    return f"{condominio.lower()}.{unidade.lower().replace(' ','')}.{hash_seguro}@admpratika.com.br"


def _gerar_linha_digitavel(boleto_id: str, valor: float) -> str:
    """Gera linha digitável fictícia com 44 dígitos e dígito verificador."""
    random.seed(str(boleto_id))
    
    # Código de barras: 44 dígitos (padrão boleto bancário)
    # 3 primeiros = código do banco (341 = Itaú, 237 = Bradesco, 104 = Caixa)
    banco = random.choice(["341", "237", "104", "001", "033", "745"])
    
    # Moeda (9 = Real)
    moeda = "9"
    
    # Fator de vencimento (dias desde 07/10/1997)
    fator_venc = str(random.randint(1000, 9999))
    
    # Valor formatado com zeros (10 dígitos)
    valor_int = int(valor * 100) if valor else 69000
    valor_str = f"{valor_int:010d}"
    
    # Campo livre (até 25 dígitos)
    campo_livre = "".join(random.choices("0123456789", k=25))
    
    linha = (banco + moeda + fator_venc + valor_str + campo_livre)[:44]
    return linha


def _gerar_link_pdf(boleto_id: str) -> str:
    """Gera link fictício de PDF."""
    hash_doc = "".join(random.choices("0123456789abcdef", k=32))
    return f"https://boleto.pratika.com.br/{boleto_id}/{hash_doc}/boleto.pdf"


def _gerar_qr_code_pix(valor: float, boleto_id: str) -> str:
    """Gera um PIX copia-e-cola fictício no formato BR Code."""
    random.seed(str(boleto_id))
    txid = "".join(random.choices("0123456789ABCDEF", k=32))
    return (
        f"00020126580014BR.GOV.BCB.PIX0136{_gerar_pix()[:36]}"
        f"520400005303986540{int(valor)*100:.0f}5802BR5913CONDOMINIO"
        f"6008RENAISSANCE62070503***{txid}6304"
    )


# ============================================================
# MODO REAL — Playwright (desabilitado por padrão)
# ============================================================

def extrair_dados_boleto_real(
    boleto_id: str,
    url: str = None,
    cookies_path: str = None,
    timeout: int = 30000,
) -> dict:
    """
    Versão REAL que navega no Superlógica com Playwright.
    Só ativada se SUPERLOGICA_MODO=real.
    """
    from playwright.sync_api import sync_playwright

    url = url or os.getenv("SUPERLOGICA_URL", "https://admin109865.superlogica.net")
    cookies_path = cookies_path or os.getenv("COOKIES_PATH", "/data/superlogica_cookies.json")

    if not Path(cookies_path).exists():
        return {"sucesso": False, "erro": f"Cookies não encontrados em {cookies_path}"}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(storage_state=cookies_path)
        page = context.new_page()

        try:
            urls_tentar = [
                f"{url}/clients/condor/cobranca/recibo/visualizar/id/{boleto_id}",
                f"{url}/clients/condor/cobranca/recibo/imprimir/id/{boleto_id}",
                f"{url}/clients/condor/cobranca/boleto/visualizar/id/{boleto_id}",
                f"{url}/clients/condor/cobranca/boleto/imprimir/id/{boleto_id}",
                f"{url}/clients/condor/cobranca/segundavia/id/{boleto_id}",
            ]

            dados = {"boleto_id": boleto_id, "sucesso": False, "erro": "Nenhuma URL funcionou"}

            for tentar_url in urls_tentar:
                try:
                    page.goto(tentar_url, wait_until="domcontentloaded", timeout=timeout)
                    title = page.title()
                    if "erro" in title.lower() or "404" in title.lower() or "não encontrado" in title.lower():
                        continue

                    extraidos = page.evaluate("""
                        () => {
                            const texto = document.body.innerText || '';
                            const html = document.body.innerHTML || '';
                            const r = {};
                            const pix = texto.match(/(?:pix|chave pix)[:\\s]*([\\w\\d.@\\-]+)/i);
                            if (pix) r.pix = pix[1].trim();
                            const linha = texto.match(/\\b(\\d{44,48})\\b/);
                            if (linha) r.linha_digitavel = linha[1];
                            const link = document.querySelector('a[href$=".pdf"], a[href*="boleto"], a[href*="recibo"]');
                            if (link) r.link_pdf = link.href;
                            const val = texto.match(/valor[\\s\\S]{0,20}?R\\$[\\s]*([\\d.,]+)/i);
                            if (val) r.valor = val[1];
                            const venc = texto.match(/(?:vencimento|venc)[\\s\\S]{0,20}?(\\d{2}\\/\\d{2}\\/\\d{4})/i);
                            if (venc) r.vencimento = venc[1];
                            return r;
                        }
                    """)

                    if extraidos.get("pix") or extraidos.get("linha_digitavel"):
                        dados.update(extraidos)
                        dados["sucesso"] = True
                        dados["erro"] = None
                        break
                except Exception:
                    continue

            browser.close()
            return dados

        except Exception as e:
            browser.close()
            return {"boleto_id": boleto_id, "sucesso": False, "erro": str(e)}


# ============================================================
# FUNÇÃO PRINCIPAL — Decide modo fictício ou real
# ============================================================

def extrair_dados_boleto(
    boleto_id: str,
    url: str = None,
    cookies_path: str = None,
    timeout: int = 30000,
    unidade: str = "",
    valor: float = 690.00,
    vencimento: str = "",
) -> dict:
    """
    Gera dados do boleto.

    Se SUPERLOGICA_MODO=real, tenta acessar o Superlógica com Playwright.
    Caso contrário (padrão), gera dados fictícios realistas para teste.
    """
    modo = os.getenv("SUPERLOGICA_MODO", "ficticio").strip().lower()

    if modo == "real":
        logger.info(f"🔍 Modo REAL — buscando boleto {boleto_id} no Superlógica...")
        return extrair_dados_boleto_real(boleto_id, url, cookies_path, timeout)

    # ─── MODO FICTÍCIO (padrão) ───
    logger.info(f"🎲 Modo FICTÍCIO — gerando dados para boleto {boleto_id}...")

    pix = _gerar_pix("RENAISSANCE", unidade)
    linha = _gerar_linha_digitavel(boleto_id, valor)
    link_pdf = _gerar_link_pdf(boleto_id)
    qr_code = _gerar_qr_code_pix(valor, boleto_id)

    return {
        "boleto_id": boleto_id,
        "pix": pix,
        "linha_digitavel": linha,
        "link_pdf": link_pdf,
        "qr_code_copia_cola": qr_code,
        "valor": valor,
        "vencimento": vencimento or (datetime.now() + timedelta(days=30)).strftime("%d/%m/%Y"),
        "sucesso": True,
        "erro": None,
        "modo": "ficticio",
    }


def buscar_e_cachear_boleto(
    boleto_id: str,
    base_path: str = None,
) -> dict:
    """
    Busca boleto no Superlógica, salva no renaissance.json e retorna.
    Se já estiver em cache, retorna direto.
    """
    base_path = base_path or os.getenv("BASE_JSON_PATH", "/data/renaissance.json")
    
    # Tenta carregar do cache existente
    if Path(base_path).exists():
        try:
            with open(base_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            boletos = data.get("boletos", data if isinstance(data, list) else [])
            for b in boletos:
                if str(b.get("boleto_id")) == str(boleto_id):
                    if b.get("pix") or b.get("linha_digitavel"):
                        logger.info(f"📦 Boleto {boleto_id} já tem dados em cache")
                        return {
                            "boleto_id": boleto_id,
                            "pix": b.get("pix"),
                            "linha_digitavel": b.get("linha_digitavel"),
                            "link_pdf": b.get("link_pdf"),
                            "valor": b.get("valor"),
                            "vencimento": b.get("vencimento"),
                            "sucesso": True,
                            "cache": True,
                        }
        except Exception as e:
            logger.warning(f"Erro ao ler cache: {e}")

    # Busca no Superlógica
    logger.info(f"🌐 Buscando boleto {boleto_id} no Superlógica...")
    dados = extrair_dados_boleto(boleto_id)

    if dados["sucesso"]:
        # Atualiza o renaissance.json com os dados
        try:
            with open(base_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            boletos = data.get("boletos", data if isinstance(data, list) else [])
            for i, b in enumerate(boletos):
                if str(b.get("boleto_id")) == str(boleto_id):
                    boletos[i]["pix"] = dados.get("pix")
                    boletos[i]["linha_digitavel"] = dados.get("linha_digitavel")
                    boletos[i]["link_pdf"] = dados.get("link_pdf")
                    boletos[i]["dados_extraidos_em"] = datetime.now().isoformat()
                    break

            # Salva de volta
            if isinstance(data, dict):
                data["boletos"] = boletos
                data["atualizado_em"] = datetime.now().isoformat()
            with open(base_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.success(f"💾 Dados do boleto {boleto_id} salvos em cache")
        except Exception as e:
            logger.warning(f"Não foi possível salvar cache: {e}")

    return dados


def enriquecer_base_completa(
    base_path: str = None,
    cookies_path: str = None,
    url: str = None,
    apenas_inadimplentes: bool = True,
) -> dict:
    """
    Varre todos os boletos inadimplentes e busca PIX/linha de cada um.
    Útil para preencher o cache antes do expediente.

    Returns: { "processados": int, "sucesso": int, "falhas": int }
    """
    base_path = base_path or os.getenv("BASE_JSON_PATH", "/data/renaissance.json")
    
    if not Path(base_path).exists():
        return {"processados": 0, "sucesso": 0, "falhas": 0, "erro": "Base não existe"}

    with open(base_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    boletos = data.get("boletos", data if isinstance(data, list) else [])
    
    processados = 0
    sucesso = 0
    falhas = 0

    for b in boletos:
        # Pula pagos se configurado
        if apenas_inadimplentes and b.get("status", "").lower() in ("pago", "baixado", "quitado"):
            continue
        
        # Pula quem já tem dados
        if b.get("pix") or b.get("linha_digitavel"):
            continue

        processados += 1
        boleto_id = str(b.get("boleto_id") or b.get("id") or "")
        if not boleto_id:
            continue

        logger.info(f"📡 Buscando dados do boleto {boleto_id} - {b.get('nome')}")

        dados = extrair_dados_boleto(
            boleto_id=boleto_id,
            url=url,
            cookies_path=cookies_path,
        )

        if dados["sucesso"]:
            b["pix"] = dados.get("pix")
            b["linha_digitavel"] = dados.get("linha_digitavel")
            b["link_pdf"] = dados.get("link_pdf")
            b["dados_extraidos_em"] = datetime.now().isoformat()
            sucesso += 1
        else:
            falhas += 1
            logger.warning(f"⚠️ Boleto {boleto_id} falhou: {dados.get('erro')}")

    # Salva de volta
    if isinstance(data, dict):
        data["atualizado_em"] = datetime.now().isoformat()
    with open(base_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    logger.success(f"📊 Enriquecimento: {processados} processados, {sucesso} sucesso, {falhas} falhas")
    return {"processados": processados, "sucesso": sucesso, "falhas": falhas}


# ─── CLI ───
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    import sys

    if "--enriquecer" in sys.argv:
        result = enriquecer_base_completa()
        print(f"\n📊 Resultado: {result}")
    
    elif len(sys.argv) > 1:
        boleto_id = sys.argv[1]
        dados = buscar_e_cachear_boleto(boleto_id)
        print(f"\n📋 Dados do boleto {boleto_id}:")
        for k, v in dados.items():
            print(f"  {k}: {v}")
    
    else:
        print("Uso:")
        print("  python -m agente.superlogica_boleto <boleto_id>   # busca 1 boleto")
        print("  python -m agente.superlogica_boleto --enriquecer  # enriquece toda a base")