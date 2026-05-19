"""
respostas_auto_test.py — Testes unitários do classificador de intenção.

Rodar:
    python -m agente.respostas_auto_test

Sem dependência de pytest — escrito como script standalone pra rodar
no servidor sem instalar nada extra.
"""

from __future__ import annotations

import sys
from typing import Optional

from agente.respostas_auto import classificar_e_responder


# ─── Casos de teste ───
# (texto_entrada, intencao_esperada, acao_esperada, descricao)
CASOS = [
    # ── ja_paguei ──
    ("ja paguei",                       "ja_paguei",          "responder_auto",  "afirmação simples"),
    ("ja paguei o boleto",              "ja_paguei",          "responder_auto",  "com complemento"),
    ("Já paguei!",                      "ja_paguei",          "responder_auto",  "com acento + pontuação"),
    ("paguei hoje cedo",                "ja_paguei",          "responder_auto",  "paguei + tempo"),
    ("ta pago",                         "ja_paguei",          "responder_auto",  "informal 'ta pago'"),
    ("transferi agora",                 "ja_paguei",          "responder_auto",  "sinônimo: transferi"),
    ("Fiz o pix",                       "ja_paguei",          "responder_auto",  "fiz o pix"),
    ("Vou te mandar o comprovante",     "ja_paguei",          "responder_auto",  "comprovante"),
    ("quitei o boleto",                 "ja_paguei",          "responder_auto",  "quitei"),

    # ── promessa_pagamento ──
    ("vou pagar amanha",                "promessa_pagamento", "responder_auto",  "vou pagar"),
    ("pago sexta-feira",                "promessa_pagamento", "responder_auto",  "pago + dia"),
    ("pago na segunda",                 "promessa_pagamento", "responder_auto",  "pago na segunda"),
    ("Semana que vem eu pago",          "promessa_pagamento", "responder_auto",  "semana que vem"),
    ("pago dia 20",                     "promessa_pagamento", "responder_auto",  "pago dia N"),

    # ── pede_valor ──
    ("qual o valor?",                   "pede_valor",         "responder_auto",  "qual o valor"),
    ("quanto eh?",                      "pede_valor",         "responder_auto",  "quanto é"),
    ("quanto ta o boleto",              "pede_valor",         "responder_auto",  "quanto ta"),
    ("Me passa o valor",                "pede_valor",         "responder_auto",  "me passa o valor"),

    # ── pede_pix ──
    ("manda o pix",                     "pede_pix",           "responder_auto",  "manda o pix"),
    ("qual o pix?",                     "pede_pix",           "responder_auto",  "qual o pix"),
    ("Tem chave pix?",                  "pede_pix",           "responder_auto",  "chave pix"),
    ("como pago?",                      "pede_pix",           "responder_auto",  "como pago"),

    # ── pede_2via ──
    ("me manda a 2 via",                "pede_2via",          "responder_auto",  "2 via"),
    ("segunda via do boleto",           "pede_2via",          "responder_auto",  "segunda via"),
    ("manda o boleto pfv",              "pede_2via",          "responder_auto",  "manda o boleto"),
    ("preciso da linha digitavel",      "pede_2via",          "responder_auto",  "linha digitavel"),

    # ── questiona_cobranca (escala) ──
    ("isso esta errado, ja paguei isso ano passado",
                                        "questiona_cobranca", "escalar_humano",  "ja paguei ano passado"),
    ("nao devo nada",                   "questiona_cobranca", "escalar_humano",  "nao devo"),
    ("Isso é um absurdo",               "questiona_cobranca", "escalar_humano",  "absurdo"),
    ("discordo dessa cobrança",         "questiona_cobranca", "escalar_humano",  "discordo"),

    # ── negociacao (escala) ──
    ("quero parcelar",                  "negociacao",         "escalar_humano",  "parcelar"),
    ("podemos fazer um acordo?",        "negociacao",         "escalar_humano",  "acordo"),
    ("tem desconto se eu pagar a vista?","negociacao",        "escalar_humano",  "desconto"),
    ("quero negociar a dívida",         "negociacao",         "escalar_humano",  "negociar"),

    # ── indefinido (escala) ──
    ("oi",                              "indefinido",         "escalar_humano",  "saudação curta"),
    ("...",                             "indefinido",         "escalar_humano",  "reticências"),
    ("blabla qualquer coisa aleatoria", "indefinido",         "escalar_humano",  "lixo aleatório"),
    ("obrigado",                        "indefinido",         "escalar_humano",  "agradecimento isolado"),

    # ── vazio ──
    ("",                                "fora_topico",        "ignorar",         "texto vazio"),
    ("   ",                             "fora_topico",        "ignorar",         "só espaços"),
]


# Limpeza: alguns valores acima têm typo nas aspas (descricao foi escrito como `'`).
# Vamos sanitizar pra evitar TypeError.
def _sanitizar_casos(casos):
    out = []
    for c in casos:
        if len(c) != 4:
            # Caso o item esteja mal-formado, ignora
            continue
        out.append(c)
    return out


def _rodar(casos) -> tuple[int, int, list]:
    passou = 0
    falhou = 0
    falhas: list[str] = []

    for entrada, esperado_int, esperado_acao, descr in casos:
        try:
            r = classificar_e_responder("5584999999999", entrada)
            ok_int = r["intencao"] == esperado_int
            ok_acao = r["acao"] == esperado_acao

            if ok_int and ok_acao:
                passou += 1
                marca = "OK"
                print(f"  [{marca}] {descr!r:50} | {entrada!r:45} -> {r['intencao']}")
            else:
                falhou += 1
                msg = (
                    f"  [FAIL] {descr!r:50} | {entrada!r:45} "
                    f"-> esperado=({esperado_int},{esperado_acao}) "
                    f"obtido=({r['intencao']},{r['acao']})"
                )
                print(msg)
                falhas.append(msg)
        except Exception as e:
            falhou += 1
            msg = f"  [ERR ] {descr!r}: {e}"
            print(msg)
            falhas.append(msg)

    return passou, falhou, falhas


def main():
    casos = _sanitizar_casos(CASOS)
    print(f"\nRodando {len(casos)} casos de teste do classificador...\n")
    print("-" * 100)
    passou, falhou, falhas = _rodar(casos)
    print("-" * 100)
    total = passou + falhou
    print(f"\nResultado: {passou}/{total} passaram, {falhou} falharam.\n")

    if falhou > 0:
        print("Falhas detalhadas:")
        for f in falhas:
            print(f)
        sys.exit(1)

    print("Todos os casos passaram.")
    sys.exit(0)


if __name__ == "__main__":
    main()
