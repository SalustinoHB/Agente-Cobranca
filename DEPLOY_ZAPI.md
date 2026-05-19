# 🚀 Deploy Z-API — Agente Cobrança Renaissance

> **Novo guia:** Deploy usando Z-API (recomendado).  
> Não precisa subir Evolution/Postgres/Redis na EC2 — economiza RAM e evita ban WhatsApp.

---

## ✅ O que você precisa antes

1. **Conta Z-API** criada em [https://z-api.io](https://z-api.io)
2. **Instância ativa** com chip WhatsApp conectado
3. **Instance URL** e **Client Token** do painel Z-API
4. **Servidor AWS** já criado (IP público, porta 5000 aberta)
5. **Chave SSH** `.pem` salva no computador

---

## 🎯 Deploy em 2 passos

### Passo 1 — Preencher o `.env` local

Abra `09 - Agente Cobrança Renaissance/.env` (crie a partir do `.env.example`) e preencha:

```bash
SENDER_TYPE=zapi
ENVIAR_DE_VERDADE=false

ZAPI_INSTANCE_URL=https://api.z-api.io/instances/SEU_INSTANCE/token/SEU_TOKEN
ZAPI_TOKEN=SEU_CLIENT_TOKEN

API_TOKEN=GERE_UM_TOKEN_SEGURO_AQUI
```

> 💡 **Não versione o `.env` no Git.** Já está no `.gitignore`.

---

### Passo 2 — Rodar o deploy

Duplo-clique em:

```
C:\Users\admin\Downloads\deploy_aws.bat
```

Isso vai:
1. Empacotar projeto local (inclui `docker-compose-zapi.yml`)
2. Enviar pra EC2 via SCP
3. Rodar `deploy_v2.sh` no servidor
4. O script detecta `SENDER_TYPE=zapi` e usa `docker-compose-zapi.yml`

---

## 🌐 Após o deploy: testar

Abra no navegador:

**`http://SEU_IP_DA_EC2:5000/`**

Deve retornar:
```json
{
  "servico": "Agente Cobrança Renaissance",
  "modo": "DRY-RUN",
  ...
}
```

### Testar status Z-API

```bash
curl http://SEU_IP:5000/api/whatsapp/status \
  -H "Authorization: Bearer SEU_API_TOKEN"
```

Retorno esperado (se Z-API conectada):
```json
{
  "backend": "zapi",
  "conectado": true,
  "dry_run": true
}
```

---

## 🚦 Ativar envio real

Só depois de testar dry-run e confirmar que mensagens renderizam corretamente:

```bash
# No servidor EC2 (SSH)
sed -i 's/ENVIAR_DE_VERDADE=false/ENVIAR_DE_VERDADE=true/' /opt/cobranca-renaissance/.env
docker restart cobranca-api
```

Ou via API (com token):
```bash
curl -X POST http://SEU_IP:5000/api/config \
  -H "Authorization: Bearer SEU_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"ENVIAR_DE_VERDADE": "true"}'
```

---

## 🛠️ Troubleshooting

| Problema | Solução |
|---|---|
| "Backend detectado: dryrun" | `.env` não foi copiado pro servidor. Verifique `scp`. |
| Z-API retorna `connected: false` | Chip não conectado no painel Z-API. Conecte primeiro. |
| Porta 5000 não responde | Verifique Security Group AWS — precisa liberar TCP 5000. |
| "Token inválido" | `API_TOKEN` no `.env` do servidor difere do usado no `curl`. |

---

## 📦 Arquivos alterados para Z-API

- `docker-compose-zapi.yml` — novo (sem Evolution/Postgres/Redis)
- `docker-compose.yml` — mantido pra quem quiser Evolution
- `.env.example` — com comentários Z-API
- `deploy_v2.sh` — detecta backend automaticamente
- `deploy_aws.bat` — inclui compose Z-API no bundle

---

## 💬 Próximos passos

1. Corrigir DDDs dos 27 contatos no Superlógica
2. Coletar telefone dos 6 sem cadastro
3. Rodar `/api/aprovacao/preview` → revisar mensagens → confirmar 1 envio de teste
4. Se chegou: ligar `ENVIAR_DE_VERDADE=true`
