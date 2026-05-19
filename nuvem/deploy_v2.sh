#!/bin/bash
# =====================================================================
# Deploy v2 - Cobranca Renaissance na EC2
# Suporta Z-API (recomendado) e Baileys/Evolution (legado)
# Roda direto na EC2 (chamado pelo deploy.bat do Windows)
# =====================================================================
set -e

PROJETO=/opt/cobranca-renaissance
DATA_DIR=$PROJETO/data
ENV_FILE=$PROJETO/.env

echo ""
echo "===================================================="
echo " Deploy v2 - Cobranca Renaissance"
echo "===================================================="
echo ""

# Detecta backend
SENDER_TYPE=$(grep -E '^SENDER_TYPE=' "$ENV_FILE" 2>/dev/null | cut -d'=' -f2 | tr -d '"' || echo "dryrun")
if [ -z "$SENDER_TYPE" ]; then
  SENDER_TYPE="dryrun"
fi
echo "Backend detectado: $SENDER_TYPE"

# ────────────────────────────────────────────────────────
echo "[1/9] Garantindo estrutura de diretorios..."
sudo mkdir -p $PROJETO/agente $DATA_DIR /var/log/cobranca /opt/backups
sudo chown -R ubuntu:ubuntu $PROJETO /var/log/cobranca /opt/backups

# ────────────────────────────────────────────────────────
echo "[2/9] Extraindo bundle..."
if [ -f /tmp/cobranca_bundle.tar.gz ]; then
  # Extrai para /tmp primeiro pra não sobrescrever .env existente
  tar xzf /tmp/cobranca_bundle.tar.gz -C /tmp/cobranca_extract_$$
  
  # Copia arquivos específicos (preserva .env existente)
  cp -r /tmp/cobranca_extract_$$/agente $PROJETO/ 2>/dev/null || true
  cp /tmp/cobranca_extract_$$/docker-compose-zapi.yml $PROJETO/ 2>/dev/null || true
  
  # Só copia .env se não existir
  if [ ! -f $ENV_FILE ]; then
    cp /tmp/cobranca_extract_$$/.env $ENV_FILE 2>/dev/null || true
    echo "  -> .env copiado do bundle"
  else
    echo "  -> .env já existe, preservado"
  fi
  
  rm -rf /tmp/cobranca_extract_$$
  echo "  -> bundle extraido"
else
  echo "  AVISO: /tmp/cobranca_bundle.tar.gz nao encontrado. Pulando extracao."
fi

# ────────────────────────────────────────────────────────
echo "[3/9] Garantindo .env basico..."
if [ ! -f $ENV_FILE ]; then
  cat > $ENV_FILE <<EOF
# Config minima - edite depois com dados reais
API_TOKEN=$(openssl rand -hex 16)
SENDER_TYPE=dryrun
ENVIAR_DE_VERDADE=false
BASE_JSON_PATH=/data/renaissance.json
CONTATOS_PATH=/data/contatos.json
DATABASE_PATH=/data/state.db
BACKUP_DIR=/data/backups
HORARIO_INICIO_ENVIO=09:00
HORARIO_FIM_ENVIO=18:00
INTERVALO_ENTRE_ENVIOS_SEGUNDOS=180
SOFT_CAP_DIARIO=50
ENVIAR_SABADO=false
ENVIAR_DOMINGO=false

# Z-API (preencher quando tiver conta)
# ZAPI_INSTANCE_URL=https://api.z-api.io/instances/XXX/token/YYY
# ZAPI_TOKEN=SEU_CLIENT_TOKEN
EOF
  echo "  -> .env criado com SENDER_TYPE=dryrun (seguro)"
else
  echo "  -> .env ja existe, mantido"
fi

# ────────────────────────────────────────────────────────
echo "[4/9] Instalando Docker + Docker Compose se nao tiver..."
if ! command -v docker &> /dev/null; then
  curl -fsSL https://get.docker.com | sudo sh
  sudo usermod -aG docker ubuntu
fi
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
  sudo apt-get update && sudo apt-get install -y docker-compose-plugin
