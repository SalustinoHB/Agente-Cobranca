"""
scraper.py — Coleta lista de boletos da Superlógica via Playwright.

Roda toda manhã às 7h. Atualiza data/renaissance.json.

Estratégia:
1. Se existir storage_state (cookies salvos), reusa
2. Senão, faz login (precisa SUPERLOGICA_EMAIL + SUPERLOGICA_SENHA)
3. Navega até listagem de boletos da Renaissance
4. Extrai dados (nome, unidade, valor, vencimento, status, whatsapp se disponível)
5. Salva em data/renaissance.json
6. Logga run em scraper_runs

Modos:
  --login   : abre browser visível, faz login manual, salva cookies
  (default) : roda headless usando cookies salvos
"""

import json
import os
import sys
from datetime import date, datetime
from pathlib import Path

from loguru import logger

# Playwright imports são lazy pra não falhar se ainda não instalou
# (instalar com: pip install playwright && playwright install chromium)


def login_interativo(
    url: str,
    email: str,
    cookies_path: str,
):
    """
    Abre browser visível. Usuário loga manualmente, salva cookies.
    Roda 1x na primeira configuração, ou quando cookies expiram.
    """
    from playwright.sync_api import sync_playwright

    logger.info("🌐 Abrindo browser visível pra login manual...")
    logger.info(f"   URL: {url}")
    logger.info("   Login com email/senha, depois APERTE ENTER aqui no terminal.")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto(url)

        input("\n⏸️  PRESSIONE ENTER QUANDO TIVER LOGADO E NA HOME DA SUPERLÓGICA...")

        # Salva cookies + localStorage
        Path(cookies_path).parent.mkdir(parents=True, exist_ok=True)
        context.storage_state(path=cookies_path)
        logger.success(f"✅ Cookies salvos em {cookies_path}")

        browser.close()


