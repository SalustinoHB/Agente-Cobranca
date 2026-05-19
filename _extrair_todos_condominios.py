"""Parser página a página - Extrai TODOS os condomínios"""
import re, json

with open('_texto_completo.txt', 'r', encoding='utf-8') as f:
    texto = f.read()

# Divide em páginas
paginas = re.split(r'=== PÁGINA \d+ ===', texto)
paginas = [p.strip() for p in paginas if p.strip()]

print(f'Total de páginas: {len(paginas)}')

# Lista de nomes de condomínios (da extração anterior)
nomes_cond = [
    'ACQUARELA', 'AMELIA AUGUSTA', 'ANTONIA LOPES', 'AQUARELLE', 'ARARA VERMELHA',
    'AUREA GUEDES', 'BOCA DOS VENTOS', 'CAMINHO DO MAR', 'CONDOMINIO APPLE FLAT',
    'CONDOMINIO AURINA GALVAO', 'CONDOMINIO BARCAS', 'CORAL GARDEN', 'CRISTAL BEACH',
    'DOM WAGNER', 'FLAMBOYANTS DUPLEXS DUPLEXS', 'FLORAIS DOS TAMARINDOS', 'I HOME VILLA',
    'JANGADAS E CARAVELAS', 'JARDINS MARIA LOPES', 'JOHANN STRAUSS', 'MAR DO ATLANTICO',
    'MARIA BERNADETE', 'MOACYR MAIA', 'MONTE CARLO', 'MONTPELLIER', 'NOVA AMERICA',
    'NOVA AMSTERDA', 'ODONTO MEDICO', 'PALAZZO DI MARIA', 'MARIA', 'PALMA VERDI', 'PIPA PARK',
    'PORTO AZUL', 'PRAIA DO FORTE', 'RECANTO DOS JASMINS', 'RENAISSANCE PREMIERE',
    'RESIDENCIAL LAGOA NOVA', 'RIVIERA MAR DE PONTA NEGRA', 'SOLAR DAS ESTACOES',
    'SPAZIO DI MARIA', 'TERRAZZO', 'TORRE PALAZZO MARIA EMILIA', 'TORRES DAS DUNAS',
    'TORRES DOS POTIGUARAS', 'URUACU IV', 'VERSAILLES', 'VILA MARIA',
    'VILLAGE DAO SILVEIRA', 'VILLAGGIO VENEZIA', 'VILLAGGIO VERITA II',
    'VISTA DO PLANALTO', 'VISTA PARQUE DAS ARVORES', 'WEST SIDE BOULEVARD',
    'LEMON FLAT', 'MANHATAN NATAL'
]

# Processa cada página
resultados = {}
cond_atual = None
unidade = {}
unidades = []

def finalizar():
    global unidade, unidades, cond_atual, resultados
    if unidade.get('apto') and unidade.get('nome'):
        unidades.append(dict(unidade))
    unidade = {}
    if cond_atual and unidades:
        if cond_atual not in resultados:
            resultados[cond_atual] = []
        resultados[cond_atual].extend(unidades)
        unidades = []

for i, pagina in enumerate(paginas):
    linhas = pagina.split('\n')
    
    # Verifica se esta pagina tem cabecalho de condominio
    for linha in linhas:
        raw = linha.strip()
        if 'W045A' in raw:
            finalizar()
            nome_raw = re.sub(r'W045A\s+', '', raw).strip()
            nome_raw = re.sub(r'\s*[-–]\s*PRATIKA\s*\(\d+\)', '', nome_raw).strip()
            nome_raw = re.sub(r'\s*\(?\d*\)?\s*$', '', nome_raw).strip()
            # Remove duplicatas "DUPLEXS DUPLEXS"
            if 'DUPLEXS' in nome_raw:
                nome_raw = 'FLAMBOYANTS DUPLEXS'
            if nome_raw == 'MARIA':
                nome_raw = 'MARIA BERNADETE'
            cond_atual = nome_raw
            break
    
    if not cond_atual:
        continue
    
    # Pula cabecalhos de tabela
    if any(h in pagina[:200] for h in ['Contatos das unidades', 'Unidade', 'Nome/Telefone']):
        continue
    
    # Extrai unidades desta pagina
    for linha in linhas:
        raw = linha.strip()
        if not raw:
            continue
        
        # Linha de apto
        m = re.match(r'^(\d{4})\s', raw)
        if m:
            finalizar()
            unidade['apto'] = m.group(1)
            resto = raw[m.end():].strip()
            if resto and not resto.startswith('+') and len(resto) > 2:
                unidade['nome'] = resto
            continue
        
        # Telefone
        if unidade and not unidade.get('fone') and (raw.startswith('+') or re.match(r'^55\d', raw)):
            unidade['fone'] = raw
            continue
        
        # Email
        if unidade and '@' in raw and not unidade.get('email'):
            unidade['email'] = raw
            continue

finalizar()

# Remove condominios comerciais
comerciais = ['OTICA', 'VANGUARDA', 'LOJA', 'TRANSPORTE', 'ADVOCACIA', 'ARTIGOS OPTICOS',
              '2V TRANSPORTES', 'PAULO HENRIQUE', 'PRATIKA - ADMINISTRADORA', 'PRATIKA COBRANCA',
              'LEMON FLAT', 'VERMELHA MOSSORO', 'PATOS QUIOSQUE', 'LIBERDADE MOSSORO',
              'LOJA CAICO', 'KINGS - VANGUARDA', 'OTICAS CAROL', 'OTICA ULISSES',
              'OTICA UBALDO', 'VANGUARDA NATAL', 'VANGUARDA FORTALEZA']

for ex in comerciais:
    resultados.pop(ex, None)

# Mostra resultado
total = 0
for nome, lista in sorted(resultados.items()):
    validos = [u for u in lista if u.get('nome') and len(u['nome']) > 4]
    if validos:
        total += len(validos)
        wpp = sum(1 for u in validos if u.get('fone'))
        print(f'{nome}: {len(validos)} condominos ({wpp} com tel)')

print(f'\nTOTAL: {total} condominos em {len(resultados)} condominios')
