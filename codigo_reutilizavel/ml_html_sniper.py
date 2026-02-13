from curl_cffi import requests
from bs4 import BeautifulSoup
import logging
import re
import time
import random
from app import create_app
from models import db, Component
from score_db import estimar_score

# --- LOGS ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - ML HTML - %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger("MLSniper")

# --- HEADERS 2026 ---
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
    'Referer': 'https://www.mercadolivre.com.br/',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'same-origin',
    'Upgrade-Insecure-Requests': '1',
}

# --- ALVOS ---
PRODUTOS_ALVO = {
    'gpu': ['placa de video rx 580 8gb', 'placa video rtx 3060', 'placa video rx 6600', 'placa video rtx 4060', 'placa video gtx 1650'],
    'cpu': ['processador ryzen 5 5600g', 'processador ryzen 5 4600g', 'processador ryzen 5 5600', 'processador i5 12400f'],
    'ram': ['memoria ram ddr4 8gb 3200mhz', 'memoria ram ddr4 16gb'],
    'ssd': ['ssd nvme 1tb', 'ssd nvme 500gb', 'ssd 480gb sata']
}

def safe_extract(tag, attr=None):
    """
    Função BLINDADA para extrair texto ou atributo.
    Resolve o erro 'AttributeValueList' convertendo tudo para string.
    """
    if not tag: return ""
    
    val = ""
    if attr:
        val = tag.get(attr)
    else:
        val = tag.get_text(strip=True)
        
    # Se o BeautifulSoup retornar uma lista (o erro que você teve), pega o primeiro
    if isinstance(val, list):
        val = val[0]
        
    # Garante que é string
    return str(val).strip()

def clean_price(tag):
    if not tag: return 0.0
    try:
        price_text = safe_extract(tag) # Usa a extração segura
        clean = re.sub(r'[^\d,]', '', price_text)
        clean = clean.replace('.', '').replace(',', '.')
        return float(clean)
    except: return 0.0

def search_ml_html(termo, tipo_peca):
    termo_slug = termo.replace(' ', '-')
    url = f"https://lista.mercadolivre.com.br/{termo_slug}_NoIndex_True"
    
    logger.info(f"🔎 HTML Buscando: '{termo}'...")
    
    try:
        r = requests.get(url, impersonate="chrome120", headers=HEADERS, timeout=20)
        
        if "captcha" in r.url or "sec-challenge" in r.text:
            logger.warning("🛡️ Captcha do ML detectado. Tentando próxima...")
            return

        soup = BeautifulSoup(r.text, 'html.parser')
        
        items = soup.find_all('li', class_='ui-search-layout__item')
        if not items:
            items = soup.find_all('div', class_='ui-search-result__wrapper')

        count = 0
        app = create_app()
        
        with app.app_context():
            for item in items:
                try:
                    # 1. Link e Título (Extração Segura)
                    link_tag = item.find('a', class_='ui-search-link')
                    if not link_tag: continue
                    
                    # AQUI OCORRIA O ERRO: Agora usamos safe_extract
                    link = safe_extract(link_tag, 'href')
                    nome = safe_extract(link_tag, 'title')
                    
                    if not nome: 
                        nome = safe_extract(link_tag) # Fallback para texto do link

                    # 2. Preço
                    price_container = item.find('div', class_='ui-search-price__second-line')
                    if not price_container:
                        price_container = item.find('span', class_='andes-money-amount__fraction')
                    else:
                        price_container = price_container.find('span', class_='andes-money-amount__fraction')
                        
                    preco = clean_price(price_container)
                    if preco < 50: continue

                    # 3. Vendedor
                    seller_tag = item.find('p', class_='ui-search-official-store-label')
                    seller = safe_extract(seller_tag) if seller_tag else "Mercado Livre"

                    # 4. Imagem
                    img_tag = item.find('img')
                    thumb = safe_extract(img_tag, 'src')
                    # ML usa lazy load (data-src), tenta pegar se existir
                    if img_tag and img_tag.get('data-src'):
                        thumb = safe_extract(img_tag, 'data-src')

                    # --- VALIDAÇÃO ---
                    if Component.query.filter_by(affiliate_link=link).first(): continue
                    
                    nome = nome.replace("Frete grátis", "").strip()

                    score = estimar_score(nome, tipo_peca)
                    is_int = False
                    if tipo_peca == 'cpu':
                        termos = nome.lower().split()
                        if any(t.endswith('g') and t[0].isdigit() for t in termos): is_int = True

                    novo = Component(
                        name=f"[{seller}] {nome[:80]}",
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

                except Exception as e:
                    # logger.error(f"Erro item: {e}") # Descomente para debug detalhado
                    continue
            
            db.session.commit()
            logger.info(f"🏁 '{termo}': {count} itens salvos.")
            
    except Exception as e:
        logger.error(f"Erro fatal: {e}")

if __name__ == "__main__":
    print("\n" + "="*40)
    print("📦 ML HTML SNIPER (BLINDADO)")
    print("="*40)
    
    op = input("Digite 'GO' para tentar via HTML: ").strip().upper()
    
    if op == 'GO':
        for tipo, lista in PRODUTOS_ALVO.items():
            for termo in lista:
                search_ml_html(termo, tipo)
                time.sleep(random.uniform(2, 4))
        
        print("\n✅ FIM DO PROCESSO.")