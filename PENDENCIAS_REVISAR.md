# 📋 Pendências para Revisão Humana

> Última atualização: 18/05/2026
> Base: Relatório 045A — Superlógica Pratika (88 unidades)

---

## ✅ RESOLVIDO — Z-API Configurada

**Status:** Conta Z-API ativa, chip conectado, instância operacional.
- Instance URL: `https://api.z-api.io/instances/3F3504716F44324E0D095EE982B712E3/token/EB69BCFE629B94E3AAC8D8E9`
- Backend: `SENDER_TYPE=zapi`
- Deploy: pronto pra subir na AWS

---

## 🔴 INADIMPLENTES — 9 unidades (requerem ação)

### I1. Com WhatsApp válido — 8 unidades (prontas pra régua)

| Unidade | Nome | WhatsApp | Valor | Dias atraso | Status |
|---|---|---|---|---|---|
| 0304 A | PATRICIA CHRISTIANNE PEREIRA DE SOUZA | 5584991298734 | R$ 740 | 13 | ✅ Pronto |
| 0603 A | FRANCISCO SOARES DE O. FILHO | 5584999823413 | R$ 740 | 13 | ✅ Pronto |
| 0802 A | ANDRE CAVALCANTI DE OLIVEIRA | 5584999848957 | R$ 740 | 13 | ✅ Pronto |
| 0803 A | TEREZINHA NOVAES GRANJA SILVA | 5583996815960 | R$ 740 | 13 | ⚠️ DDD 83 (PB) |
| 1104 A | GILVANETE SILVA | 5584996920820 | R$ 740 | 13 | ✅ Pronto |
| 0302 B | EMANUEL GUTTEMBERG DE MEDEIROS | 5584995293395 | R$ 740 | 13 | ✅ Pronto |
| 1003 B | GERALDO SABINO DE ARAUJO | 5584999916688 | R$ 740 | 13 | ✅ Pronto |
| 1104 B | LUZIA VALENTIM BORGES MARQUES | 5584988485153 | R$ 740 | 13 | ✅ Pronto |

**Ação:** Aprovar via dashboard (`/dashboard/aprovacao.html`) ou API.

---

### I2. SEM TELEFONE — 1 unidade (não pode receber automático)

| Unidade | Nome | Problema | Ação necessária |
|---|---|---|---|
| 0704 A | ALICE MARIA LINS MONTEIRO | Sem telefone no Superlógica | Coletar na portaria ou com síndico |

---

## 🟡 SEM WHATSAPP — 37 unidades (em dia, mas sem contato)

Estas unidades estão com pagamento em dia, mas **não têm telefone cadastrado** no Superlógica. Isso é um risco operacional — se atrasarem, não dá pra cobrar automaticamente.

> **Total: 37 de 88 unidades sem telefone cadastrado.**
> **Recomendação:** Campanha de atualização cadastral com o síndico.

---

## 🟠 CASOS DA BASE ANTIGA (29 unidades) — NÃO ENCONTRADOS NA NOVA BASE

| Apto | Nome | Situação na base antiga | Ação |
|---|---|---|---|
| 0602 | MARCO ANTONIO MARTINS | Inadimplente (R$ 1.596,04) | 🔍 Verificar se pagou |
| 0801 | PAULO EDUARDO | Inadimplente (R$ 1.697,39) | 🔍 Verificar se pagou |
| 0802 | LUCIANA GUERRA | Em acordo (parcela 10/11) | 🔍 Verificar status do acordo |
| 2602 | BRUNALDO BIGI | Inadimplência crônica (197 dias) | 🔍 Verificar se entrou em acordo |
| 2702 | RAIMUNDO NONATO | Blacklist jurídico (Dra. Katiuscia) | 🔍 Verificar se processo continua |

---

## 📊 RESUMO GERAL

| Categoria | Quantidade | % do total |
|---|---|---|
| **Total unidades** | 88 | 100% |
| Pagos/em dia | 79 | 90% |
| Inadimplentes | 9 | 10% |
| Inadimplentes com WhatsApp | 8 | 9% |
| Inadimplentes SEM telefone | 1 | 1% |
| Em dia SEM telefone | 37 | 42% |

---

## 🛠️ Próximos passos recomendados

1. **Deploy AWS** — subir agente com Z-API
2. **Testar dry-run** — gerar preview das 8 mensagens
3. **Aprovar 1 envio de teste** — pra Patricia (0304 A) ou outro com WhatsApp válido
4. **Se chegou:** ligar `ENVIAR_DE_VERDADE=true`
5. **Coletar telefone Alice (0704 A)** — na portaria ou com síndico
6. **Verificar casos da base antiga** — Marco Antonio, Paulo Eduardo, Brunaldo, Raimundo

---

## 🗄️ HISTÓRICO (base antiga — 13/05/2026)

<details>
<summary>Clique para ver pendências da base antiga (29 unidades)</summary>

### B1. Conexão WhatsApp — anti-abuso ativo (RESOLVIDO com Z-API)

