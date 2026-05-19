#!/bin/bash
# ============================================================
# Bootstrap EC2 — Agente Cobrança Renaissance
# Ubuntu 22.04 LTS (testado)
# ============================================================
# Uso:
#   1. Subir EC2 t3.small Ubuntu 22.04, security group abre 22, 8080
#   2. SSH no servidor
#   3. wget https://.../ec2_setup.sh && chmod +x ec2_setup.sh && ./ec2_setup.sh
# ============================================================

set -e

echo "🚀 Bootstrap EC2 — Agente Cobrança Renaissance"
echo "=============================================="

# ─── Atualizar sistema ───
echo "📦 Atualizando pacotes..."
sudo apt-get update -y
sudo apt-get upgrade -y

# ─── Instalar Docker + Docker Compose ───
echo "🐳 Instalando Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    rm get-docker.sh
    sudo usermod -aG docker ubuntu
    echo "✅ Docker instalado"
else
    echo "✓ Docker já presente"
fi

# Docker Compose plugin
if ! docker compose version &> /dev/null; then
    sudo apt-get install -y docker-compose-plugin
fi

# ─── Configurações de sistema ───
echo "⚙️  Configurando sistema..."

# Timezone
sudo timedatectl set-timezone America/Fortaleza

# Swap (necessário pra t3.small com 2GB RAM)
if [ ! -f /swapfile ]; then
    echo "💾 Criando swap 2GB..."
    sudo fallocate -l 2G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    echo "/swapfile none swap sw 0 0" | sudo tee -a /etc/fstab
fi

# Firewall (UFW)
echo "🔥 Configurando firewall..."
sudo ufw allow 22/tcp     # SSH
sudo ufw allow 8080/tcp   # Evolution API
sudo ufw --force enable

# ─── Diretórios ───
sudo mkdir -p /opt/cobranca-renaissance
sudo chown ubuntu:ubuntu /opt/cobranca-renaissance

echo ""
echo "✅ Bootstrap concluído!"
echo ""
echo "Próximos passos:"
echo "  1. Copie o projeto pra /opt/cobranca-renaissance/"
echo "     scp -r ./09-agente-cobranca-renaissance/ ubuntu@SEU_EC2_IP:/opt/cobranca-renaissance/"
echo ""
echo "  2. Configure .env:"
echo "     cd /opt/cobranca-renaissance/"
echo "     cp .env.example .env"
echo "     nano .env"
echo ""
echo "  3. Suba Docker:"
echo "     docker compose up -d"
echo ""
echo "  4. Conecte WhatsApp (Evolution):"
echo "     # Abrir http://SEU_EC2_IP:8080/manager"
echo "     # Criar instância 'cobranca-renaissance'"
echo "     # Escanear QR Code com o chip dedicado"
echo ""
echo "  5. Login na Superlógica (1x):"
echo "     docker compose exec agente python -m agente.scraper --login"
echo ""
echo "⚠️  IMPORTANTE: AGENTE INICIA EM MODO DRY-RUN."
echo "    Mude ENVIAR_DE_VERDADE=true no .env só quando estiver pronto."
echo ""
