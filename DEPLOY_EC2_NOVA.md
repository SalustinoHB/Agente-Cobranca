# 🚀 DEPLOY EC2 NOVA — 3 comandos no PowerShell

> EC2 t3.small (2GB RAM) em São Paulo, criada e rodando agora.
> Tempo: **10 min** pra ter Evolution + WhatsApp conectado.

---

## ✅ Dados da máquina

| Item | Valor |
|---|---|
| **Nome** | cobranca-renaissance |
| **ID** | i-07b07038f7fb05fd3 |
| **Tipo** | t3.small (2 vCPU, **2 GB RAM**) |
| **Região** | sa-east-1 (São Paulo) |
| **IP público** | **`15.228.231.24`** |
| **DNS** | ec2-15-228-231-24.sa-east-1.compute.amazonaws.com |
| **User SSH** | `ubuntu` |
| **Chave SSH** | `C:\Users\admin\Downloads\cobranca-renaissance-key.pem` |

---

## 🎯 OS 3 COMANDOS — copia e cola um por vez no PowerShell

Abre o **PowerShell** (tecla Win → "powershell" → Enter) e cola **um por vez**:

---

### 📌 Comando 1 — Proteger a chave SSH (1 segundo)

```powershell
icacls "C:\Users\admin\Downloads\cobranca-renaissance-key.pem" /inheritance:r /grant:r "$($env:USERNAME):(R)"
```

> Deve aparecer: "Processed 1 file."

---

### 📌 Comando 2 — Abrir portas 5000 e 8080 no Security Group (via AWS CLI ou manualmente)

**Caminho mais simples — via console AWS (30 segundos):**
1. Abra: https://sa-east-1.console.aws.amazon.com/ec2/home?region=sa-east-1#SecurityGroups:
2. Procure o security group **da cobranca-renaissance** (vai ter "launch-wizard-X" no nome)
3. Clica nele → aba **Inbound rules** → **Edit inbound rules**
4. **Add rule** (2 vezes):
   - Type: Custom TCP · Port: **5000** · Source: Anywhere-IPv4 (0.0.0.0/0)
   - Type: Custom TCP · Port: **8080** · Source: Anywhere-IPv4 (0.0.0.0/0)
5. **Save rules**

---

### 📌 Comando 3 — Enviar script + Instalar tudo (8-10 min)

```powershell
scp -o StrictHostKeyChecking=no -i "C:\Users\admin\Downloads\cobranca-renaissance-key.pem" "C:\Users\admin\Downloads\Serviço\09 - Agente Cobrança Renaissance\install_aws.sh" ubuntu@15.228.231.24:~/
```

E logo em seguida:

```powershell
ssh -o StrictHostKeyChecking=no -i "C:\Users\admin\Downloads\cobranca-renaissance-key.pem" ubuntu@15.228.231.24 "chmod +x install_aws.sh && bash install_aws.sh"
```

> Demora **8-10 min**. Vai aparecer várias linhas. **NÃO cancela**. No fim aparece "✅ DEPLOY CONCLUÍDO!" com os 3 tokens.

---

## ⚡ O que vai acontecer no Comando 3

```
[1/6] Atualizando sistema...        (~1 min)
[2/6] Instalando Docker...          (~2 min)
[3/6] Criando swap 2GB...           (~30s) ← agora desnecessário com 2GB RAM mas ok
[4/6] Criando estrutura...          (~5s)
[5/6] docker-compose.yml + tokens... (~5s)
[6/6] Subindo Evolution + Postgres + Redis... (~3 min)
✅ DEPLOY CONCLUÍDO!
```

Aparece tokens tipo:
```
EVOLUTION_API_KEY=abc123...
POSTGRES_PASSWORD=def456...
API_TOKEN=ghi789...
```

**👉 Copia esses 3 tokens e cola aqui no chat.**

---

## 🌐 Quando terminar: testar Evolution

Abre no navegador:

**http://15.228.231.24:8080/manager**

Cola a `EVOLUTION_API_KEY` que apareceu nos tokens.

Aí eu crio uma instância, gero **Pairing Code** (código de 8 letras), você digita no WhatsApp e pronto — dispara as mensagens.

---

## 🚨 Se der erro

| Erro | Solução |
|---|---|
| "Permission denied (publickey)" | Comando 1 não rodou. Roda o comando 1 primeiro. |
| "Connection refused / timeout" | Aguarda 1-2 min pra EC2 estabilizar. Tenta de novo. |
| "scp/ssh: command not found" | Instala OpenSSH Client (Configurações Windows → Apps → Recursos opcionais) |
| Travou no `apt-get` | Aguarde — primeira vez demora. NÃO cancele. |

---

## 💰 Custo

- **t3.small** em sa-east-1: **~US$ 17/mês** (R$ 90)
- Armazenamento 8GB: **~US$ 1/mês**
- Total: **~US$ 18/mês (R$ 95)** — sem free tier desta vez

---

## 🎁 Bônus: quando estiver tudo pronto

Quando o WhatsApp estiver conectado, vou:
1. ✅ Listar **3 contatos recentes** via API Evolution
2. ✅ Mostrar **draft de mensagem** pra cada um
3. ✅ Pedir **aprovação** sua antes de cada envio
4. ✅ Mandar via API
5. ✅ Você vê chegar no seu WhatsApp

**E a régua de cobrança fica pronta pra disparo automatizado** quando você decidir.

---

*Atualizado: 12/05/2026 · Servidor: 15.228.231.24 · Região: sa-east-1*