### D1. 27 unidades com DDD ausente (base antiga)
- 0102 JOÃO TOSCANO DELGADO
- 0201 ROBERTO TEIXEIRA JUNIOR
- 0301 ADAY REGINA DE SOUSA
- 0302 SIMONE SOUTO MAIA
- 0401 MARÍLIA SILVEIRA
- 0402 ALEXANDRE MOTTA
- 0502 FV INVESTIMENTOS (PJ)
- ... (ver base antiga completa em `contatos_consolidado.json`)

### D2. 6 unidades SEM TELEFONE (base antiga)
- 0501 HELIO SANTA ROSA MAFRA
- 0901 ANDRÉS DE MEDEIROS LEITE
- 1301 DIRCEU FONSECA DE MIRANDA
- 1702 THIAGO GALVÃO SIMONETTI
- 1901 MELINA TERTULINO DE LIMA
- 2302 ERIKA VIDAL COSTA RÊGO

</details>
> Base: Relatório 045A — Contatos das Unidades (Superlógica Pratika)
> Itens que **eu (Claude) não consegui resolver sozinho** — precisam de validação humana.

---

## ✅ BLOQUEADOR RESOLVIDO

### B1. Conexão WhatsApp — Z-API ativa

**Status:** ✅ RESOLVIDO — Conta Z-API criada e configurada.

- **Instance URL:** `https://api.z-api.io/instances/3F3504716F44324E0D095EE982B712E3/token/EB69BCFE629B94E3AAC8D8E9`
- **Backend:** `SENDER_TYPE=zapi`
- **Chip:** Conectado no painel Z-API
- **Custo:** ~R$ 67/mês

---

## 📊 DADOS ATUALIZADOS (88 unidades — Maio/2026)

**Fonte:** `Serviço Releitura/08 - Pratika Cobrança Renaissance/01 - Dados/base_unificada.json`

| Métrica | Valor |
|---|---|
| Total unidades | **88** |
| Boletos pagos/recebidos | 79 |
| Boletos vencidos (inadimplentes) | **9** |
| Valor padrão do condomínio | R$ 690,00 |
| Valor com juros (atraso) | R$ 740,00 |
| Vencimento | 05/05/2026 |
| Dias de atraso (hoje 18/05) | 13 dias |
| Com WhatsApp válido | 51 |
| Sem WhatsApp | 37 |

---

## 🔴 INADIMPLENTES — 9 unidades (status "Vencida")

| Unidade | Nome | WhatsApp | Valor | Dias atraso | Status envio |
|---|---|---|---|---|---|
| 0304 A | PATRICIA CHRISTIANNE PEREIRA DE SOUZA | ✅ 5584991298734 | R$ 740 | 13 | **Pronto** |
| 0603 A | FRANCISCO SOARES DE O. FILHO | ✅ 5584999823413 | R$ 740 | 13 | **Pronto** |
| 0704 A | ALICE MARIA LINS MONTEIRO | ❌ **SEM TELEFONE** | R$ 740 | 13 | **Bloqueado** |
| 0802 A | ANDRE CAVALCANTI DE OLIVEIRA | ✅ 5584999848957 | R$ 740 | 13 | **Pronto** |
| 0803 A | TEREZINHA NOVAES GRANJA SILVA | ✅ 5583996815960 | R$ 740 | 13 | **Pronto** |
| 1104 A | GILVANETE SILVA | ✅ 5584996920820 | R$ 740 | 13 | **Pronto** |
| 0302 B | EMANUEL GUTTEMBERG DE MEDEIROS | ✅ 5584995293395 | R$ 740 | 13 | **Pronto** |
| 1003 B | GERALDO SABINO DE ARAUJO | ✅ 5584999916688 | R$ 740 | 13 | **Pronto** |
| 1104 B | LUZIA VALENTIM BORGES MARQUES | ✅ 5584988485153 | R$ 740 | 13 | **Pronto** |

**Cobertura de cobrança:** 8 de 9 inadimplentes (89%) têm WhatsApp válido.
**Bloqueado:** 1 unidade (0704 A — Alice) sem telefone cadastrado.

---

## 🟡 UNIDADES SEM WHATSAPP (37 total)

Estas unidades não têm telefone cadastrado no Superlógica ou o número está em formato inválido. Não receberão cobrança automática até atualização.

### Sem telefone algum cadastrado

