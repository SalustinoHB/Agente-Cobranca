# 📋 Manual de Aprovação — Cobrança Renaissance

> Como aprovar mensagens de cobrança antes do bot enviar.
> **Você nunca precisa abrir a Claude pra isso.**

---

## 🎯 Visão Geral do Fluxo

```
┌─────────────────────────────────────────────────┐
│  08h00 — Régua roda automaticamente na AWS      │
│         Identifica 5 inadimplentes pra cobrar   │
└─────────────────────┬───────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────┐
│  08h05 — Sistema gera mensagens prontas         │
│         Salva em "pendentes" (não envia ainda)  │
└─────────────────────┬───────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────┐
│  08h05 — Você recebe notificação WhatsApp       │
│         no seu número (+5584921627655)          │
└─────────────────────┬───────────────────────────┘
                      │
                      ▼
              ┌───────┴───────┐
              ▼               ▼
    ┌──────────────┐  ┌──────────────────┐
    │ Aprovar via  │  │ Aprovar via      │
    │ WhatsApp     │  │ Dashboard Web    │
    │ (responder)  │  │ (abrir link)     │
    └──────┬───────┘  └────────┬─────────┘
           └──────────┬────────┘
                      ▼
┌─────────────────────────────────────────────────┐
│  Bot envia mensagens aprovadas pelos clientes   │
└─────────────────────────────────────────────────┘
```

---

## 📱 Onde chega a notificação?

**Número configurado:** **+55 84 99162-7655** (seu WhatsApp pessoal)

Configurado no `.env` da EC2 como `OPERADOR_WHATSAPP=5584921627655`.

Pra mudar (ex: pra Paulo), edita esse arquivo e reinicia o container.

---

## 🔵 Modo 1 — Aprovar via WhatsApp (mobile)

### Chegará uma mensagem assim no seu WhatsApp:

```
📬 PRATIKA COBRANÇA — Aprovações pendentes

5 mensagens prontas pra disparar hoje:

1️⃣ MARCO ANTONIO (apto 0602)
   R$ 1.596,04 — 7 dias atraso

2️⃣ PAULO EDUARDO (apto 0801)
   R$ 1.697,39 — 7 dias atraso

3️⃣ BRUNALDO BIGI (apto 2602)
   R$ 13.350,61 — 197 dias atraso ⚠️

...

━━━━━━━━━━━━━━━━━━━━
Como aprovar:

✅ "ok"          → aprova todas
🔢 "1 2 4"       → aprova só essas
✏️ "editar 3"   → edita a 3
❌ "cancelar"   → cancela tudo

📱 Detalhes: http://15.228.231.24:5000/dashboard

⏰ Decide até 17h hoje.
```

### Suas respostas possíveis:

| Você responde | O que acontece |
|---|---|
| `ok` | Aprova **todas** — bot envia em sequência (3 min entre cada pra não dar flag) |
| `1 2 4` | Aprova só 1, 2 e 4 — pula 3 e 5 |
| `editar 3` | Sistema te manda texto do nº 3, você edita, manda de volta, sistema envia versão editada |
| `cancelar` | Cancela tudo, nada é enviado hoje |
| Não responder | Nada é enviado (régua espera aprovação) |

---

## 🟢 Modo 2 — Aprovar via Dashboard Web

### URL: http://15.228.231.24:5000/dashboard

Acessível por qualquer navegador (PC, celular, tablet).

### O que você vê:

```
┌─────────────────────────────────────────────────────┐
│  Cobranca Renaissance — Dashboard                    │
│                                                       │
│  Status: WhatsApp ✅ conectado                        │
│  Sender: Z-API                                        │
│  Enviadas hoje: 0                                    │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│  1. MARCO ANTONIO MARTINS — apto 0602                │
│     R$ 1.596,04 · 7 dias atraso                     │
│     Etapa: Atraso inicial                           │
│                                                       │
│     📨 Mensagem prevista:                            │
│     ┌─────────────────────────────────────────┐    │
│     │ Oi, Marco! Tudo bem?                     │    │
│     │                                           │    │
│     │ Identificamos que o boleto do apto 0602 │    │
│     │ venceu há 7 dias e ainda não consta...  │    │
│     │ ...                                       │    │
│     └─────────────────────────────────────────┘    │
│                                                       │
│     [✅ Aprovar] [✏️ Editar] [❌ Pular]              │
└─────────────────────────────────────────────────────┘

[+ Mais 4 cards iguais]

[Aprovar todas] [Cancelar todas]
```

### Como usar:

1. Acessa a URL no navegador
2. Login com **API Token** (te passo separado por segurança)
3. Revisa cada card
4. Clica **"✅ Aprovar"** em cada um que quiser enviar
5. OU clica **"✏️ Editar"** pra mexer no texto antes
6. OU clica **"Aprovar todas"** se tá tudo OK
7. Bot envia em sequência (3 min de intervalo)

### Quem pode acessar:

- Você (com token)
- Paulo (com token)
- Eduardo, Tiago, etc. (com token)
- **Não tem login/senha individual**, é o mesmo token pra todos

---

## ⚙️ Modo 3 — API direta (pra integrações)

Pra usar em scripts, Asana, planilhas Google, etc.:

### Listar pendentes
```bash
curl http://15.228.231.24:5000/api/aprovacao/pendentes \
  -H "Authorization: Bearer SEU_TOKEN"
```

