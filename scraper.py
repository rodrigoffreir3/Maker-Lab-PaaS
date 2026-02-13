from curl_cffi import requests # A mágica acontece aqui
from bs4 import BeautifulSoup
import logging
import random
import time
import json
import re
from app import create_app
from models import db, Component

# --- CONFIGURAÇÃO DE LOGS ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [SNIPER] - %(levelname)s - %(message)s'
)
logger = logging.getLogger("HardwareSniper.Scraper")

def get_html(url):
    """
    Baixa o HTML usando curl_cffi para emular um navegador Chrome real (TLS Fingerprint).
    Isso passa pelo Cloudflare/WAF da Terabyte e Kabum.
    """
    try:
        # impersonate="chrome110" faz o servidor achar que somos um Chrome legítimo
        response = requests.get(
            url, 
            impersonate="chrome110", 
            timeout=20,
            headers={
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
                'Referer': 'https://www.google.com/'
            }
        )
        
        if response.status_code == 403:
            logger.error(f"⛔ Bloqueio WAF (403) em: {url}")
            return None
            
        return response.text
    except Exception as e:
        logger.error(f"Erro de conexão com {url}: {str(e)}")
        return None

def clean_price(price_str):
    """Limpa string de preço (R$ 1.200,90 -> 1200.90)"""
    if not price_str: return None
    try:
        clean = re.sub(r'[^\d.,]', '', str(price_str))
        if ',' in clean:
            clean = clean.replace('.', '').replace(',', '.')
        return float(clean)
    except Exception:
        return None

def regex_search_price(soup):
    """
    TÉCNICA DE DESESPERO:
    Se os seletores falharem, procura padrões de preço no texto visível.
    Procura por 'R$ X à vista' ou apenas o maior preço que faça sentido.
    """
    text = soup.get_text()
    # Procura padrões como "R$ 1.200,00 à vista" ou "R$ 1200,00"
    matches = re.findall(r'R\$\s?(\d{1,3}(?:\.\d{3})*,\d{2})', text)
    
    precos_encontrados = []
    for m in matches:
        v = clean_price(m)
        if v and v > 50: # Ignora preços de frete ou parcelas pequenas
            precos_encontrados.append(v)
            
    if precos_encontrados:
        # Geralmente o menor preço da página > 50 reais é o preço à vista do produto principal
        # (sites costumam mostrar "De: 2000" e "Por: 1500", queremos o menor)
        return min(precos_encontrados)
    return None

# --- EXTRATORES ---

def extract_kabum(soup):
    try:
        # 1. JSON-LD
        scripts = soup.find_all('script', type='application/ld+json')
        for script in scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, list): data = data[0]
                if 'offers' in data and 'price' in data['offers']:
                    return float(data['offers']['price'])
            except: continue
            
        # 2. Tag Específica
        price_tag = soup.find('h4', class_='finalPrice')
        if price_tag: return clean_price(price_tag.text)
        
        return regex_search_price(soup)
    except: return None

def extract_terabyte(soup):
    try:
        # 1. ID Específico
        price_tag = soup.find(id='valVista')
        if price_tag: return clean_price(price_tag.text)
        
        # 2. Meta Tag
        meta_price = soup.find('meta', property='product:price:amount')
        if meta_price: return float(meta_price['content'])
        
        return regex_search_price(soup)
    except: return None

def extract_pichau(soup):
    try:
        # 1. Texto Bruto "à vista"
        text = soup.get_text()
        match = re.search(r'R\$\s?([\d.,]+)\s?à vista', text)
        if match: return clean_price(match.group(1))
            
        # 2. Meta Tag
        meta_price = soup.find('meta', property='og:price:amount')
        if meta_price: return clean_price(meta_price['content'])

        return regex_search_price(soup)
    except: return None

def extract_shopinfo(soup):
    try:
        price_tag = soup.find('span', class_='price-box__price')
        if price_tag: return clean_price(price_tag.text)
        return regex_search_price(soup)
    except: return None

def extract_generic(soup):
    try:
        meta_price = soup.find('meta', property='og:price:amount')
        if meta_price: return clean_price(meta_price['content'])
        return regex_search_price(soup)
    except: return None

# --- LOOP PRINCIPAL ---

def update_prices():
    app = create_app()
    with app.app_context():
        components = Component.query.filter(Component.affiliate_link != None).all()
        logger.info(f"Iniciando monitoramento de {len(components)} peças...")
        
        for comp in components:
            url = comp.affiliate_link
            if not url or 'http' not in url: continue
                
            logger.info(f"🔎 Visitando: {comp.name}...")
            
            html = get_html(url)
            if not html: continue # Se deu 403, pula
            
            soup = BeautifulSoup(html, 'html.parser')
            new_price = None
            
            if 'kabum.com' in url: new_price = extract_kabum(soup)
            elif 'terabyteshop.com' in url: new_price = extract_terabyte(soup)
            elif 'pichau.com' in url: new_price = extract_pichau(soup)
            elif 'shopinfo.com' in url: new_price = extract_shopinfo(soup)
            else: new_price = extract_generic(soup)
            
            if new_price and new_price > 0:
                if new_price != comp.price:
                    variation = abs(new_price - comp.price) / comp.price if comp.price > 0 else 0
                    if variation > 0.6 and comp.price > 10: # Proteção contra bug de leitura
                         logger.warning(f"⚠️ Variação suspeita ({variation*100:.0f}%) para {comp.name}. Ignorando.")
                    else:
                        logger.info(f"✅ ATUALIZADO: {comp.name} | R$ {comp.price} -> R$ {new_price}")
                        comp.old_price = comp.price
                        comp.price = new_price
                else:
                    logger.info(f"💤 Sem alteração: R$ {new_price}")
            else:
                logger.warning(f"❌ Não foi possível ler preço de {comp.name} (Tentativa Regex falhou)")
            
            time.sleep(random.uniform(2, 5))
            
        db.session.commit()
        logger.info("🏁 Fim da rodada.")

if __name__ == "__main__":
    update_prices()