# 🏢 Agente Cobrança Renaissance — Pratika

Sistema de cobrança automática via WhatsApp com Z-API.

## Stack Técnica
- **Python 3.11** + **FastAPI** | **SQLite** | **Z-API** | **Playwright** | **Docker**

## Estrutura
```
agente/
├── api.py, webhook.py, sender.py     # API REST + Webhook + Envio
├── respostas.py, respostas_engine.py  # Classificador + Motor de respostas
├── templates.py                       # Régua de cobrança
├── conversa_memoria.py                # Memória + aprendizado
├── superlogica_boleto.py              # Busca boletos no Superlógica
├── escalacao.py, state.py             # Escalação humana + SQLite
├── scraper.py, regua.py               # Coleta + motor da régua
├── requirements.txt, Dockerfile
└── dashboard/                         # Painel web
```

## Funcionalidades
- ✅ Classificação de 8 intenções | ✅ Respostas personalizadas em tempo real
- ✅ 97+ variações combinatórias | ✅ Memória de conversa por contato
- ✅ Escalação silenciosa | ✅ Webhook Z-API | ✅ Dashboard | ✅ CLI

## Rodar Local
```bash
pip install -r agente/requirements.txt
playwright install chromium
uvicorn agente.api:app --host 0.0.0.0 --port 5005 --reload
```

---

## 🤖 Agente Cobrança Renaissance

> Sistema automático de cobrança de inadimplentes do condomínio Renaissance via WhatsApp.
> Roda na **AWS**, lê boletos da **Superlógica** todo dia, envia mensagens via **Evolution API** seguindo régua de **6 etapas**.

---

## 🎯 O que faz

1. **Toda manhã às 7h** — scraper Playwright loga na Superlógica do Eduardo (cookies salvos), baixa lista atualizada de boletos da Pratika Renaissance.
2. **Às 8h** — motor da régua lê base atualizada, calcula `dias_em_atraso` por boleto, decide qual etapa aplicar (D-3 / D-0 / D+1 / D+7 / D+15 / D+30).
3. **Envia via Evolution API** — uma mensagem por boleto, com intervalo de **3 minutos entre envios** (anti-banimento WhatsApp).
4. **Logga tudo** — quem foi cobrado, em qual etapa, quando, qual texto exato (SQLite `state.db`).
5. **Idempotente** — se o agente roda 2 vezes no mesmo dia, NÃO duplica envio.
6. **Para de cobrar** quando boleto vira `pago` na Superlógica.

---

## 🔒 Estado atual: DRY-RUN

**O agente NÃO envia mensagens de verdade até você ligar o interruptor.**

No `.env`:
```
ENVIAR_DE_VERDADE=false   # ← muda pra true quando quiser ativar
```

Enquanto em DRY-RUN, o agente:
- ✅ Roda o scraper normal
- ✅ Calcula etapas normal
- ✅ Renderiza mensagens normal
- ✅ Logga tudo em `state.db` (com flag `dry_run=true`)
- ❌ **NÃO envia mensagens**
- ✅ Manda relatório diário pra você por email/log avisando: "Hoje teriam sido enviadas X mensagens"

---

## 🏗️ Arquitetura

```
                      AWS EC2 (t3.small)
                      ─────────────────────
   Superlógica  →  scraper.py (Playwright, cron 7h)
                          ↓
                  data/renaissance.json
                          ↓
                      regua.py (cron 8h)
                          ↓
                       state.db (SQLite)
                          ↓
                      sender.py
                          ↓
                   Evolution API (Docker)
                          ↓
              📱 Chip dedicado cobrança
                          ↓
              💬 WhatsApp dos moradores
```

---

## 📁 Estrutura

```
09 - Agente Cobrança Renaissance/
├── README.md                  ← (você está aqui)
├── DEPLOY_AWS.md              ← guia de deploy na AWS
├── ARQUITETURA.md             ← detalhes técnicos
├── docker-compose.yml         ← Evolution + Agente + volumes
├── .env.example               ← copie pra .env e preencha
│
├── agente/
│   ├── main.py                ← orquestrador (cron 8h)
│   ├── scraper.py             ← Playwright Superlógica (cron 7h)
│   ├── regua.py               ← motor de etapas
│   ├── sender.py              ← cliente Evolution
│   ├── state.py               ← SQLite (log + idempotência)
│   ├── templates.py           ← 6 mensagens da régua
│   ├── requirements.txt
│   ├── Dockerfile
│   └── data/
│       ├── renaissance.json   ← base cacheada do scraper
│       ├── superlogica_cookies.json  ← cookies de sessão
│       └── state.db           ← SQLite (criado em runtime)
│
└── nuvem/
    ├── ec2_setup.sh           ← bootstrap inicial do EC2
    └── crontab.txt            ← cron jobs do servidor
```

---

## 🚀 Como subir (resumo)

Detalhes em `DEPLOY_AWS.md`. Resumo:

```bash
# 1. Criar EC2 t3.small Ubuntu 22.04
# 2. SSH no servidor
ssh ubuntu@SEU_EC2_IP

# 3. Bootstrap
curl -O https://raw.githubusercontent.com/.../ec2_setup.sh
chmod +x ec2_setup.sh
./ec2_setup.sh

# 4. Copiar projeto
scp -r 09-agente-cobranca-renaissance ubuntu@SEU_EC2_IP:/opt/

# 5. Configurar .env
cd /opt/09-agente-cobranca-renaissance
cp .env.example .env
nano .env  # preencher com seus dados

# 6. Subir Docker
docker compose up -d

# 7. Conectar chip WhatsApp na Evolution
# (abrir http://SEU_EC2_IP:8080/manager, escanear QR)

# 8. Salvar cookies da Superlógica (primeira vez)
docker compose exec agente python -m agente.scraper --login

# 9. Verificar dry-run
docker compose exec agente python -m agente.main --dry-run

# 10. Quando estiver tudo OK, ligar interruptor
nano .env  # mudar ENVIAR_DE_VERDADE=true
docker compose restart agente
```

---

## 🎚️ Variáveis principais (.env)

```bash
# === Envio ===
ENVIAR_DE_VERDADE=false                    # ← interruptor mestre
INTERVALO_ENTRE_ENVIOS_SEGUNDOS=180         # 3 min entre cada msg
SOFT_CAP_DIARIO=50                          # warning se passar
HORARIO_INICIO_ENVIO=09:00
HORARIO_FIM_ENVIO=18:00                     # não envia depois das 18h

# === Evolution API ===
EVOLUTION_URL=http://evolution:8080
EVOLUTION_API_KEY=sua-key-aqui
EVOLUTION_INSTANCE=cobranca-renaissance

# === Superlógica (scraper) ===
SUPERLOGICA_URL=https://admin109865.superlogica.net
SUPERLOGICA_EMAIL=eduardo@pratika.com.br
SUPERLOGICA_SENHA=                          # opcional, melhor usar cookies
SUPERLOGICA_CONDOMINIO_ID=14                # Renaissance

# === Notificação (relatório diário) ===
NOTIFICACAO_EMAIL=muriloheitor@drnuvio.com
NOTIFICACAO_WHATSAPP=+55XXXXXXXXX            # opcional

# === Banco ===
DATABASE_PATH=/data/state.db
BASE_JSON_PATH=/data/renaissance.json
```

---

## 📋 Régua de 6 etapas

| Etapa | Quando | Tom | Ação |
|---|---|---|---|
| **D-3** | 3 dias antes do vencimento | Lembrete suave | Texto educado, lembrete |
| **D-0** | Dia do vencimento | Direto, neutro | "Vence hoje, link do boleto" |
| **D+1** | 1 dia atrasado | Cobrança leve | "Boleto venceu ontem" |
| **D+7** | 1 semana atrasado | Mais firme | Juros mencionados |
| **D+15** | 2 semanas | Formal | Aviso de protocolo |
| **D+30** | 1 mês | Última | Aviso de protesto / jurídico |

Textos exatos em `agente/templates.py`. Personalização: `{nome}`, `{unidade}`, `{valor}`, `{vencimento}`, `{dias_atraso}`.

---

## 🛡️ Regras de segurança embutidas

1. **DRY-RUN por padrão** — não envia até `ENVIAR_DE_VERDADE=true`
2. **Idempotência** — não envia 2x a mesma etapa pro mesmo boleto
3. **Horário comercial** — só envia entre 09:00 e 18:00
4. **Intervalo 3 min** entre envios (anti-spam WhatsApp)
5. **Soft cap 50/dia** — passou disso, agente para e te avisa
6. **Skip pagos** — boletos com status `pago` na Superlógica não são cobrados
7. **Skip blacklist** — números em `data/blacklist.txt` nunca recebem
8. **Log completo** — toda mensagem fica em `state.db` com timestamp, texto e response da Evolution

---

## 📊 Como monitorar

```bash
# Ver últimas 10 mensagens enviadas
docker compose exec agente python -m agente.state --recent

# Ver inadimplentes ativos hoje
docker compose exec agente python -m agente.regua --simular

# Ver erros recentes
docker compose logs agente --tail 100

# Ver Evolution status
curl http://localhost:8080/instance/connectionState/cobranca-renaissance
```

---

## 🚨 Em caso de problema

| Problema | Causa provável | Solução |
|---|---|---|
| Cookies Superlógica expirados | 30 dias sem login | `docker compose exec agente python -m agente.scraper --login` |
| Evolution desconectou | WhatsApp deslogou | Abrir `http://EC2_IP:8080/manager`, escanear QR novo |
| Mensagem duplicada | Bug raro no state.db | Inspecionar `state.db`, deletar linha duplicada |
| WhatsApp banido | Excedeu volume seguro | Aguardar 24-48h, trocar chip se necessário |

---

## 🗺️ Roadmap

- [x] Régua de 6 etapas definida
- [x] Templates renderizados (9 vencidos atuais)
- [x] Esqueleto do projeto
- [ ] **Scraper Superlógica com Playwright** ← aqui
- [ ] **Evolution API config + chip**
- [ ] **Deploy AWS**
- [ ] **Validação DRY-RUN 1 semana**
- [ ] **Ativação real (interruptor on)**
- [ ] Próximas fases:
  - [ ] Dashboard web (status de cada inadimplente)
  - [ ] Respostas inbound (cliente responde "já paguei", agente reconhece)
  - [ ] Integração com agente Triador
  - [ ] Geração 2ª via boleto automática

---

*Pratika · Renaissance · Maio/2026*