def coletar_boletos(
    url: str,
    cookies_path: str,
    condominio_id: int,
    lote_mes: str = "auto",
    headless: bool = True,
) -> list:
    """
    Headless, usa cookies salvos. Coleta lista de boletos.

    Retorna lista de dicts com: nome, unidade, valor, vencimento, status, whatsapp, boleto_id.
    """
    from playwright.sync_api import sync_playwright

    if lote_mes == "auto":
        hoje = date.today()
        lote_mes = f"-{hoje.strftime('%Y%m')}"  # ex: -202605

    if not Path(cookies_path).exists():
        raise FileNotFoundError(
            f"Cookies não existem em {cookies_path}. "
            "Rode `python -m agente.scraper --login` primeiro."
        )

    logger.info(f"🔍 Scraping Superlógica | condomínio={condominio_id} | lote={lote_mes}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(storage_state=cookies_path)
        page = context.new_page()

        # Página de cobrança/listagem de boletos
        listagem_url = (
            f"{url}/clients/condor/cobranca/index"
            f"?idLote={lote_mes}&idCondominio={condominio_id}"
        )
        logger.debug(f"Acessando: {listagem_url}")
        page.goto(listagem_url, wait_until="networkidle", timeout=30000)

        # Aguarda tabela carregar
        page.wait_for_selector("table", timeout=15000)

        # Extrai dados via JavaScript
        # NOTA: o seletor exato pode precisar ajuste após inspeção da página real
        boletos = page.evaluate("""
            () => {
                const linhas = document.querySelectorAll('table tbody tr');
                const result = [];

                linhas.forEach((tr) => {
                    const tds = tr.querySelectorAll('td');
                    if (tds.length < 5) return;

                    const item = {
                        // Ajustar índices conforme tabela real
                        unidade: tds[0]?.innerText.trim() || '',
                        nome: tds[1]?.innerText.trim() || '',
                        vencimento: tds[2]?.innerText.trim() || '',
                        valor_str: tds[3]?.innerText.trim() || '',
                        status: tds[4]?.innerText.trim() || '',
                    };

                    // Tenta extrair id do botão de ação
                    const link = tr.querySelector('a[href*="recibo"], a[href*="boleto"]');
                    if (link) {
                        const match = link.href.match(/(\\d{6,})/);
                        if (match) item.boleto_id = match[1];
                    }

                    // Valor: 'R$ 1.234,56' → 1234.56
                    const valorMatch = item.valor_str.match(/[\\d.,]+/);
                    if (valorMatch) {
                        item.valor = parseFloat(
                            valorMatch[0].replace(/\\./g, '').replace(',', '.')
                        );
                    }

                    result.push(item);
                });

                return result;
            }
        """)

        logger.info(f"📥 Coletados {len(boletos)} boletos da listagem")

        # Pega contatos (relatório de Unidades) — opcional, requer URL específica
        # TODO: cruzar com base de contatos depois
        # Por enquanto retorna sem whatsapp; cruzamento é feito separadamente

        browser.close()
        return boletos


def cruzar_com_contatos(boletos: list, contatos_path: str) -> list:
    """
    Cruza boletos coletados com base de contatos (whatsapp) salva localmente.

    contatos.json formato:
    [
      {"unidade": "Apt 401", "nome": "...", "whatsapp": "+5584..."}
    ]
    """
    if not Path(contatos_path).exists():
        logger.warning(f"Contatos não existem em {contatos_path} — boletos sem whatsapp")
        return boletos

    with open(contatos_path, "r", encoding="utf-8") as f:
        contatos = json.load(f)

    # Index por unidade
    idx = {c["unidade"].strip().lower(): c for c in contatos}

    enriched = []
    for b in boletos:
        unidade_key = b.get("unidade", "").strip().lower()
        contato = idx.get(unidade_key)
        if contato:
            b["whatsapp"] = contato.get("whatsapp", "")
            # Confirma nome se não veio do boleto
            if not b.get("nome") and contato.get("nome"):
                b["nome"] = contato["nome"]
        enriched.append(b)

    com_wpp = sum(1 for b in enriched if b.get("whatsapp"))
    logger.info(f"🔗 Cruzamento: {com_wpp}/{len(enriched)} boletos com whatsapp")

    return enriched


def salvar_base(boletos: list, caminho: str):
    """Salva renaissance.json."""
    Path(caminho).parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "atualizado_em": datetime.now().isoformat(),
        "total": len(boletos),
        "boletos": boletos,
    }
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    logger.success(f"💾 Base salva: {caminho} ({len(boletos)} boletos)")


# ─── CLI ───
if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()

    url = os.getenv("SUPERLOGICA_URL", "https://admin109865.superlogica.net")
    cookies = os.getenv("COOKIES_PATH", "./data/superlogica_cookies.json")
    condominio_id = int(os.getenv("SUPERLOGICA_CONDOMINIO_ID", "14"))
    lote = os.getenv("SUPERLOGICA_LOTE_MES", "auto")
    base_out = os.getenv("BASE_JSON_PATH", "./data/renaissance.json")
    contatos = "./data/contatos.json"

    if "--login" in sys.argv:
        email = os.getenv("SUPERLOGICA_EMAIL", "")
        login_interativo(url, email, cookies)
        sys.exit(0)

    headless = "--show" not in sys.argv

    try:
        from agente.state import State
        state = State(os.getenv("DATABASE_PATH", "./data/state.db"))
        run_id = state.registrar_scraper_inicio()

        boletos = coletar_boletos(url, cookies, condominio_id, lote, headless)
        boletos = cruzar_com_contatos(boletos, contatos)
        salvar_base(boletos, base_out)

        state.registrar_scraper_fim(run_id, sucesso=True, boletos=len(boletos))
        logger.success("✅ Scraper concluído com sucesso")

    except Exception as e:
        logger.error(f"❌ Scraper falhou: {e}")
        try:
            state.registrar_scraper_fim(run_id, sucesso=False, erro=str(e))
        except Exception:
            pass
        sys.exit(1)
