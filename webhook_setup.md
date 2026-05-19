# Webhook Auto-Responder — Setup

Este documento descreve como configurar o auto-responder do agente de cobranca
para receber mensagens via Z-API e responder automaticamente.

---

## 1. Configuracao no painel Z-API

1. Acesse o painel Z-API: <https://app.z-api.io>
2. Selecione a instancia configurada (id `3F3116A80C20E2B7E02E36BEE236CCA1`).
3. Va em **Configuracoes -> Webhooks**.
4. No campo **"On message received" / "Ao receber"**, cole a URL publica:

   ```
   http://15.228.231.24:5000/api/webhook/zapi
   ```

5. Marque **Notificar tambem mensagens enviadas por mim?** = **NAO** (evita loop).
6. Salve. O painel Z-API costuma fazer um POST de teste — voce deve ver no log
   do servico um `[webhook] payload recebido: {...}` com `type=ReceivedCallback`
   ou similar.

> Caso esteja atras de NGINX/CloudFront, garanta que `POST` esta liberado e que
> o body JSON chega sem ser truncado. Limite recomendado: 2 MB.

---

## 2. Variaveis novas no `.env`

Adicione (ou atualize) no `.env` do servidor:

```env
# ─── Auto-responder ───
RESPOSTAS_AUTO_HABILITADAS=true

# Operador humano que recebe escalacoes (acordo, reclamacao, comprovante invalido)
OPERADOR_WHATSAPP=5584921627655

# Politica: todos | so_inadimplentes | whitelist
WEBHOOK_RESPONDER_AUTO_AO=todos

# (Opcional) lista de telefones autorizados se politica=whitelist
WEBHOOK_WHITELIST=5584999999999,5584988888888

# ─── Dados que vao na resposta de "pedido_2via_boleto" ───
# Pratika precisa preencher esses campos:
PIX_CONDOMINIO=
LINHA_DIGITAVEL_CONDOMINIO=

# ─── OCR (validacao de comprovantes) ───
# No Windows, aponte pro tesseract.exe se ele nao estiver no PATH:
# TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
TESSERACT_CMD=

# Pasta onde os comprovantes recebidos sao arquivados
COMPROVANTES_DIR=/data/comprovantes
COMPROVANTES_TMP_DIR=/data/comprovantes_tmp
```

Tambem precisa estar configurado (ja existem):

```env
SENDER_TYPE=zapi
ZAPI_INSTANCE_URL=https://api.z-api.io/instances/3F3116A80C20E2B7E02E36BEE236CCA1/token/C41548A184E0B3781A73FD14
ZAPI_CLIENT_TOKEN=F15aa798117d946e2bf37737584a75f61S
ENVIAR_DE_VERDADE=true
```

---

## 3. Dependencias do SO (Linux/EC2)

O OCR (Tesseract) precisa do binario instalado:

```bash
sudo apt-get update
sudo apt-get install -y tesseract-ocr tesseract-ocr-por poppler-utils
```

Verifica:

```bash
tesseract --version
# tesseract 4.x.x
pdftoppm -v
# poppler 22.x
```

Depois instale as libs Python (ja no `requirements.txt`):

```bash
pip install -r agente/requirements.txt
```

---

## 4. Estrutura do payload Z-API (referencia)

### Texto comum
```json
{
  "phone": "5584999999999",
  "fromMe": false,
  "isGroup": false,
  "type": "ReceivedCallback",
  "messageId": "3EB0...",
  "text": {"message": "ja paguei"},
  "senderName": "Marco Antonio",
  "momment": 1697000000
}
```

### Imagem (comprovante por print)
```json
{
  "phone": "5584999999999",
  "fromMe": false,
  "messageId": "3EB0...",
  "image": {
    "imageUrl": "https://files.z-api.io/.../imagem.jpg",
    "caption": "segue comprovante"
  }
}
```

### Documento (PDF)
```json
{
  "phone": "5584999999999",
  "fromMe": false,
  "messageId": "3EB0...",
  "document": {
    "documentUrl": "https://files.z-api.io/.../comprovante.pdf",
    "fileName": "comprovante.pdf",
    "caption": ""
  }
}
```

**Filtros aplicados:**
- `fromMe=true` -> ignora (evita loop)
- `isGroup=true` -> ignora (nao responde em grupo)
- `type != ReceivedCallback` -> ignora (so processa mensagem nova)
- mesmo `messageId` 2x -> ignora (idempotencia)

---

## 5. Como testar manualmente

### Via curl (sem precisar de Z-API)

