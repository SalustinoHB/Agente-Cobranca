"""Parser APRIMORADO - Extrai TODOS os 56 condominios com seus condominos"""
import re, json

with open('_texto_completo.txt', 'r', encoding='utf-8') as f:
    texto = f.read()

# Divide em paginas numeradas
paginas = re.split(r'=== PÁGINA \d+ ===', texto)
paginas = [p.strip() for p in paginas if p.strip()]

print(f'Total de paginas: {len(paginas)}')

# Estrutura
condominios = {}
cond_atual = None
unidade = {}
unidades = []

def salvar_unidade():
    global unidade, unidades
    if unidade.get('apto') and unidade.get('nome'):
        nome = unidade['nome'].strip()
        if nome and len(nome) > 3 and not nome.isdigit():
            unidades.append(dict(unidade))
    unidade = {}

# Processa cada pagina em ordem
for pagina in paginas:
    linhas = pagina.split('\n')
    
    for linha in linhas:
        raw = linha.strip()
        if not raw:
            continue
        
        # Detecta condominio (W045A)
        if 'W045A' in raw:
            salvar_unidade()
            if cond_atual and unidades:
                if cond_atual not in condominios:
                    condominios[cond_atual] = []
                condominios[cond_atual].extend(unidades)
                unidades = []
            
            nome_raw = re.sub(r'W045A\s+', '', raw).strip()
            nome_raw = re.sub(r'\s*[-–]\s*PRATIKA\s*\(\d+\)', '', nome_raw).strip()
            nome_raw = re.sub(r'\(\d+\)$', '', nome_raw).strip()
            cond_atual = nome_raw.strip()
            continue
        
        if not cond_atual:
            continue
        
        # Pula cabecalhos
        if any(h in raw for h in ['Contatos das unidades', 'Unidade', 'Nome/Telefone', 'Fração', 'Tipo', 'Endereço', 'CPF/CNPJ', 'E-mail']):
            continue
        
        # Linha de unidade: 4 digitos
        m_apto = re.match(r'^(\d{4})\s', raw)
        if m_apto:
            salvar_unidade()
            unidade['apto'] = m_apto.group(1)
            # Pega o nome (restante da linha)
            resto = raw[m_apto.end():].strip()
            if resto and not resto.startswith('+') and not resto.startswith('0') and len(resto) > 2:
                unidade['nome'] = resto
            continue
        
        # Telefone (linha começando com +)
        if unidade and not unidade.get('fone') and (raw.startswith('+') or re.match(r'^55\d', raw)):
            unidade['fone'] = raw
            continue
        
        # Email
        if unidade and '@' in raw and not unidade.get('email'):
            unidade['email'] = raw
            continue

# Salva ultimo
salvar_unidade()
if cond_atual and unidades:
    if cond_atual not in condominios:
        condominios[cond_atual] = []
    condominios[cond_atual].extend(unidades)

# Remove condominios sem dados ou comerciais
excluir_nomes = ['OTICA', 'OTICAS', 'VANGUARDA', 'LOJA', 'QUIOSQUE', 'TRANSPORTE',
                 'ADVOCACIA', 'ARTIGOS OPTICOS', '2V TRANSPORTES', 'PAULO HENRIQUE',
                 'PRATIKA - ADMINISTRADORA', 'PRATIKA COBRANCA', 'LEMON FLAT',
                 'VERMELHA MOSSORO', 'PATOS QUIOSQUE', 'LIBERDADE MOSSORO',
                 'LOJA CAICO', 'KINGS - VANGUARDA']

for ex in excluir_nomes:
    condominios.pop(ex, None)

# Salva
with open('_todos_56_condominios.json', 'w', encoding='utf-8') as f:
    json.dump(condominios, f, indent=2, ensure_ascii=False)

# Mostra resumo
total_cond = 0
for nome, lista in sorted(condominios.items()):
    # Filtra unidades validas
    validas = [u for u in lista if u.get('nome') and len(u['nome']) > 4 
               and not any(x in u.get('nome','') for x in ['CIDADE', 'NATAL', 'PONTA', 'Capim', 'Torre', 'Bloco', 'LOTE', 'Rua'])]
    if validas:
        total_cond += len(validas)
        wpp = sum(1 for u in validas if u.get('fone'))
        print(f'{nome}: {len(validas)} condominos ({wpp} com telefone)')

print(f'\nTOTAL: {total_cond} condominos em {len(condominios)} condominios')
print(f'\nJSON salvo em _todos_56_condominios.json')