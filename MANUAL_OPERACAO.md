# Manual de Operação — Agente Cobrança Renaissance

> Versão 0.2 — para Paulo, Eduardo e Murilo
> Stack: FastAPI + APScheduler + SQLite + Playwright + WhatsApp (Baileys/Z-API/Evolution)

Este documento cobre as operações do dia a dia: monitorar, ajustar contatos, pausar envios, aprovar mensagens, lidar com problemas comuns.

Convenções:
- Todas as chamadas usam `Authorization: Bearer $API_TOKEN`. Substitua `<TOKEN>` nos exemplos.
- Base URL no servidor padrão: `http://localhost:5000`. Em produção use o domínio configurado.
- Modo seguro é o default: `ENVIAR_DE_VERDADE=false` no `.env` significa dry-run (não envia).

---

## 1. Verificar o que está rodando

### Status geral

```bash
curl -s http://localhost:5000/api/status \
  -H "Authorization: Bearer <TOKEN>" | jq
```

Retorna: modo (REAL/DRY-RUN), backend (baileys/zapi/evolution/dryrun), WhatsApp conectado, enviados hoje, base atualizada quando, último scraper.

### Status detalhado do WhatsApp

```bash
curl -s http://localhost:5000/api/whatsapp/status \
  -H "Authorization: Bearer <TOKEN>" | jq
```

### Dashboard visual

Abra no navegador: `http://localhost:5000/dashboard`

Cole o `API_TOKEN` no topo, salve. O painel atualiza a cada 30 segundos sozinho.

---

## 2. Adicionar novo inadimplente

1. Editar `agente/data/contatos.json` adicionando a unidade:

```json
{
  "unidade": "0103",
  "nome": "FULANO DE TAL",
  "whatsapp": "+5584999999999",
  "email": "fulano@exemplo.com"
}
```

2. Salvar o arquivo.
3. Sincronizar a base do Superlógica:

```bash
curl -X POST http://localhost:5000/api/sincronizar \
  -H "Authorization: Bearer <TOKEN>"
```

4. Confirmar que apareceu:

```bash
curl -s "http://localhost:5000/api/unidades/0103" \
  -H "Authorization: Bearer <TOKEN>" | jq
```

Não precisa reiniciar o serviço — a base é relida a cada execução.

---

## 3. Pausar a régua

### Opção A — Pausa total via .env

Editar `.env`:

```
ENVIAR_DE_VERDADE=false
```

Reiniciar o container:

```bash
docker compose restart agente
```

O scheduler continua rodando, mas tudo vira dry-run (nada chega no WhatsApp).

### Opção B — Pausar só uma pessoa

Adicionar à blacklist (ver seção 6).

---

## 4. Ver histórico

### Últimos 50 envios

```bash
curl -s "http://localhost:5000/api/historico?limit=50" \
  -H "Authorization: Bearer <TOKEN>" | jq
```

### Resumo do dia

```bash
curl -s http://localhost:5000/api/historico/hoje \
  -H "Authorization: Bearer <TOKEN>" | jq
```

Retorna: enviados (reais), falhas, dry_run, total.

### Inspeção direta (no servidor)

```bash
docker compose exec agente python -m agente.state --recent
docker compose exec agente python -m agente.state --hoje
```

---

## 5. Fluxo de aprovação (recomendado pra começar em produção)

A ideia: rodar a régua em modo "preview", revisar as mensagens, e só depois confirmar o envio real. Isso evita disparos errados nas primeiras semanas.

### Passo 1 — Gerar preview

```bash
curl -X POST http://localhost:5000/api/aprovacao/preview \
  -H "Authorization: Bearer <TOKEN>" | jq
```

Retorna a lista de candidatos com a mensagem renderizada de cada um. Também grava em `/data/pendentes.json`.

### Passo 2 — Revisar

```bash
curl -s http://localhost:5000/api/aprovacao/pendentes \
  -H "Authorization: Bearer <TOKEN>" | jq '.candidatos[] | {unidade, nome, etapa_codigo, texto}'
```

Ou abre o dashboard e clica em "Ver mensagem" em cada card.

### Passo 3 — Confirmar

Aprovar TODOS:

```bash
curl -X POST http://localhost:5000/api/aprovacao/confirmar \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"todos": true}'
```

Aprovar específicos (use os `boleto_id` do preview):

```bash
curl -X POST http://localhost:5000/api/aprovacao/confirmar \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"ids": ["BOLETO_ID_1", "BOLETO_ID_2"]}'
```

> Importante: pra confirmar com envio real, `ENVIAR_DE_VERDADE` precisa estar `true` no `.env`. Caso contrário, o sistema confirma mas grava como dry-run.

---

## 6. Blacklist

### Adicionar

```bash
curl -X POST http://localhost:5000/api/blacklist \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"whatsapp": "+5584999999999", "motivo": "Em acordo judicial"}'
```

### Remover

```bash
curl -X DELETE http://localhost:5000/api/blacklist/+5584999999999 \
  -H "Authorization: Bearer <TOKEN>"
```

