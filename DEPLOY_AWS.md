# 🚀 Deploy AWS — Passo a Passo

> Tempo total: ~45-60 min na primeira vez. Custo: ~US$ 10-15/mês.

---

## 1. Criar o servidor

### Opção A: Lightsail (mais simples, recomendado pra começar)

1. Acessar [aws.amazon.com/lightsail](https://aws.amazon.com/lightsail/)
2. **Create instance**
3. Configurações:
   - **Plataforma:** Linux/Unix
   - **Blueprint:** OS Only → Ubuntu 22.04 LTS
   - **Plano:** US$ 10/mês (2 vCPU, 2 GB RAM, 60 GB SSD) — recomendado
   - **Nome:** `cobranca-renaissance`
4. Em **Networking** depois, abrir portas:
   - 22 (SSH) — só do seu IP
   - 8080 (Evolution) — só do seu IP (segurança)
5. Criar **Static IP** e atribuir à instância (US$ 0)

### Opção B: EC2 (mais controle, ~mesmo preço)

- AMI: **Ubuntu 22.04 LTS**
- Instance type: **t3.small** (2 vCPU, 2 GB RAM)
- Storage: 30 GB gp3
- Security Group:
  - Port 22 (SSH) — Source: seu IP
  - Port 8080 (Evolution Manager) — Source: seu IP
- Elastic IP atribuído

---

## 2. Acessar o servidor

```bash
# Salve o .pem (chave SSH) que a AWS te deu
chmod 400 ~/Downloads/cobranca-renaissance.pem

# SSH
ssh -i ~/Downloads/cobranca-renaissance.pem ubuntu@SEU_IP_AQUI
```

---

## 3. Bootstrap (instala tudo)

```bash
# Dentro do servidor:
wget https://raw.githubusercontent.com/SEU_REPO/main/nuvem/ec2_setup.sh
chmod +x ec2_setup.sh
./ec2_setup.sh
```

Ou se ainda não tiver no Git, copia o `ec2_setup.sh` direto:

```bash
# Na sua máquina local:
scp -i ~/Downloads/cobranca-renaissance.pem \
    "nuvem/ec2_setup.sh" \
    ubuntu@SEU_IP:/tmp/

# No servidor:
chmod +x /tmp/ec2_setup.sh
/tmp/ec2_setup.sh
```

⚠️ Após instalar Docker, **faça logout e login de novo** pra o grupo `docker` valer.

---

## 4. Copiar o projeto pro servidor

```bash
# Na sua máquina local, dentro de Downloads/Serviço/:
scp -i ~/Downloads/cobranca-renaissance.pem -r \
    "09 - Agente Cobrança Renaissance/" \
    ubuntu@SEU_IP:/opt/cobranca-renaissance/
```

---

## 5. Configurar .env

```bash
# No servidor:
cd /opt/cobranca-renaissance/09\ -\ Agente\ Cobrança\ Renaissance/
cp .env.example .env
nano .env
```

**Mínimo a preencher antes do primeiro start:**

```bash
# Deixe FALSE no primeiro deploy (dry-run)
ENVIAR_DE_VERDADE=false

# Gere uma API key forte:
EVOLUTION_API_KEY=cole-uma-string-longa-aleatoria-aqui

# Postgres password (qualquer string forte)
POSTGRES_PASSWORD=outra-senha-forte-aqui

# Seu acesso ao Superlógica
SUPERLOGICA_URL=https://admin109865.superlogica.net
SUPERLOGICA_EMAIL=eduardo@pratika.com.br
SUPERLOGICA_CONDOMINIO_ID=14

# Seus dados de notificação
NOTIFICACAO_EMAIL=muriloheitor@drnuvio.com
ADMIN_WHATSAPP=+5584XXXXXXXX
```

Como gerar string forte:
```bash
openssl rand -hex 32
```

---

## 6. Subir Docker

```bash
docker compose up -d
docker compose ps   # confirma que os 4 containers tão UP
docker compose logs -f agente   # ver logs do agente
```

Containers esperados:
- `evolution` — Evolution API (porta 8080)
- `postgres` — banco da Evolution
- `redis` — cache da Evolution
- `agente` — Python (scheduler)

---

## 7. Conectar WhatsApp na Evolution

1. Abrir no navegador: `http://SEU_IP:8080/manager`
2. Login: cole sua `EVOLUTION_API_KEY` (a mesma do .env)
3. **Create Instance**:
   - Name: `cobranca-renaissance` (igual a `EVOLUTION_INSTANCE` no .env)
   - Token: (qualquer string)
   - Webhook: (deixar vazio por enquanto)
4. Clica em **QR Code**
5. **No celular do chip dedicado** (NÃO o chip pessoal):
   - WhatsApp → ⋮ → Aparelhos Conectados → Conectar
   - Escanear o QR
6. Aguardar status virar **open** (~10 segundos)

⚠️ **Importante:** o chip precisa ter WhatsApp ativo (chip recebeu SMS de cadastro). Recomendo:
- Chip Vivo Easy / TIM Easy / Claro Flex (~R$ 10)
- Ativar com o número limpo, sem usar antes
- Cadastrar nome do perfil: "Pratika Cobrança"

---

## 8. Login da Superlógica (1x)

O scraper precisa cookies de sessão do Superlógica. Login interativo (1x):

```bash
# Esse comando vai abrir browser visível no servidor — vai dar erro em headless
# Solução: rodar localmente na sua máquina e copiar os cookies pro servidor.

# Localmente (na sua máquina):
cd "09 - Agente Cobrança Renaissance/agente/"
pip install playwright python-dotenv loguru
playwright install chromium

# Cria .env local com SUPERLOGICA_URL e COOKIES_PATH=./superlogica_cookies.json
python -m agente.scraper --login

# Após logar, copia o arquivo pro servidor:
scp superlogica_cookies.json ubuntu@SEU_IP:/opt/cobranca-renaissance/.../agente/data/

# No servidor, mover pro volume Docker:
docker compose exec agente cp /app/agente/data/superlogica_cookies.json /data/
```

Cookies da Superlógica costumam durar 30 dias. Quando expirar, repetir o processo.

---

## 9. Validar (DRY-RUN)

```bash
# Roda um ciclo manual em DRY-RUN, forçando (ignora horário)
docker compose exec agente python -m agente.main --once --dry-run

# Ver últimos envios (deve ter os "DRY-RUN" listados)
docker compose exec agente python -m agente.state --recent

# Resumo do dia
docker compose exec agente python -m agente.state --hoje
```

Você deve ver:
- Quantos boletos foram processados
- Quais etapas seriam disparadas
- O texto exato que iria pra cada um

Se algo tá errado, **corrige antes de ligar o interruptor**.

---

## 10. Cron (já automático)

Os jobs rodam sozinhos:
- **07:00** — scraper Superlógica
- **08:00** — régua envia (se janela horária permitir)
- **18:30** — relatório do dia

Ver logs:
```bash
docker compose logs -f agente | grep -E "(scraper|régua|RESUMO)"
```

---

## 11. 🚦 LIGAR O INTERRUPTOR (envio real)

Depois de **pelo menos 1 semana em DRY-RUN** validando que tudo funciona certinho:

```bash
nano .env
# Mudar: ENVIAR_DE_VERDADE=true

docker compose restart agente
docker compose logs -f agente
```

⚠️ **A primeira semana real:** envia 1 só mensagem (canário). Acompanhe.
- Manualmente reduza a base pra 1 boleto de teste
- OU adicione 8 dos 9 vencidos na blacklist temporariamente

---

## Manutenção

### Backup do state.db (semanal)
```bash
docker compose exec agente cp /data/state.db /data/state.backup.$(date +%F).db
```

### Atualizar Evolution
```bash
docker compose pull evolution
docker compose up -d evolution
```

### Renovar cookies Superlógica (mensal)
Mesmo processo do passo 8.

### Adicionar à blacklist
```bash
docker compose exec agente python -c "
from agente.state import State
import os
s = State(os.getenv('DATABASE_PATH', '/data/state.db'))
s.adicionar_blacklist('+5584999999999', 'pediu pra parar')
"
```

---

## Custos estimados

| Item | Custo/mês |
|---|---|
| Lightsail US$ 10 plan | R$ 60 |
| Static IP | R$ 0 |
| Backup snapshot (opcional) | R$ 6 |
| Chip dedicado pré-pago | R$ 15-30 |
| **Total** | **R$ 80-95/mês** |

---

## Troubleshooting

### "Evolution não conecta"
```bash
docker compose logs evolution --tail 50
# Procure por erros de Postgres ou Redis
docker compose restart evolution
```

### "Scraper timeout"
- Cookies podem ter expirado → rodar `--login` de novo
- Superlógica pode ter mudado HTML → atualizar seletores em `scraper.py`

### "WhatsApp desconectou"
- Chip foi removido do app? Reconectar.
- Banimento? Verificar volume (não passar de 50/dia)
- Trocar chip se necessário

### "Agente não envia, mesmo com ENVIAR_DE_VERDADE=true"
- Está dentro da janela horária (09:00-18:00)?
- Hoje é fim de semana? (ENVIAR_SABADO/DOMINGO)
- Soft cap diário atingido?
- Já enviou essa etapa pra esse boleto antes? (idempotência)

---

*Atualizado: 12/05/2026*
