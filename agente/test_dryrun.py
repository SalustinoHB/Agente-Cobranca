"""
test_dryrun.py — Teste end-to-end em modo dry-run.

O que faz:
  1. Força SENDER_TYPE=dryrun e usa um state.db isolado (./data/test_state.db)
  2. Carrega ./data/renaissance.json
  3. Para cada inadimplente, deriva a etapa pela régua e renderiza a mensagem
  4. Gera relatório Markdown em ./data/teste_dryrun_YYYYMMDD.md
  5. Roda asserts:
       - blacklist (Raimundo 2702) é respeitada
       - sem whatsapp = skip
       - idempotência: 2ª chamada da régua no mesmo dia não duplica
       - cada candidato tem etapa válida da régua

Uso:
    python -m agente.test_dryrun
"""

import os
import sys
import json
import tempfile
from datetime import date, datetime
from pathlib import Path


# Configura ambiente ANTES dos imports do agente
os.environ["SENDER_TYPE"] = "dryrun"
os.environ["ENVIAR_DE_VERDADE"] = "false"

# DB de teste isolado
_TEST_DB = Path("./data/test_state.db").resolve()
_TEST_DB.parent.mkdir(parents=True, exist_ok=True)
if _TEST_DB.exists():
    _TEST_DB.unlink()
os.environ["DATABASE_PATH"] = str(_TEST_DB)

# Logs em arquivo local
os.environ["LOG_FILE"] = "./logs/test_dryrun.log"

from loguru import logger  # noqa: E402

from agente.state import State  # noqa: E402
from agente.sender import make_sender, DryRunSender  # noqa: E402
from agente import regua, templates as tpl  # noqa: E402


# ============================================================
# Caminhos
# ============================================================
BASE_DIR = Path(__file__).parent
BASE_JSON = (BASE_DIR / "data" / "renaissance.json").resolve()
REPORT_DIR = (BASE_DIR / "data").resolve()
REPORT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# Util
# ============================================================
class TestResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.itens = []  # (nome, ok, detalhe)

    def assert_true(self, cond, nome, detalhe=""):
        if cond:
            self.passed += 1
            self.itens.append((nome, True, detalhe))
            print(f"  PASS  {nome}")
        else:
            self.failed += 1
            self.itens.append((nome, False, detalhe))
            print(f"  FAIL  {nome}  ({detalhe})")

    def assert_eq(self, esperado, atual, nome):
        self.assert_true(
            esperado == atual,
            nome,
            f"esperado={esperado!r} atual={atual!r}",
        )

    def resumo(self) -> str:
        total = self.passed + self.failed
        return f"{self.passed}/{total} PASS, {self.failed} FAIL"


