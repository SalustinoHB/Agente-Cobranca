# 🤖 Auto-Resposta Humanizada — Agente Renaissance

> **Data:** 18/05/2026  
> **Versão:** 2.0 — Respostas mais naturais e humanas

---

## 🆕 O que mudou

### 1. VARIAÇÕES DE RESPOSTA
Cada tipo de mensagem agora tem **3-5 respostas diferentes**. O agente escolhe uma aleatoriamente, então **nunca parece robô repetitivo**.

| Intenção | Variações | Exemplo |
|---|---|---|
| "Paguei" | 5 respostas | "Show! Me manda o comprovante..." / "Boa! Manda o comprovantezinho..." |
| "Oi/Bom dia" | 5 respostas | "Oi João! Tudo bem?" / "E aí Maria! Beleza?" |
| "Vou pagar" | 5 respostas | "Combinado! Fico no aguardo..." / "Beleza! Me avisa quando pagar..." |
| "2ª via" | 4 respostas | "Te mando já!" / "Segue os dados atualizados..." |
| "Reclamação" | 4 respostas | "Entendi. Deixa eu verificar..." / "Opa, pode ter engano..." |

### 2. DELAY NATURAL (Simula digitação humana)
Antes respondia instantaneamente (óbvio que era robô). Agora:

```
Cliente envia: "Oi"
Agente aguarda: 4.2 segundos (simulando digitação)
Agente responde: "Oi João! Tudo bem? Aqui é da Pratika..."
```

**Tempo:** 3-8 segundos aleatórios entre receber e responder.

### 3. MEMÓRIA DE CONVERSA
Se o cliente mandar 3 mensagens seguidas, o agente **não repete "Oi" toda vez**.

```
10:00 — Cliente: "Oi"
10:00 — Agente: "Oi Maria! Tudo bem? Aqui é da Pratika..."

10:05 — Cliente: "Qual o valor?"
10:09 — Agente: "O valor é R$ 740,00..."  (sem "Oi" de novo!)
```

### 4. TOM MAIS HUMANO
- **Contractions:** "tô", "tá", "pra", "pro"
- **Gírias leves:** "show", "beleza", "massa", "opa"
- **Emojis esporádicos:** máximo 1 por mensagem
- **Sem formalidade exagerada:** parece mensagem de verdade, não e-mail

---

## 📋 Como funciona o fluxo

```
1. Morador responde a cobrança
      ↓
2. Z-API envia webhook pra API
      ↓
3. Agent classifica a intenção (oi / paguei / vou pagar / etc)
      ↓
4. Verifica se já falou com esse número hoje
      ↓
5. Escolhe resposta aleatória do banco
      ↓
6. Aguarda 3-8 segundos (simula digitação)
      ↓
7. Envia resposta via Z-API
      ↓
8. Se for reclamação/acordo → escala humano (notifica você)
```

---

## 🎯 Intenções que o agente entende

| O que o morador diz | Intenção detectada | O que o agente faz |
|---|---|---|
| "Paguei" / "Já paguei" / "Fiz PIX" | `confirmacao_pagamento` | Pede comprovante |
| "Vou pagar amanhã" / "Pago dia 20" | `promessa_pagamento` | Confirma, pede comprovante depois |
| "Manda o boleto" / "Qual o valor?" | `pedido_2via_boleto` | Manda valor + PIX + linha |
| "Posso parcelar?" / "Tem desconto?" | `pedido_acordo` | Escala pro síndico |
| "Não devo" / "Já paguei mês passado" | `reclamacao` | Escala humano pra verificar |
| "Oi" / "Bom dia" | `saudacao` | Responde amigável, pergunta como ajudar |
| Envia imagem/PDF | `comprovante` | Confirma recebimento, processa OCR |
| Qualquer outra coisa | `desconhecida` | Escala humano (conservador) |

---

## ⚠️ Quando escala pra humano

O agente **sempre escala** (te notifica) quando:

1. **Reclamação** — morador diz que não deve, que já pagou, etc.
2. **Acordo/Parcelamento** — precisa de negociação
3. **Comprovante inválido** — OCR detectou valor errado
4. **Mensagem não entendida** — fallback seguro

**Você recebe notificação por:**
- WhatsApp (se configurado)
- Email (se configurado)
- Dashboard da API (`/api/webhook/conversas`)

---

## 🛠️ Configuração

No `.env`, controle como o agente responde:

```bash
# Quem o agente responde automaticamente?
# "todos" = qualquer número
# "so_inadimplentes" = só quem está na base de devedores
# "whitelist" = só números listados em WEBHOOK_WHITELIST
WEBHOOK_RESPONDER_AUTO_AO=todos

# Respostas automáticas ligadas?
RESPOSTAS_AUTO_HABILITADAS=true

# PIX e linha digitavel do condomínio (aparecem nas respostas)
PIX_CONDOMINIO=pratika.renaissance@pix.com.br
LINHA_DIGITAVEL_CONDOMINIO=00190.00009 01234.567890 12345.678901 2 12345678901234
```

---

## 🧪 Testar o auto-responder

1. **Envie uma mensagem** pra sua instância Z-API
2. **O agente vai responder sozinho** em 3-8 segundos
3. **Verifique a resposta** — deve parecer mensagem de pessoa real

Ou teste via API:
```bash
curl "http://SEU_IP:5000/api/webhook/zapi/test?phone=5584991627655&texto=oi"
```

---

## 📈 Próximas melhorias (roadmap)

- [ ] Integração com LLM (Claude/GPT) pra respostas ainda mais naturais
- [ ] Memória de contexto (lembrar o que falou na conversa passada)
- [ ] Personalização por perfil do morador (formal vs casual)
- [ ] Respostas com botões (Z-API suporta)
- [ ] Análise de sentimento (detectar irritado/estressado)

---

**Arquivos modificados:**
- `agente/respostas.py` — banco de respostas humanizadas
- `agente/webhook.py` — delay + memória + classificador v2
