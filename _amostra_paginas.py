"""Mostra amostra de páginas do PDF para entender formato"""
import re

with open('_texto_completo.txt', 'r', encoding='utf-8') as f:
    texto = f.read()

paginas = re.split(r'=== PÁGINA \d+ ===', texto)
print(f'Total paginas: {len(paginas)}')

# Mostra amostra de paginas especificas
for idx in [1, 50, 100, 150, 200, 250, 300, 350, 400]:
    if idx < len(paginas):
        p = paginas[idx][:400]
        print(f'\n--- Pagina {idx} (inicio) ---')
        print(p[:300])
