"""
tunnel.py — Sobe a API local e cria um túnel público GRÁTIS
Usando bore (sem cadastro, sem ngrok)

Passo 1: Roda isso daqui
Passo 2: Vai no painel Z-API e muda o webhook pra URL que aparecer
Passo 3: Envia mensagem do seu WhatsApp pro chip Z-API
Passo 4: O agente responde automaticamente!
"""

import subprocess
import sys
import os
import json
import urllib.request
import time
import threading
import signal

API_PORT = 5005

def start_api():
    """Sobe a API local"""
    os.chdir(os.path.join(os.path.dirname(__file__)))
    cmd = [sys.executable, "-m", "uvicorn", "agente.api:app", "--host", "0.0.0.0", "--port", str(API_PORT)]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return proc

def find_public_url():
    """Tenta várias alternativas de túnel gratuito"""
    # Tenta localhost.run (SSH, sem cadastro)
    print("🔄 Conectando ao localhost.run...")
    print("   Pressione Enter quando aparecer 'Ready, you can use your tunnel'")
    
    # Abre SSH tunnel
    ssh_cmd = ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ServerAliveInterval=60",
               "-R", f"80:localhost:{API_PORT}", "nokey@localhost.run"]
    proc = subprocess.Popen(ssh_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    
    url = None
    for line in proc.stdout:
        print(f"   {line.strip()}")
        if "https://" in line and ".localhost.run" in line:
            url = line.strip().split()[-1].strip()
            break
    
    return url, proc

def main():
    print("=" * 55)
    print("🔥  TÚNEL PÚBLICO PARA TESTE NO WHATSAPP")
    print("=" * 55)
    print()
    print("1️⃣  Subindo API local...")
    api_proc = start_api()
    time.sleep(3)
    print("   ✅ API rodando em http://localhost:5005")
    print()
    print("2️⃣  Criando túnel público (localhost.run)...")
    print("   ⏳ Aguarde... pode levar 10-20s")
    print()
    
    url, ssh_proc = find_public_url()
    
    if url:
        webhook_url = f"{url}/api/webhook/zapi"
        print()
        print("=" * 55)
        print("✅  TÚNEL ATIVO!")
        print("=" * 55)
        print()
        print(f"📡 URL do webhook:")
        print(f"   {webhook_url}")
        print()
        print("3️⃣  Agora configure no painel Z-API:")
        print("   https://app.z-api.io/app/instances/visualization/3F3504716F44324E0D095EE982B712E3")
        print()
        print("   → Vá em 'Webhooks e configurações gerais'")
        print("   → Cole a URL acima no campo 'Ao receber'")
        print("   → Clique em Salvar")
        print()
        print("4️⃣  Envie uma mensagem do SEU WhatsApp")
        print("   para o número do chip conectado no Z-API")
        print()
        print("5️⃣  O agente vai responder automaticamente!")
        print()
        print("🛑  PRESSIONE CTRL+C PARA PARAR")
        print()
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Encerrando...")
    else:
        print("❌ Não foi possível criar túnel público")
        print()
        print("Alternativa: use http://localhost:5005 localmente")
    
    ssh_proc.terminate()
    api_proc.terminate()

if __name__ == "__main__":
    main()