# ============================================================
# Helpers
# ============================================================
def carregar_inadimplentes(base_path: Path) -> list:
    """Lê renaissance.json e retorna lista de boletos não pagos."""
    if not base_path.exists():
        print(f"AVISO: base não encontrada em {base_path} — usando mock")
        return _MOCK_BOLETOS

    with open(base_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    boletos = data if isinstance(data, list) else data.get("boletos", [])
    return [b for b in boletos if b.get("status", "").lower() not in ("pago", "baixado", "quitado")]


# Mock pra rodar mesmo sem renaissance.json (5 inadimplentes confirmados)
_HOJE = date.today()


def _venc(dias_atraso: int) -> str:
    from datetime import timedelta
    return (_HOJE - timedelta(days=dias_atraso)).strftime("%d/%m/%Y")


_MOCK_BOLETOS = [
    {
        "id": "MOCK-0602", "boleto_id": "MOCK-0602",
        "unidade": "0602", "nome": "MARCO ANTONIO MARTINS",
        "whatsapp": "+5584999815955",
        "valor": 1596.04, "vencimento": _venc(7), "dias_atraso": 7,
        "status": "vencido", "juridico": False, "acordo": False,
    },
    {
        "id": "MOCK-0801", "boleto_id": "MOCK-0801",
        "unidade": "0801", "nome": "PAULO EDUARDO MORAES",
        "whatsapp": "+5584999828117",
        "valor": 1697.39, "vencimento": _venc(7), "dias_atraso": 7,
        "status": "vencido", "juridico": False, "acordo": False,
    },
    {
        "id": "MOCK-0802", "boleto_id": "MOCK-0802",
        "unidade": "0802", "nome": "LUCIANA GUERRA BRANDÃO",
        "whatsapp": "+5584981184849",
        "valor": 1907.23, "vencimento": _venc(15), "dias_atraso": 15,
        "status": "vencido", "juridico": False, "acordo": True,
    },
    {
        "id": "MOCK-2602", "boleto_id": "MOCK-2602",
        "unidade": "2602", "nome": "BRUNALDO BIGI",
        "whatsapp": "+5511999512022",
        "valor": 13350.61, "vencimento": _venc(30), "dias_atraso": 30,
        "status": "vencido", "juridico": False, "acordo": False,
    },
    {
        "id": "MOCK-2702", "boleto_id": "MOCK-2702",
        "unidade": "2702", "nome": "RAIMUNDO NONATO",
        "whatsapp": "+5584988888888",
        "valor": 5000.00, "vencimento": _venc(60), "dias_atraso": 60,
        "status": "vencido", "juridico": True, "acordo": False,
    },
]


# ============================================================
# Suite
# ============================================================
def run_tests() -> tuple:
    """Executa toda a suíte. Retorna (TestResult, relatorio_dict)."""
    t = TestResult()
    print("=" * 60)
    print("TESTE END-TO-END — Cobrança Renaissance (dry-run)")
    print("=" * 60)

    # ─── Setup ───
    state = State(str(_TEST_DB))
    sender = make_sender()
    t.assert_true(isinstance(sender, DryRunSender), "Sender é DryRunSender")
    t.assert_true(sender.esta_conectado(), "DryRunSender 'conectado'")

    # Adiciona Raimundo na blacklist
    state.adicionar_blacklist("+5584988888888", "Caso jurídico")
    t.assert_true(
        state.esta_na_blacklist("+5584988888888"),
        "Blacklist registrada para Raimundo",
    )

    # ─── Carregar base ───
    boletos = carregar_inadimplentes(BASE_JSON)
    print(f"\nBoletos carregados: {len(boletos)}")
    t.assert_true(len(boletos) > 0, "Base tem pelo menos 1 boleto")

    # ─── Renderiza mensagem pra cada inadimplente ───
    relatorio_msgs = []
    print("\n--- Renderização das mensagens ---")
    for b in boletos:
        dias = b.get("dias_atraso", 0)
        etapa = tpl.determinar_etapa(dias)
        if etapa:
            codigo, descricao, _ = etapa
            resultado = tpl.renderizar(b)
            relatorio_msgs.append({
                "unidade": b.get("unidade"),
                "nome": b.get("nome"),
                "whatsapp": b.get("whatsapp"),
                "dias_atraso": dias,
                "etapa": codigo,
                "etapa_descricao": descricao,
                "texto": resultado.get("texto"),
                "deve_enviar": True,
            })
            print(f"  {b.get('unidade')} {b.get('nome'):30} dias={dias:>4}  etapa={codigo}")
        else:
            relatorio_msgs.append({
                "unidade": b.get("unidade"),
                "nome": b.get("nome"),
                "whatsapp": b.get("whatsapp"),
                "dias_atraso": dias,
                "etapa": None,
                "etapa_descricao": f"fora da régua ({dias} dias)",
                "texto": None,
                "deve_enviar": False,
            })
            print(f"  {b.get('unidade')} {b.get('nome'):30} dias={dias:>4}  SKIP (fora da régua)")

    # ─── Régua: 1ª passada ───
    print("\n--- 1ª passada da régua ---")
    candidatos1 = regua.filtrar_para_envio_hoje(boletos, state)
    print(f"Candidatos: {len(candidatos1)}")

    # Raimundo NÃO deve estar na lista (blacklist)
    nomes_cand = [c["boleto"].get("nome") for c in candidatos1]
    t.assert_true(
        "RAIMUNDO NONATO" not in nomes_cand,
        "Blacklist respeitada (Raimundo fora dos candidatos)",
    )

    # Boletos sem whatsapp não entram
    for c in candidatos1:
        t.assert_true(
            bool(c["boleto"].get("whatsapp")),
            f"Candidato tem whatsapp ({c['boleto'].get('nome')})",
        )

    # Cada candidato tem etapa válida
    etapas_validas = {"D-3", "D-0", "D+1", "D+7", "D+15", "D+30"}
    for c in candidatos1:
        cod = c["resultado"]["etapa_codigo"]
        t.assert_true(
            cod in etapas_validas,
            f"Etapa válida para {c['boleto'].get('nome')} (codigo={cod})",
        )

    # ─── Envio simulado (escreve no state) ───
    for c in candidatos1:
        b = c["boleto"]
        r = c["resultado"]
        envio = sender.enviar_texto(b["whatsapp"], r["texto"])
        state.registrar_envio(
            boleto=b,
            etapa_codigo=r["etapa_codigo"],
            etapa_descricao=r["etapa_descricao"],
            texto=r["texto"],
            dry_run=True,
            sucesso=envio["sucesso"],
            evolution_message_id=envio["message_id"],
            evolution_response=str(envio["raw_response"])[:500],
            erro=envio["erro"],
        )
        t.assert_true(envio["sucesso"], f"Envio dry-run OK pra {b.get('nome')}")

    # ─── Régua: 2ª passada (idempotência) ───
    print("\n--- 2ª passada da régua (esperado: 0 candidatos) ---")
    candidatos2 = regua.filtrar_para_envio_hoje(boletos, state)
    t.assert_eq(
        0,
        len(candidatos2),
        "Idempotência: 2ª passada não retorna candidatos",
    )

    # ─── Stage selection coverage ───
    print("\n--- Cobertura de seleção de etapas ---")
    for dias_test in [-3, 0, 1, 7, 15, 30]:
        etapa = tpl.determinar_etapa(dias_test)
        t.assert_true(
            etapa is not None,
            f"determinar_etapa({dias_test}) retorna template",
        )
    for dias_test in [-2, -1, 2, 8, 50, 100]:
        etapa = tpl.determinar_etapa(dias_test)
        t.assert_true(
            etapa is None,
            f"determinar_etapa({dias_test}) retorna None (fora da régua)",
        )

    return t, relatorio_msgs


# ============================================================
# Markdown report
# ============================================================
def gerar_relatorio_markdown(msgs: list, test_result: TestResult) -> Path:
    """Gera ./data/teste_dryrun_YYYYMMDD.md com cada mensagem renderizada."""
    nome_arq = f"teste_dryrun_{datetime.now().strftime('%Y%m%d')}.md"
    arquivo = REPORT_DIR / nome_arq

    linhas = []
    linhas.append(f"# Teste Dry-Run — {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    linhas.append("")
    linhas.append(f"**Resultado**: {test_result.resumo()}")
    linhas.append("")
    linhas.append("## Asserts")
    linhas.append("")
    for nome, ok, detalhe in test_result.itens:
        marca = "[PASS]" if ok else "[FAIL]"
        linhas.append(f"- {marca} {nome}" + (f" — {detalhe}" if detalhe and not ok else ""))
    linhas.append("")
    linhas.append("## Mensagens renderizadas")
    linhas.append("")

    for m in msgs:
        linhas.append("---")
        linhas.append("")
        linhas.append(f"### Apto {m['unidade']} — {m['nome']}")
        linhas.append("")
        linhas.append(f"- WhatsApp: `{m['whatsapp']}`")
        linhas.append(f"- Dias de atraso: **{m['dias_atraso']}**")
        linhas.append(f"- Etapa: **{m['etapa'] or '—'}** ({m['etapa_descricao']})")
        linhas.append(f"- Deve enviar: {'sim' if m['deve_enviar'] else 'não'}")
        linhas.append("")
        if m["texto"]:
            linhas.append("```")
            linhas.append(m["texto"])
            linhas.append("```")
        else:
            linhas.append("_Fora da régua hoje — sem mensagem._")
        linhas.append("")

    arquivo.write_text("\n".join(linhas), encoding="utf-8")
    print(f"\nRelatório gerado: {arquivo}")
    return arquivo


# ============================================================
# Main
# ============================================================
def main() -> int:
    # Logging mínimo para console (sem poluir o teste)
    logger.remove()
    logger.add(sys.stderr, level="WARNING")

    test_result, msgs = run_tests()
    gerar_relatorio_markdown(msgs, test_result)

    print()
    print("=" * 60)
    print(f"SUMÁRIO: {test_result.resumo()}")
    print("=" * 60)

    return 0 if test_result.failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
