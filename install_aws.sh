#!/bin/bash
# =====================================================================
# 🚀 INSTALL COBRANÇA RENAISSANCE — AWS LIGHTSAIL
# =====================================================================
# Como usar:
#   1. Abra o Lightsail SSH no navegador (botão "Connect using SSH")
#   2. Cole TODO este arquivo no terminal (Ctrl+Shift+V no navegador)
#   3. Aperte Enter e aguarde ~5-10 min
#   4. Quando terminar, abra http://32.197.47.159:8080/manager
#   5. Quando o chip estiver pronto, escaneie o QR
# =====================================================================

set -e
cd ~

echo "=================================================================="
echo "🚀 Deploy Cobrança Renaissance — Iniciando..."
echo "=================================================================="

# ─── 1. Atualizar sistema ───────────────────────────────────────────
echo ""
echo "📦 [1/6] Atualizando sistema..."
sudo apt-get update -y
sudo apt-get upgrade -y -q

# ─── 2. Instalar Docker ─────────────────────────────────────────────
echo ""
echo "🐳 [2/6] Instalando Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    rm get-docker.sh
    sudo usermod -aG docker ubuntu
    sudo systemctl enable docker
    sudo systemctl start docker
    echo "✅ Docker instalado"
else
    echo "✓ Docker já presente"
fi

# Plugin Compose
sudo apt-get install -y docker-compose-plugin

# ─── 3. Swap (1GB RAM precisa de swap) ──────────────────────────────
echo ""
echo "💾 [3/6] Criando swap 2GB (necessário pra RAM 1GB)..."
if [ ! -f /swapfile ]; then
    sudo fallocate -l 2G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    echo "/swapfile none swap sw 0 0" | sudo tee -a /etc/fstab
    echo "✅ Swap 2GB criado"
else
    echo "✓ Swap já existe"
fi

# Otimização de memória pro Docker
echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf > /dev/null
sudo sysctl -p > /dev/null 2>&1 || true

# ─── 4. Criar estrutura de pastas ───────────────────────────────────
echo ""
echo "📁 [4/6] Criando estrutura de pastas..."
sudo mkdir -p /opt/cobranca-renaissance/data
sudo chown -R ubuntu:ubuntu /opt/cobranca-renaissance
cd /opt/cobranca-renaissance

# ─── 5. Criar docker-compose.yml (versão Evolution-first) ───────────
echo ""
echo "📝 [5/6] Criando docker-compose.yml..."

# Gera tokens fortes automaticamente
EVOLUTION_KEY=$(openssl rand -hex 32)
POSTGRES_PASS=$(openssl rand -hex 16)
API_TOKEN=$(openssl rand -hex 32)

# Salva tokens em arquivo separado
cat > tokens.txt <<EOF
# ═══════════════════════════════════════════════════════════
# 🔐 TOKENS GERADOS — GUARDAR EM LUGAR SEGURO!
# ═══════════════════════════════════════════════════════════
# Gerados em: $(date)
# Servidor: $(hostname) ($(curl -s ifconfig.me))
# ═══════════════════════════════════════════════════════════

EVOLUTION_API_KEY=${EVOLUTION_KEY}
POSTGRES_PASSWORD=${POSTGRES_PASS}
API_TOKEN=${API_TOKEN}

# Pra acessar o Evolution Manager:
#   URL: http://$(curl -s ifconfig.me):8080/manager
#   API Key: ${EVOLUTION_KEY}

# Pra acessar a API do agente (quando subir):
#   URL: http://$(curl -s ifconfig.me):5000
#   Header: Authorization: Bearer ${API_TOKEN}
EOF
chmod 600 tokens.txt

cat > docker-compose.yml <<COMPOSE_EOF
version: "3.9"

services:
  evolution:
    image: atendai/evolution-api:v2.1.1
    restart: unless-stopped
    ports:
      - "8080:8080"
    environment:
      - SERVER_TYPE=http
      - SERVER_PORT=8080
      - CORS_ORIGIN=*
      - AUTHENTICATION_API_KEY=${EVOLUTION_KEY}
      - DATABASE_ENABLED=true
      - DATABASE_PROVIDER=postgresql
      - DATABASE_CONNECTION_URI=postgresql://evolution:${POSTGRES_PASS}@postgres:5432/evolution
      - DATABASE_SAVE_DATA_INSTANCE=true
      - DATABASE_SAVE_DATA_NEW_MESSAGE=true
      - DATABASE_SAVE_MESSAGE_UPDATE=true
      - DATABASE_SAVE_DATA_CONTACTS=true
      - CACHE_REDIS_ENABLED=true
      - CACHE_REDIS_URI=redis://redis:6379
      - CACHE_REDIS_PREFIX_KEY=evolution
      - CACHE_REDIS_SAVE_INSTANCES=true
      - LANGUAGE=pt-BR
      - DEL_INSTANCE=false
      - QRCODE_LIMIT=30
    volumes:
      - ./data/evolution_instances:/evolution/instances
    networks:
      - cobranca
    depends_on:
      - postgres
      - redis
    deploy:
      resources:
        limits:
          memory: 600M

  postgres:
    image: postgres:15-alpine
    restart: unless-stopped
    environment:
      - POSTGRES_USER=evolution
      - POSTGRES_PASSWORD=${POSTGRES_PASS}
      - POSTGRES_DB=evolution
    volumes:
      - ./data/postgres:/var/lib/postgresql/data
    networks:
      - cobranca
    deploy:
      resources:
        limits:
          memory: 200M

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    command: redis-server --maxmemory 50mb --maxmemory-policy allkeys-lru
    volumes:
      - ./data/redis:/data
    networks:
      - cobranca
    deploy:
      resources:
        limits:
          memory: 80M

networks:
  cobranca:
    driver: bridge
COMPOSE_EOF

echo "✅ docker-compose.yml criado"

# ─── 6. Subir os containers ─────────────────────────────────────────
echo ""
echo "🚢 [6/6] Subindo containers (Evolution + Postgres + Redis)..."
sudo docker compose pull
sudo docker compose up -d

# Aguardar containers iniciarem
echo ""
echo "⏳ Aguardando 30s pros containers iniciarem..."
sleep 30

echo ""
echo "=================================================================="
echo "✅ DEPLOY CONCLUÍDO!"
echo "=================================================================="
echo ""
sudo docker compose ps
echo ""
echo "=================================================================="
echo "📋 PRÓXIMOS PASSOS:"
echo "=================================================================="
echo ""
echo "1. Veja seus tokens (anote em lugar seguro):"
echo "   cat tokens.txt"
echo ""
echo "2. Acesse o Evolution Manager pelo navegador:"
echo "   http://$(curl -s ifconfig.me):8080/manager"
echo "   API Key: ${EVOLUTION_KEY}"
echo ""
echo "3. Crie uma instância chamada 'cobranca-renaissance'"
echo ""
echo "4. Quando tiver o chip dedicado conectado:"
echo "   - WhatsApp do chip → Aparelhos Conectados → Conectar"
echo "   - Escanear o QR mostrado no Manager"
echo ""
echo "5. O agente Python será adicionado depois — comando ficará pronto"
echo "   pra apenas executar quando você quiser ativar o envio."
echo ""
echo "🔥 Status atual: Evolution rodando, pronto pra receber o chip!"
echo "=================================================================="