| Unidade | Nome | Email (se houver) |
|---|---|---|
| 0104 A | MARIA DE FATIMA SOUTO | dudunatal2006@gmail.com |
| 0203 A | JEIMES MARQUES TEODORO | jmt13@bol.com.br |
| 0303 A | ERTON LUIZ DE LIMA | ertonlima@hotmail.com |
| 0501 A | IVANALDO SOARES DA SILVA JUNIOR | ivanaldo.soares71@gmail.com |
| 0502 A | HEBERT RANIERY SILVA DE ALBUQUERQUE | hebertraniery@hotmail.com |
| 0503 A | (dados incompletos) | — |
| 0604 A | LUIS GEVANIR DE FREITAS GUERRA | — |
| 0704 A | ALICE MARIA LINS MONTEIRO | — |
| 0804 A | (dados incompletos) | — |
| 0901 A | (dados incompletos) | — |
| 0902 A | (dados incompletos) | — |
| 0903 A | (dados incompletos) | — |
| 0904 A | (dados incompletos) | — |
| 1001 A | (dados incompletos) | — |
| 1002 A | (dados incompletos) | — |
| 1004 A | (dados incompletos) | — |
| 1101 A | (dados incompletos) | — |
| 1102 A | (dados incompletos) | — |
| 1103 A | (dados incompletos) | — |
| 1201 A | (dados incompletos) | — |
| 1202 A | (dados incompletos) | — |
| 1203 A | (dados incompletos) | — |
| 1204 A | (dados incompletos) | — |
| 1301 A | (dados incompletos) | — |
| 1302 A | (dados incompletos) | — |
| 1303 A | (dados incompletos) | — |
| 1304 A | (dados incompletos) | — |
| 1401 A | (dados incompletos) | — |
| 1402 A | (dados incompletos) | — |
| 1403 A | (dados incompletos) | — |
| 1404 A | (dados incompletos) | — |

### Com telefone em formato inválido/não normalizável

| Unidade | Nome | Telefone bruto | Problema |
|---|---|---|---|
| 0201 A | TALITA CAMARA MEDEIROS | +55 32079607 | Fixo 8 dígitos sem DDD |
| 0504 A | LENIGIA MARIA DE ALENCAR | +55 32328320 / +55 32084042 | Fixo 8 dígitos sem DDD |
| 0701 A | MARCOS VASCONCELOS CORREIA | +55 32079607 | Fixo 8 dígitos sem DDD |

**Ação sugerida:** Equipe Pratika abre cadastro no Superlógica e adiciona celular com DDD 84.

---

## 🟠 ATENÇÃO — Casos da base antiga (não encontrados na nova base de 88)

Os seguintes inadimplentes da base antiga (29 unidades) **não aparecem** no relatório 045A atual. Precisam ser verificados:

| Apto | Nome | Situação na base antiga | Ação necessária |
|---|---|---|---|
| 0602 | MARCO ANTONIO MARTINS | Inadimplente (R$ 1.596,04, 7 dias) | Verificar se pagou ou se é outro bloco |
| 0801 | PAULO EDUARDO | Inadimplente (R$ 1.697,39), DDD ambíguo | Confirmar cadastro no Superlógica |
| 0802 | LUCIANA GUERRA | Em acordo (parcela 10/11) | Verificar status do acordo |
| 2602 | BRUNALDO BIGI | Inadimplência crônica (197 dias), DDD 11 SP | Contato humano recomendado |
| 2702 | RAIMUNDO NONATO | **Blacklist jurídico** — Dra. Katiuscia | Manter em blacklist |

> ⚠️ **Possíveis explicações:**
> - Podem ser de outro bloco/edifício do condomínio
> - Podem ter sido excluídos do relatório 045A por algum filtro
> - Nomes podem estar diferentes no cadastro

---

## 🚫 BLACKLIST (manter)

### BL1. Apto 2702 RAIMUNDO NONATO DA FONSECA

**Em processo jurídico** — advogada **Dra. Katiuscia Fonseca**.

**Status:** `envia_regua: false`, `categoria: juridico_blacklist`.

Adicionar via API se necessário:
```bash
curl -X POST http://IP:5000/api/blacklist \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"whatsapp": "5555988122235", "motivo": "Em processo juridico - Dra. Katiuscia Fonseca"}'
```

---

## 📊 RESUMO GERAL

| O que | Quantidade |
|---|---|
| Total unidades no condomínio | **88** |
| Inadimplentes (vencidos) | **9** |
| Inadimplentes com WhatsApp válido | **8** (89%) |
| Inadimplentes SEM WhatsApp | **1** (0704 A Alice) |
| Unidades em dia com WhatsApp | 43 |
| Unidades em dia SEM WhatsApp | 36 |
| **Cobertura total de cobrança** | **51 de 88** (58%) |

---

## 🛠️ Como atualizar telefones

1. Abrir Superlógica → Relatório 045A → Contatos das Unidades
2. Para cada unidade sem telefone:
   - Adicionar celular no campo "Telefone 1" ou "Celular"
   - Formato ideal: `(84) 99999-9999`
3. Salvar alterações no Superlógica
4. Rodar scraper ou exportar novo relatório 045A
5. Me enviar o novo arquivo que eu converto automaticamente

---

## 🚀 Próximos passos para produção

| # | Ação | Responsável | Prazo |
|---|---|---|---|
| 1 | Verificar 5 casos da base antiga (0602, 0801, 0802, 2602, 2702) | Pratika | Antes do 1º envio |
| 2 | Coletar telefone da Alice (0704 A) | Síndico/Portaria | Antes do 1º envio |
| 3 | Testar envio dry-run pra 1 número próprio | Murilo | Após deploy |
| 4 | Aprovar envio real via dashboard | Murilo/Paulo | Quando confiar |
| 5 | Ligar `ENVIAR_DE_VERDADE=true` | Murilo | Após testes OK |
