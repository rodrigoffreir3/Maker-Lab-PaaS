from curl_cffi import requests
import logging
import time
import random
from app import create_app
from models import db, Component
from score_db import estimar_score

# --- LOGS ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - ML API - %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger("MLSniper")

# --- LISTA DE ALVOS (ESSENCIAIS) ---
PRODUTOS_ALVO = {
    'gpu': [
        'rx 580 8gb', 'rx 6600', 'rtx 3060 12gb', 'rtx 4060', 'gtx 1650', 
        'rx 550', 'rtx 4070', 'rx 7600', 'gt 1030'
    ],
    'cpu': [
        'ryzen 5 5600g', 'ryzen 5 4600g', 'ryzen 7 5700g', 'ryzen 5 5600', 
        'i5 12400f', 'i3 12100f', 'i5 10400f', 'ryzen 7 5800x3d'
    ],
    'ram': [
        'memoria ram ddr4 8gb 3200mhz', 'memoria ram ddr4 16gb', 
        'memoria ram ddr3 8gb'
    ],
    'ssd': [
        'ssd nvme 500gb', 'ssd nvme 1tb', 'ssd sata 480gb', 'ssd sata 960gb'
    ]
}

def search_mercadolivre(termo, tipo_peca):
    """
    Usa a API do ML via curl_cffi para evitar erro 403.
    """
    logger.info(f"🔎 API Buscando: '{termo}'...")
    
    # URL da API Pública
    url = f"https://api.mercadolibre.com/sites/MLB/search?q={termo}&limit=15&condition=new"
    
    try:
        # O SEGRED0: Impersonate Chrome para não ser barrado como script python
        response = requests.get(
            url, 
            impersonate="chrome120", 
            timeout=20
        )
        
        if response.status_code != 200:
            logger.error(f"Erro API: {response.status_code} (Bloqueio ou Erro)")
            return

        data = response.json()
        results = data.get('results', [])
        
        if not results:
            logger.warning("Nenhum resultado retornado.")
            return

        count = 0
        app = create_app()
        
        with app.app_context():
            for item in results:
                try:
                    # Extração Segura
                    ml_id = item.get('id')
                    nome = item.get('title')
                    if not nome: continue
                    
                    preco = float(item.get('price'))
                    link = item.get('permalink')
                    thumb = item.get('thumbnail')
                    
                    # Filtro de preço (Ignorar parafusos e cabos)
                    if preco < 50: continue
                    
                    # Filtro de Lixo no Nome
                    nome_lower = nome.lower()
                    if "caixa vazia" in nome_lower or " defeito" in nome_lower: continue

                    # Define Vendedor (Loja Oficial ou Vendedor Platinum)
                    seller_name = "Mercado Livre"
                    if item.get('official_store_id'):
                        seller_name = "Loja Oficial ML"
                    elif item.get('seller', {}).get('seller_reputation', {}).get('power_seller_status') == 'platinum':
                        seller_name = "ML Platinum"
                    
                    # Verifica duplicidade
                    if Component.query.filter_by(affiliate_link=link).first(): continue
                    
                    # Score Inteligente
                    score = estimar_score(nome, tipo_peca)
                    
                    # GPU Integrada?
                    is_int = False
                    if tipo_peca == 'cpu':
                        termos = nome_lower.split()
                        if any(t.endswith('g') and t[0].isdigit() for t in termos): is_int = True

                    novo = Component(
                        name=f"[{seller_name}] {nome[:90]}",
                        type=tipo_peca,
                        price=preco,
                        performance_score=score,
                        generation=0,
                        is_integrated_graphics=is_int,
                        affiliate_link=link,
                        image_url=thumb
                    )
                    db.session.add(novo)
                    count += 1
                    logger.info(f"✅ {nome[:30]}... | R$ {preco}")
                    
                except Exception: continue

            db.session.commit()
            logger.info(f"🏁 Adicionados: {count} itens.")

    except Exception as e:
        logger.error(f"Erro fatal: {e}")

if __name__ == "__main__":
    print("\n" + "="*40)
    print("📦 ML API SNIPER v2 (ANTI-BOT)")
    print("="*40)
    
    op = input("Digite 'GO' para iniciar a carga: ").strip().upper()
    
    if op == 'GO':
        for tipo, lista in PRODUTOS_ALVO.items():
            print(f"\n--- {tipo.upper()} ---")
            for termo in lista:
                search_mercadolivre(termo, tipo)
                # Pausa aleatória para não tomar Rate Limit da API
                time.sleep(random.uniform(1.5, 3))
        
        print("\n✅ BANCO CARREGADO COM SUCESSO! (Espero...)")