Casos onde adicionar à blacklist:
- Inadimplente entrou em acordo extrajudicial direto com a administradora
- Caso foi pro jurídico (ex: RAIMUNDO NONATO, 2702)
- Solicitação formal do morador via canal oficial
- Número errado / não é mais do morador

---

## 7. Envio manual avulso

Pra mandar uma mensagem ad-hoc (fora da régua):

```bash
curl -X POST http://localhost:5000/api/mensagem \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
        "whatsapp": "+5584999999999",
        "texto": "Olá, segue o link da 2ª via: https://...",
        "forcar_envio": false
      }'
```

`forcar_envio: true` ignora dry-run (use com EXTREMA cautela — só com aprovação do Murilo).

---

## 8. Trocar o backend de WhatsApp

No `.env`, escolha um:

```
SENDER_TYPE=dryrun     # padrão, não envia nada
SENDER_TYPE=baileys    # Baileys self-hosted
SENDER_TYPE=zapi       # Z-API
SENDER_TYPE=evolution  # Evolution API (legado)
```

Cada backend tem suas variáveis (ver `.env.example`):

- **Baileys**: `BAILEYS_URL`, `BAILEYS_API_KEY`
- **Z-API**: `ZAPI_INSTANCE_URL`, `ZAPI_TOKEN`
- **Evolution**: `EVOLUTION_URL`, `EVOLUTION_API_KEY`, `EVOLUTION_INSTANCE`

Reiniciar o serviço após mudar:

```bash
docker compose restart agente
```

---

## 9. Problemas comuns

### WhatsApp desconectou

Sintoma: `/api/status` retorna `whatsapp_conectado: false`.

Solução:
1. Acessar o painel do backend (Baileys/Z-API/Evolution) e re-escanear o QR.
2. Confirmar reconexão: `curl /api/whatsapp/status`.
3. Re-rodar régua manualmente se já passou da janela:
   ```bash
   docker compose exec agente python -m agente.main --once
   ```

### Scraper falhou

Sintoma: `/api/status` mostra `scraper_ultima_run.sucesso: false`.

Causa comum: cookie do Superlógica expirou.

Solução:
1. Logar no Superlógica via navegador.
2. Exportar cookies (extensão tipo "EditThisCookie") pro arquivo `/data/superlogica_cookies.json`.
3. Tentar de novo:
   ```bash
   curl -X POST http://localhost:5000/api/sincronizar \
     -H "Authorization: Bearer <TOKEN>"
   ```

### Mensagem não entregue (status falha)

1. Olha o erro no histórico:
   ```bash
   curl -s "http://localhost:5000/api/historico?limit=10" \
     -H "Authorization: Bearer <TOKEN>" | jq '.envios[] | select(.sucesso==false)'
   ```
2. Erros comuns:
   - `HTTP 401` → token do sender errado
   - `HTTP 400` + `not a WhatsApp user` → número não tem WhatsApp ativo
   - `HTTP 429` → muitas mensagens rápido demais, aumentar `INTERVALO_ENTRE_ENVIOS_SEGUNDOS`
3. Confirma o número direto no WhatsApp Web.

### Mensagem duplicada

Não acontece pelo design: o `state.db` tem UNIQUE em (boleto_id, etapa_codigo). Se aconteceu, alguém forçou via `/api/mensagem` ou rodou manual.

### Container caiu

```bash
docker compose ps              # ver status
docker compose logs --tail 200 agente    # ver últimos logs
docker compose restart agente
```

Logs persistentes em `/var/log/cobranca/app.log` (rotaciona 100MB, retém 30 dias).

---

## 10. Backups

Backup automático diário às 23h em `/data/backups/`. Mantém os últimos 30.

### Backup manual agora

```bash
docker compose exec agente python -m agente.backup
```

### Restaurar

```bash
# Parar o serviço
docker compose stop agente

# Copiar o backup desejado pro lugar do state.db
cp /data/backups/state_20260513_230000.db /data/state.db

# Subir de volta
docker compose start agente
```

---

## 11. Os 5 inadimplentes atuais (referência rápida)

| Apto | Nome                   | Valor       | Atraso | Status                            |
|------|------------------------|-------------|--------|------------------------------------|
| 0602 | MARCO ANTONIO MARTINS  | R$ 1.596,04 | 7 d    | normal                             |
| 0801 | PAULO EDUARDO MORAES   | R$ 1.697,39 | 7 d    | normal                             |
| 0802 | LUCIANA GUERRA BRANDÃO | R$ 1.907,23 | —      | em acordo (não cobrar pela régua)  |
| 2602 | BRUNALDO BIGI          | R$ 13.350,61| 197 d  | crônico (4 boletos)                |
| 2702 | RAIMUNDO NONATO        | —           | —      | BLACKLIST — jurídico               |

---

## 12. Contatos

- **Operação dia a dia**: Paulo / Eduardo
- **Configuração/infra**: Murilo (`muriloheitor@drnuvio.com`)
- **Jurídico/casos especiais**: Pratika
