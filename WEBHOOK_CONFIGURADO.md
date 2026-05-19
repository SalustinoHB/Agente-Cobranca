# ✅ Webhook Configurado — Z-API

## O que foi feito

### 1. Painel Z-API (app.z-api.io)
- ✅ Acessada instância `cobranca` (ID: 3F3504716F44324E0D095EE982B712E3)
- ✅ Configurado webhook "Ao receber":
  ```
  http://15.228.231.24:5000/api/webhook/zapi
  ```
- ✅ Salvo com sucesso (mensagem: "Instância web salva com sucesso")

### 2. Endpoint do Webhook (agente/webhook.py)
- ✅ `POST /api/webhook/zapi` — recebe mensagens do Z-API
- ✅ Ignora mensagens próprias (`fromMe=true`) e grupos (`isGroup=true`)
- ✅ Idempotente por `messageId` — não processa a mesma msg 2x
- ✅ Classifica intenção e responde automaticamente
- ✅ Delay natural de 3-8 segundos antes de responder
- ✅ Registra tudo no SQLite (auditoria)

### 3. Auto-Responder (agente/respostas.py v2)
- ✅ Variações de resposta (3-5 por intenção)
- ✅ Memória de conversa (evita repetir "Oi" toda hora)
- ✅ Personalização com nome do morador
- ✅ Intenções suportadas:
  - `confirmacao_pagamento` → pede comprovante
  - `promessa_pagamento` → confirma e aguarda
  - `pedido_2via_boleto` → envia dados do boleto
  - `pedido_acordo` → encaminha pro síndico
  - `reclamacao` → escala pra humano
  - `saudacao` → responde com contexto
  - `comprovante` → confirma recebimento
  - `desconhecida` → resposta genérica

## Como testar

### Teste local (sem Z-API):
```bash
# 1. Inicie a API local
uvicorn agente.api:app --host 0.0.0.0 --port 5000

# 2. Em outro terminal, rode o teste
python teste_webhook_local.py
```

### Teste real (com Z-API):
1. Envie uma mensagem de teste para o número do chip conectado no Z-API
2. O webhook vai receber e responder automaticamente
3. Verifique os logs: `tail -f /data/agente.log`

## Próximos passos

1. **Garantir que a API está rodando na AWS** (15.228.231.24:5000)
2. **Testar com mensagem real** — envie "Oi" para o número do chip
3. **Verificar logs** para confirmar que o webhook está recebendo
4. **Ajustar política de resposta** no `.env` se necessário:
   ```env
   WEBHOOK_RESPONDER_AUTO_AO=todos          # responde qualquer um
   WEBHOOK_RESPONDER_AUTO_AO=so_inadimplentes  # só inadimplentes
   WEBHOOK_RESPONDER_AUTO_AO=whitelist     # só números na lista
   ```

## URLs Importantes

| Serviço | URL |
|---------|-----|
| Painel Z-API | https://app.z-api.io |
| API Local | http://localhost:5000 |
| API AWS | http://15.228.231.24:5000 |
| Webhook | `POST /api/webhook/zapi` |
| Dashboard | http://localhost:5000/dashboard |
| Docs Swagger | http://localhost:5000/docs |
