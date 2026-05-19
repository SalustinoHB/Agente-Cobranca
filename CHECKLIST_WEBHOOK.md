# ✅ Checklist — Webhook Configurado

## O que foi feito agora

### 1. Painel Z-API
- ✅ Acessado: https://app.z-api.io/app/instances/visualization/3F3504716F44324E0D095EE982B712E3
- ✅ Configurado webhook "Ao receber": `http://15.228.231.24:5000/api/webhook/zapi`
- ✅ Salvo com sucesso

### 2. Código do Agente (atualizado)
- ✅ `sender.py` — Retry automático (3 tentativas), verificação de conexão, delay humanizado
- ✅ `templates.py` — 2-3 variações por etapa (evita padrão robótico)
- ✅ `regua.py` — Passa seed pra templates (consistência por unidade)
- ✅ `main.py` — CLI avançado: `--relatorio`, `--status`, `--enviar-teste`, `--blacklist`
- ✅ `state.py` — Métricas: `total_envios()`, `total_blacklist()`, `listar_blacklist()`
- ✅ `webhook.py` — Auto-responder com delay 3-8s, memória de conversa, variações

---

## 🔍 Verificar se está funcionando

### Passo 1: Verificar se API está rodando na AWS

Abra o navegador e acesse:
```
http://15.228.231.24:5000/
```

Deve retornar algo como:
```json
{
  "servico": "Agente Cobrança Renaissance",
  "modo": "DRY-RUN",
  ...
}
```

**Se não carregar**, a API não está no ar. Você precisa:
1. Conectar na EC2 via SSH
2. Verificar se o Docker está rodando: `docker ps`
3. Subir a API: `docker-compose -f docker-compose-zapi.yml up -d`

---

### Passo 2: Testar webhook localmente (sem depender do Z-API)

No servidor AWS (SSH):
```bash
cd /opt/cobranca-renaissance
python teste_webhook_local.py
```

Ou via curl direto:
```bash
curl -X POST http://localhost:5000/api/webhook/zapi \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "5584991627655",
    "messageId": "TESTE_001",
    "text": "Oi, já paguei o boleto",
    "fromMe": false,
    "isGroup": false,
    "senderName": "Murilo"
  }'
```

---

### Passo 3: Testar com mensagem REAL do WhatsApp

1. Envie uma mensagem para o número do chip conectado no Z-API
2. O Z-API vai disparar o webhook pra sua API
3. A API vai classificar a intenção e responder automaticamente
4. Verifique os logs: `docker logs cobranca-api -f`

---

## 🛠️ Se precisar subir a API na AWS

Conecte na EC2:
```bash
ssh -i "cobranca-renaissance-key.pem" ubuntu@15.228.231.24
```

No servidor:
```bash
cd /opt/cobranca-renaissance

# Verificar status
docker ps

# Se não estiver rodando, subir:
docker-compose -f docker-compose-zapi.yml up -d

# Ver logs
docker logs cobranca-api -f
```

---

## 📋 Resumo dos comandos CLI disponíveis

```bash
# Relatório bonito no terminal
python -m agente.main --relatorio

# Status rápido
python -m agente.main --status

# Enviar teste
python -m agente.main --enviar-teste 5584999999999 "Oi, teste"

# Blacklist
python -m agente.main --blacklist list
python -m agente.main --blacklist add 5584999999999
python -m agente.main --blacklist remove 5584999999999

# Régua dry-run
python -m agente.main --once --dry-run

# Régua real
python -m agente.main --once
```

---

## ⚠️ Importante

O webhook está configurado no Z-API, mas **só funciona se a API estiver rodando** na AWS. Se a EC2 estiver desligada ou o Docker parado, o Z-API vai receber erro 404/Connection Refused e pode desativar o webhook após várias falhas.

**Recomendação:** Suba a API na AWS e faça um teste real enviando "Oi" para o número do chip.
