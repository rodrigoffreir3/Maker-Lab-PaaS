# score_db.py
import re

# Dicionário de Scores Base (PassMark G3D Mark / CPU Mark)
# Focamos em peças populares no mercado brasileiro (Novas e Usadas)
SCORES_HARDWARE = {
    # --- PLACAS DE VÍDEO (GPU) ---
    "rtx 4090": 39000, "rtx 4080": 35000, "rtx 4070": 27000, "rtx 4060": 19500,
    "rtx 3090": 26000, "rtx 3080": 24000, "rtx 3070": 22000, "rtx 3060": 17000, 
    "rtx 3050": 12800, "rtx 2060": 14000, "gtx 1660": 11500, "gtx 1650": 7800,
    "gtx 1060": 10000, "gtx 1050": 6000, "gt 1030": 2600, 
    
    "rx 7900": 31000, "rx 7800": 28000, "rx 7700": 24000, "rx 7600": 16500,
    "rx 6900": 25000, "rx 6800": 23000, "rx 6750": 18500, "rx 6700": 18000,
    "rx 6650": 16000, "rx 6600": 15000, "rx 6500": 9500, "rx 6400": 7300,
    "rx 5700": 14500, "rx 5600": 13500, "rx 5500": 8900,
    "rx 590": 9200, "rx 580": 8700, "rx 570": 7000, "rx 560": 3600, "rx 550": 2800,
    
    # As Guerreiras (Low End)
    "gt 740": 1600, "gt 730": 900, "gt 710": 650, 
    "gt 630": 750, "gt 610": 350, "gt 210": 180,
    "hd 5450": 230, "hd 6450": 280, "r5 230": 260,

    # --- PROCESSADORES (CPU) ---
    # AMD Ryzen
    "ryzen 9 7950x": 63000, "ryzen 9 5950x": 46000,
    "ryzen 7 7800x3d": 55000, "ryzen 7 5800x3d": 28000, "ryzen 7 5700x": 26800, "ryzen 7 5700g": 24500,
    "ryzen 5 7600": 29000, "ryzen 5 5600x": 22000, "ryzen 5 5600": 21500, 
    "ryzen 5 5600g": 19800, "ryzen 5 5600gt": 20000, "ryzen 5 5500": 19500,
    "ryzen 5 4600g": 16200, "ryzen 5 4500": 15800, "ryzen 5 3600": 17800, "ryzen 5 3400g": 9400,
    "ryzen 3 4100": 11500, "ryzen 3 3200g": 7200, "ryzen 3 2200g": 6800,
    "athlon 3000g": 4500, "athlon 320ge": 4600, "athlon 200ge": 4200,

    # Intel Core
    "i9-14900k": 62000, "i7-14700k": 54000, "i5-14600k": 39000,
    "i9-13900k": 60000, "i7-13700": 34000, "i5-13400": 26000,
    "i7-12700": 31500, "i5-12400": 19500, "i3-12100": 14500,
    "i5-11400": 17000, "i5-10400": 12500, "i3-10100": 9000,
    "i7-7700": 8700, "i5-7400": 5500, 
    "i7-4790": 7200, "i5-4590": 5300, "i5-3470": 4600, "i3-3220": 3200, # Clássicos de escritório
}

def estimar_score(nome_produto, tipo_peca):
    """
    Tenta adivinhar o score baseado no nome.
    Se for RAM ou SSD, usa heurística. Se for CPU/GPU, usa o dicionário.
    """
    nome_norm = nome_produto.lower()
    
    # 1. Heurística para RAM (Baseada na frequência)
    if tipo_peca == 'ram':
        # Procura por "3200MHz", "3200", "2666", etc.
        match = re.search(r'(\d{4})\s?mhz', nome_norm)
        if match:
            return int(match.group(1))
        # Se não achar MHz explícito, procura números comuns
        if '3200' in nome_norm: return 3200
        if '3000' in nome_norm: return 3000
        if '2666' in nome_norm: return 2666
        if '2400' in nome_norm: return 2400
        if 'ddr4' in nome_norm: return 2400 # Padrão DDR4
        if 'ddr3' in nome_norm: return 1600 # Padrão DDR3
        return 2133 # Fallback

    # 2. Heurística para SSD (Baseada na tecnologia)
    if tipo_peca == 'ssd':
        if 'nvme' in nome_norm or 'm.2' in nome_norm:
            # NVMe genérico ganha score alto pela velocidade
            return 3500 
        return 550 # SATA III padrão
        
    # 3. Busca no Dicionário (CPU e GPU)
    melhor_match = 0
    maior_len = 0
    
    for chave, score in SCORES_HARDWARE.items():
        if chave in nome_norm:
            # Prioriza a chave mais longa (ex: "rtx 3060 ti" > "rtx 3060")
            if len(chave) > maior_len:
                maior_len = len(chave)
                melhor_match = score
                
    return melhor_match