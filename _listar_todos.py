"""Extrai TODOS os condomínios residenciais do PDF"""
import re, json

with open('_texto_completo.txt', 'r', encoding='utf-8') as f:
    texto = f.read()

# Pega todas as ocorrências W045A
matches = re.findall(r'W045A[^\n]*', texto)

# Filtra só condomínios (ignora lojas, óticas, transportes, etc)
excluir = ['OTICA', 'OTICAS', 'VANGUARDA', 'LOJA', 'QUIOSQUE', 'TRANSPORTE', 
           'ADVOCACIA', 'ARTIGOS OPTICOS', 'PRATIKA - ADMINISTRADORA',
           'PRATIKA COBRANCA', 'PAULO HENRIQUE']

condominios_raw = []
for m in matches:
    # Extrai o nome
    nome = re.sub(r'W045A\s+', '', m).strip()
    # Remove numero de paginas do final
    nome = re.sub(r'\(\d+\)$', '', nome).strip()
    nome = nome.replace('- PRATIKA', '').strip()
    
    if any(excl in nome.upper() for excl in excluir):
        continue
    
    if nome and nome not in condominios_raw:
        condominios_raw.append(nome)

print(f'Total de condomínios encontrados: {len(condominios_raw)}')
print()
for i, c in enumerate(sorted(condominios_raw), 1):
    print(f'{i:2d}. {c}')

# Salva lista
with open('_lista_condominios.txt', 'w', encoding='utf-8') as f:
    for c in sorted(condominios_raw):
        f.write(c + '\n')