fi
docker --version
docker compose version || docker-compose --version || true

# ────────────────────────────────────────────────────────
echo "[5/9] Build da imagem Docker..."
cd $PROJETO
if [ -f agente/Dockerfile ]; then
  sudo docker build -t cobranca-api:latest agente/
else
  echo "  AVISO: agente/Dockerfile nao encontrado"
fi

# ────────────────────────────────────────────────────────
echo "[6/9] Subindo stack..."
sudo docker stop cobranca-api 2>/dev/null || true
sudo docker rm cobranca-api 2>/dev/null || true

if [ "$SENDER_TYPE" = "zapi" ] && [ -f $PROJETO/docker-compose-zapi.yml ]; then
  echo "  -> Usando docker-compose-zapi.yml (sem Evolution/Postgres/Redis)"
  cd $PROJETO
  sudo docker compose -f docker-compose-zapi.yml down 2>/dev/null || true
  sudo docker compose -f docker-compose-zapi.yml up -d
elif [ -f $PROJETO/docker-compose.yml ]; then
  echo "  -> Usando docker-compose.yml (com Evolution + Postgres + Redis)"
  cd $PROJETO
  sudo docker compose down 2>/dev/null || true
  sudo docker compose up -d
else
  echo "  -> Usando docker run standalone (fallback)"
  sudo docker run -d \
    --name cobranca-api \
    --restart unless-stopped \
    -p 5000:5000 \
    --env-file $ENV_FILE \
    -v $DATA_DIR:/data \
    -v /var/log/cobranca:/var/log/cobranca \
    cobranca-api:latest
fi

sleep 5

# ────────────────────────────────────────────────────────
echo "[7/9] Reiniciando Baileys (se existir e for usado)..."
if [ "$SENDER_TYPE" = "baileys" ] && systemctl list-unit-files | grep -q baileys-cobranca; then
  sudo systemctl restart baileys-cobranca 2>/dev/null || true
  echo "  -> Baileys reiniciado"
else
  echo "  -> Baileys nao necessario para backend=$SENDER_TYPE"
fi

# ────────────────────────────────────────────────────────
echo "[8/9] Verificando..."
sleep 3
echo ""
echo "=== STATUS DOCKER ==="
sudo docker ps --filter name=cobranca --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
echo ""
echo "=== LOG ULTIMAS 20 LINHAS ==="
sudo docker logs --tail 20 cobranca-api 2>&1 || true
echo ""
echo "=== HEALTHCHECK ==="
curl -s http://localhost:5000/ | head -c 500
echo ""
echo ""

# ────────────────────────────────────────────────────────
echo "[9/9] Resumo..."
IP_PUBLICO=$(curl -s ifconfig.me 2>/dev/null || echo "IP_DESCONHECIDO")
echo ""
echo "===================================================="
echo " DEPLOY CONCLUIDO!"
echo "===================================================="
echo ""
echo " Backend:    $SENDER_TYPE"
echo " API:        http://$IP_PUBLICO:5000"
echo " Docs:       http://$IP_PUBLICO:5000/docs"
echo " Dashboard:  http://$IP_PUBLICO:5000/dashboard"
echo ""
echo " Proximos passos:"
echo "  1. Abrir .env e preencher ZAPI_INSTANCE_URL + ZAPI_TOKEN"
echo "  2. docker compose restart (ou docker restart cobranca-api)"
echo "  3. Conectar WhatsApp no painel da Z-API"
echo "  4. Testar /api/whatsapp/status"
echo "  5. Quando pronto: ENVIAR_DE_VERDADE=true"
echo ""
echo " Dashboard:  http://15.228.231.24:5000/dashboard"
echo ""
echo " Token API:  cat $ENV_FILE | grep API_TOKEN"
echo ""
echo " Modo atual: DRY-RUN (nao envia mensagens reais)"
echo " Pra ativar envio: editar $ENV_FILE -> ENVIAR_DE_VERDADE=true"
echo "                  + SENDER_TYPE=baileys (depois que WhatsApp conectar)"
echo ""
