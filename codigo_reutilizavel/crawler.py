from curl_cffi import requests
from bs4 import BeautifulSoup
import logging
import re
import time
import json
import random
from app import create_app
from models import db, Component
from score_db import estimar_score

# --- CONFIGURAÇÃO DE LOGS ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("HardwareSniper.Crawler")

# --- MAPA DE URLS ---
URLS_CATEGORIAS = {
    'terabyte': {
        'gpu': 'https://www.terabyteshop.com.br/hardware/placas-de-video',
        'cpu': 'https://www.terabyteshop.com.br/hardware/processadores',
        'ram': 'https://www.terabyteshop.com.br/hardware/memorias',
        'ssd': 'https://www.terabyteshop.com.br/hardware/hard-disk/ssd',
    },
    'pichau': {
        'gpu': 'https://www.pichau.com.br/hardware/placa-de-video',
        'cpu': 'https://www.pichau.com.br/hardware/processadores',
        'ram': 'https://www.pichau.com.br/hardware/memorias',
        'ssd': 'https://www.pichau.com.br/hardware/ssd',
    },
    'shopinfo': {
        'gpu': 'https://www.shopinfo.com.br/hardware/placa-de-video',
        'cpu': 'https://www.shopinfo.com.br/hardware/processador',
        'ram': 'https://www.shopinfo.com.br/hardware/memoria',
        'ssd': 'https://www.shopinfo.com.br/hardware/ssd',
    }
}

# --- HEADERS 2026 (CHROME 144) ---
HEADERS_2026 = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
    'Referer': 'https://www.google.com/',
    'Sec-Ch-Ua': '"Not(A:Brand";v="24", "Chromium";v="144", "Google Chrome";v="144"',
    'Sec-Ch-Ua-Mobile': '?0',
    'Sec-Ch-Ua-Platform': '"Windows"',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'cross-site',
    'Sec-Fetch-User': '?1',
    'Dnt': '1'
}

# --- FUNÇÕES SEGURAS (CORREÇÃO DE BUGS) ---

def safe_text(tag):
    """Retorna o texto de uma tag com segurança, retornando vazio se a tag for None."""
    if tag:
        return tag.get_text(strip=True)
    return ""

def clean_price(price_str):
    if not price_str: return 0.0
    if isinstance(price_str, (int, float)): return float(price_str)
    try:
        clean = re.sub(r'[^\d,]', '', str(price_str))
        clean = clean.replace(',', '.')
        return float(clean)
    except: return 0.0

def get_soup(url):
    try:
        logger.info(f"🌐 Acessando: {url}")
        # Impersonate chrome124 (estável) + Headers do 144
        r = requests.get(url, impersonate="chrome124", headers=HEADERS_2026, timeout=30)
        
        if r.status_code in [200, 201, 403]:
            # Detecta Captcha do Cloudflare
            if "Just a moment" in r.text or "challenge-platform" in r.text:
                logger.warning(f"🛡️ Bloqueio Cloudflare (Captcha) em: {url}")
                return None
            return BeautifulSoup(r.text, 'html.parser')
            
        logger.error(f"❌ Erro HTTP {r.status_code}")
        return None
    except Exception as e:
        logger.error(f"❌ Erro de conexão: {e}")
        return None

def extract_json_ld(soup):
    """Extrai dados estruturados ocultos (JSON-LD)"""
    products = []
    scripts = soup.find_all('script', type='application/ld+json')
    
    for script in scripts:
        try:
            if not script.string: continue
            data = json.loads(script.string)
            
            # Formato ItemList (Categorias)
            if isinstance(data, dict) and data.get('@type') == 'ItemList':
                items = data.get('itemListElement', [])
                for item in items:
                    prod = item.get('item', {}) if 'item' in item else item
                    p_data = {
                        'name': prod.get('name'),
                        'url': prod.get('url'),
                        'price': 0
                    }
                    if 'offers' in prod:
                        offer = prod['offers']
                        if isinstance(offer, list): offer = offer[0]
                        p_data['price'] = offer.get('price') or offer.get('lowPrice')
                    products.append(p_data)

            # Formato Graph (Wordpress/Shopinfo)
            elif isinstance(data, dict) and '@graph' in data:
                for node in data['@graph']:
                    if node.get('@type') == 'Product':
                        p_data = {
                            'name': node.get('name'),
                            'url': node.get('url'),
                            'price': 0
                        }
                        if 'offers' in node:
                            offer = node['offers']
                            if isinstance(offer, list): offer = offer[0]
                            p_data['price'] = offer.get('price')
                        products.append(p_data)
        except: continue
        
    return products