### Aprovar todos
```bash
curl -X POST http://15.228.231.24:5000/api/aprovacao/confirmar \
  -H "Authorization: Bearer SEU_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"todos": true}'
```

### Aprovar específicos
```bash
curl -X POST http://15.228.231.24:5000/api/aprovacao/confirmar \
  -H "Authorization: Bearer SEU_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"ids": ["159305", "159308"]}'
```

---

## 🚦 Cenários comuns

### Cenário 1 — Aprovação rápida no celular

São 9h da manhã. Você toma café, abre WhatsApp e vê:

> 📬 PRATIKA COBRANÇA — 5 pendentes...

Lê rapidão, todas parecem OK. Responde **"ok"** → bot envia as 5 nos próximos 15 min.

### Cenário 2 — Tirar 1 da lista

Mesmo cenário, mas você vê que o nº 3 é o **Brunaldo** (crônico, mora em SP, prefere falar com ele pessoalmente):

Responde **"1 2 4 5"** → bot envia 1, 2, 4 e 5. Pula o 3.

### Cenário 3 — Ajustar uma mensagem antes

Você acha que o texto da nº 2 (Paulo Eduardo) deveria ser mais brando porque ele é amigo:

Responde **"editar 2"** → bot manda o texto atual → você manda versão editada → bot envia a versão sua.

### Cenário 4 — Não responder

Você tá em reunião o dia todo, não responde nada.

**Resultado:** nada é enviado. Mensagens ficam pendentes pra você revisar depois. Régua roda de novo amanhã às 8h.

### Cenário 5 — Cliente já paguei (resposta)

Marco Antonio recebe sua cobrança, responde "já paguei segunda".

**O bot detecta intent "confirmacao_pagamento" e responde automático:**

> Massa! Pra confirmar aqui no sistema e dar baixa, pode me mandar o comprovante (print ou PDF)? Bem rapidinho ✅

Marco manda print do comprovante → bot baixa imagem → OCR extrai valor → compara com boleto → se bater, marca como pago e responde:

> Comprovante recebido e validado, R$ 1.596,04 ✅
> Boleto do apto 0602 dado como pago. Obrigado!

Se não bater (valor errado, falsificação), bot escala pra você:

> 🚨 Cobrança Pratika - Escalação
> Marco Antonio mandou comprovante mas valor não bate
> Esperado: R$ 1.596,04 | Extraído: R$ 596,04
> Verifica antes de dar baixa.

---

## ❓ Perguntas frequentes

**Q: E se eu não quiser aprovar via WhatsApp, só via dashboard?**
R: Desabilita a notificação WhatsApp setando `NOTIFICAR_OPERADOR_WHATSAPP=false` no .env. Sistema só guarda em pendentes; você revisa quando quiser no dashboard.

**Q: Quanto tempo a aprovação expira?**
R: Não expira. Mensagens ficam em pendentes até você aprovar/cancelar/expirar via tempo (default 24h).

**Q: Posso ter horários diferentes de envio?**
R: Sim. Edita `HORARIO_INICIO_ENVIO` e `HORARIO_FIM_ENVIO` no .env. Por padrão é 09:00-18:00. Fora desse horário fica em pendentes.

**Q: E sábado e domingo?**
R: Por padrão NÃO envia. Configurável: `ENVIAR_SABADO=true`, `ENVIAR_DOMINGO=true`.

**Q: Quantos pedidos de aprovação posso ter ao mesmo tempo?**
R: Sem limite. Mas se tiver mais de 50 pendentes, o WhatsApp vai estourar tamanho de mensagem. Aí a notif do WhatsApp mostra só os 20 primeiros e te manda o link do dashboard pro resto.

**Q: O bot manda lembrete se eu não aprovar?**
R: Sim. Às 14h, se ainda tem pendentes, envia lembrete: "⏰ 5 pendentes esperando aprovação. Decide até 17h."

**Q: Como adiciono outra pessoa pra aprovar (Paulo)?**
R: Configura `OPERADOR_WHATSAPP_SECUNDARIO=5584XXXXXXXXX` no .env. Os 2 recebem a notif. Qualquer um pode aprovar.

---

## 🛡️ Segurança

- **Mensagens enviadas são auditadas**: tudo gravado em SQLite (`/data/state.db`)
- **Histórico no dashboard**: vê quem aprovou cada mensagem
- **Sem dupla aprovação**: se você aprovou "1 2 4" no WhatsApp e Paulo aprova "tudo" depois, sistema só envia 1 vez cada
- **Idempotência**: mesma mensagem nunca é enviada 2x no mesmo dia (mesmo se aprovada 2x)

---

## 🔧 Como mudar quem recebe a notificação

Edita o arquivo `.env` na EC2:
```bash
ssh -i C:\Users\admin\Downloads\cobranca-renaissance-key.pem ubuntu@15.228.231.24
sudo nano /opt/cobranca-renaissance/.env
```

Muda:
```
OPERADOR_WHATSAPP=5584XXXXXXXXX   ← seu número novo
```

Reinicia:
```bash
sudo docker restart cobranca-api
```

Pronto. Próxima rodada da régua vai notificar o número novo.

---

*Manual gerado em 13/05/2026. Pratika/Nuvio.*