```bash
# Teste 1: cliente disse que pagou
curl -X POST http://localhost:5000/api/webhook/testar \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "5584999999999",
    "fromMe": false,
    "messageId": "TEST-1",
    "text": {"message": "ja paguei"},
    "senderName": "Joao Teste"
  }'

# Teste 2: pedido de acordo (deve escalar pro operador)
curl -X POST http://localhost:5000/api/webhook/testar \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "5584999999999",
    "messageId": "TEST-2",
    "text": {"message": "posso parcelar em 3x?"}
  }'

# Teste 3: pedido de 2 via
curl -X POST http://localhost:5000/api/webhook/testar \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "5584999999999",
    "messageId": "TEST-3",
    "text": {"message": "manda o boleto"}
  }'

# Teste 4: reclamacao (escala)
curl -X POST http://localhost:5000/api/webhook/testar \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "5584999999999",
    "messageId": "TEST-4",
    "text": {"message": "nao devo nada, isso esta errado"}
  }'

# Teste 5: comprovante (imagem) - OCR roda no anexo
curl -X POST http://localhost:5000/api/webhook/testar \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "5584999999999",
    "messageId": "TEST-5",
    "image": {"imageUrl": "https://example.com/comprovante.jpg"}
  }'
```

### Via GET (mais simples pra teste rapido de texto)

```bash
curl "http://localhost:5000/api/webhook/zapi/test?phone=5584999999999&texto=ja+paguei"
```

### Via Swagger UI

Abra `http://localhost:5000/docs` e use a UI interativa.

---

## 6. Verificando no dashboard

Apos a config:

1. Va em `http://localhost:5000/dashboard` (ou `http://15.228.231.24:5000/dashboard`).
2. A secao **"Conversas"** mostra as ultimas 50 conversas com:
   - Telefone do cliente
   - Nome (se conhecido)
   - Ultima mensagem recebida
   - Intent classificado
   - Flag "escalado" (vermelho) ou "ok" (verde)
3. Clicando em **"Ver detalhes"** abre o historico completo (msgs recebidas + enviadas).

API REST equivalente:

```bash
# Lista todas as conversas
curl http://localhost:5000/api/webhook/conversas?token=$API_TOKEN

# Detalhes de uma conversa
curl "http://localhost:5000/api/webhook/conversas/5584999999999?token=$API_TOKEN"

# Comprovantes recebidos
curl http://localhost:5000/api/webhook/comprovantes
```

---

## 7. Fluxos suportados

| Intent do cliente             | Acao do bot                                       |
|-------------------------------|---------------------------------------------------|
| `confirmacao_pagamento`       | Pede comprovante                                  |
| `promessa_pagamento`          | Combina, marca aguardando_comprovante             |
| `pedido_2via_boleto`          | Manda valor + vencimento + PIX + linha digitavel  |
| `pedido_acordo`               | **Escala** pro operador (acordo/desconto/parcel.) |
| `reclamacao`                  | **Escala** pro operador                           |
| `saudacao`                    | Cumprimenta + se apresenta                        |
| `comprovante` (com imagem/PDF)| Baixa, roda OCR, valida valor (tolerancia 1%)     |
|                               |   * valido -> "Recebi! Vou conferir e dar baixa"  |
|                               |   * invalido -> **Escala** pro operador           |
| `desconhecida`                | Resposta de espera + **Escala** pro operador      |

---

## 8. Troubleshooting

**Z-API nao chama o webhook**
- Verifica se a URL no painel esta acessivel publicamente: `curl -X POST <url>`.
- Z-API exige resposta `200` em < 5s. Se o servidor demora, ele retenta e duplica.

**Bot manda resposta em loop**
- Confirma que `fromMe=true` esta sendo ignorado (procure no log: `ignorado: fromMe`).
- Confirme que `OPERADOR_WHATSAPP` nao e o mesmo numero da instancia Z-API.

**OCR sempre retorna `ocr_indisponivel`**
- Falta instalar o pacote do SO: `apt-get install tesseract-ocr tesseract-ocr-por`.
- Confirme com: `tesseract --version`.

**OCR retorna `valor_divergente` toda hora**
- Pode ser que o comprovante tem o valor com formato diferente do esperado.
- Cheque `raw_text` do registro em `/api/webhook/comprovantes`.
- Aumente a tolerancia: passe `tolerancia=0.05` (5%) no `contexto_boleto`.

**Mensagens recebidas nao aparecem no dashboard**
- Verifica `state.db`: `sqlite3 /data/state.db "SELECT * FROM mensagens_recebidas LIMIT 5;"`.
- Reinicia o servico: `systemctl restart agente-cobranca`.