def salvar_produto(nome, link, preco, tipo_peca, loja_nome):
    if not nome or not link or not preco: return
    preco = clean_price(preco)
    if preco < 50: return 
    
    # Filtros de Lixo
    nome_lower = nome.lower()
    if any(x in nome_lower for x in ["computador", "pc gamer", "upgrade", "kit", "t-gamer"]): return 
    
    # Arruma links relativos
    if not link.startswith('http'):
        if loja_nome == 'terabyte': link = "https://www.terabyteshop.com.br" + link
        elif loja_nome == 'pichau': link = "https://www.pichau.com.br" + link
        elif loja_nome == 'shopinfo': link = "https://www.shopinfo.com.br" + link

    app = create_app()
    with app.app_context():
        if Component.query.filter_by(affiliate_link=link).first(): return

        score = estimar_score(nome, tipo_peca)
        is_integrated = False
        if tipo_peca == 'cpu':
            termos = nome_lower.split()
            if any(x.endswith('g') and len(x) > 2 and x[0].isdigit() for x in termos): is_integrated = True
            if 'gt' in termos: is_integrated = True

        novo = Component(
            name=f"[{loja_nome.capitalize()}] {nome[:100]}",
            type=tipo_peca,
            price=preco,
            performance_score=score,
            generation=0,
            is_integrated_graphics=is_integrated,
            affiliate_link=link
        )
        db.session.add(novo)
        db.session.commit()
        logger.info(f"✅ [{loja_nome}] {nome[:30]}... | R$ {preco} | Score: {score}")

def crawl_universal(loja, tipo):
    url = URLS_CATEGORIAS[loja].get(tipo)
    if not url: return
    
    soup = get_soup(url)
    if not soup: return
    
    count = 0
    
    # 1. Tenta JSON-LD (Prioridade máxima)
    json_products = extract_json_ld(soup)
    if json_products:
        logger.info(f"🔍 {loja.upper()}: {len(json_products)} itens via JSON")
        for p in json_products:
            salvar_produto(p.get('name'), p.get('url'), p.get('price'), tipo, loja)
            count += 1
            
    # 2. Fallback Visual (Se JSON falhar)
    if count == 0:
        logger.info(f"⚠️ {loja.upper()}: Tentando modo visual...")
        
        if loja == 'terabyte':
            for p in soup.find_all('div', class_='pbox'):
                try:
                    nm = p.find('a', class_='prod-name')
                    pr_div = p.find('div', class_='prod-new-price')
                    
                    if nm and pr_div:
                        # Extração segura do preço
                        span_preco = pr_div.find('span')
                        if span_preco:
                            preco_texto = span_preco.get_text(strip=True)
                        else:
                            preco_texto = pr_div.get_text(strip=True)
                            
                        salvar_produto(safe_text(nm), nm['href'], preco_texto, tipo, loja)
                        count += 1
                except Exception: continue

        elif loja == 'pichau':
            # Busca cards MUI ou links soltos
            cards = soup.find_all('div', class_=re.compile('MuiCard'))
            if not cards: cards = soup.find_all('a', href=True)
            
            for c in cards:
                try:
                    link_tag = c if c.name == 'a' else c.find('a', href=True)
                    if not link_tag: continue
                    
                    link = link_tag['href']
                    # Filtro básico de URL para não pegar links de rodapé
                    if '/hardware/' not in link and '/placa-de-video' not in link: continue
                    
                    nome = safe_text(link_tag)
                    if not nome: nome = safe_text(c)
                    
                    # Preço no contexto
                    txt = safe_text(c)
                    if c.parent: txt += safe_text(c.parent)
                    match = re.search(r'R\$\s?([\d.,]+)', txt)
                    
                    if match:
                        salvar_produto(nome, link, match.group(1), tipo, loja)
                        count += 1
                except: continue

        elif loja == 'shopinfo':
            for p in soup.find_all(class_=re.compile(r'product-item|li-product')):
                try:
                    lnk = p.find('a', href=True)
                    pr = p.find(class_=re.compile(r'price'))
                    if lnk and pr:
                        nome = lnk.get('title') or safe_text(lnk)
                        salvar_produto(nome, lnk['href'], safe_text(pr), tipo, loja)
                        count += 1
                except: continue

    logger.info(f"🏁 {loja.upper()} {tipo.upper()}: {count} itens cadastrados.")

# --- FERRAMENTA DE DEBUG ---
def debug_mode():
    print("\n--- DEBUG MODE (Chrome 144) ---")
    url = input("Cole a URL para testar: ").strip()
    if not url: return
    
    try:
        r = requests.get(url, impersonate="chrome124", headers=HEADERS_2026, timeout=20)
        print(f"\nStatus Code: {r.status_code}")
        print(f"Headers Recebidos: {r.headers}")
        print(f"Tamanho HTML: {len(r.text)} bytes")
        
        filename = "debug_last_request.html"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(r.text)
        print(f"HTML salvo em '{filename}' para análise.")
        
        if "Just a moment" in r.text:
            print("⚠️ ALERTA: Página de Bloqueio Cloudflare detectada.")
    except Exception as e:
        print(f"Erro fatal no debug: {e}")

# --- MENU PRINCIPAL ---
if __name__ == "__main__":
    print("\n" + "="*40)
    print("🕷️  HARDWARE SNIPER - OMNI CRAWLER (2026)")
    print("="*40)
    print("5. RODAR TUDO (Modo Deus)")
    print("9. MODO DEBUG (Testar URL)")
    
    op = input("\nEscolha: ").strip()
    
    if op == '9':
        debug_mode()
    elif op == '5':
        for tipo in ['gpu', 'cpu', 'ram', 'ssd']:
            logger.info(f"\n--- {tipo.upper()} ---")
            crawl_universal('terabyte', tipo)
            time.sleep(2)
            crawl_universal('pichau', tipo)
            time.sleep(2)
            crawl_universal('shopinfo', tipo)