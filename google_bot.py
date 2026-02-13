import time
import random
import re
import os
import gc # Garbage Collector do Python
from playwright.sync_api import sync_playwright
from app import create_app
from models import db, Component
import logging

# --- LOGS ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - BOT V8 - %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger("GoogleShoppingBot")

if not os.path.exists('prints_debug'):
    os.makedirs('prints_debug')

def clean_price(text):
    if not text: return None
    try:
        text = text.replace('\xa0', ' ').strip()
        blacklist = [r'/mês', r'x\s\d+', r'\d+x', r'juros', r'entrada', r'cada', r'\(']
        for term in blacklist:
            if re.search(term, text, re.IGNORECASE): return None
            
        match = re.search(r'R\$\s*([\d.,]+)', text)
        if match:
            num_str = match.group(1)
            if num_str.count('.') > 1:
                num_str = num_str.replace('.', '', num_str.count('.') - 1)
            return float(num_str.replace('.', '').replace(',', '.'))
        return None
    except: return None

def search_lowest_price(component, page):
    clean_name = re.sub(r'\[.*?\]', '', component.name).strip()
    
    url = f"https://www.google.com/search?q={clean_name}&tbm=shop&tbs=p_ord:p&hl=pt-BR"
    logger.info(f"🔎 {clean_name}...")
    
    try:
        page.goto(url, timeout=20000, wait_until='domcontentloaded')
        
        if "recaptcha" in page.url:
            logger.warning("🛡️ CAPTCHA! Pausando lote...")
            return "CAPTCHA"

        # Scan rápido
        try:
            product_cards = page.locator(".sh-dgr__content").all()
            if not product_cards:
                product_cards = page.locator("div").filter(has_text=re.compile(r"R\$")).all()
        except: return False

        candidates = []
        for card in product_cards[:6]: # Reduzi para top 6 para economizar memória
            try:
                if not card.is_visible(): continue
                text_content = card.inner_text()
                lines = text_content.split('\n')
                for line in lines:
                    price = clean_price(line)
                    if price and price > 50: candidates.append(price)
            except: pass

        if candidates:
            candidates = sorted(list(set(candidates)))
            target = component.price if component.price > 10 else 500
            best_price = None
            min_diff = float('inf')
            
            for p in candidates:
                if p < (target * 0.35): continue 
                if p > (target * 2.5): continue
                diff = abs(p - target)
                if diff < min_diff:
                    min_diff = diff
                    best_price = p
            
            if not best_price and candidates:
                 valid_c = [x for x in candidates if x > (target * 0.35)]
                 if valid_c: best_price = min(valid_c)

            if best_price:
                old = component.price
                component.price = best_price
                db.session.commit() # Salva no banco
                
                if old != best_price:
                    logger.info(f"⚡ R$ {old} -> R$ {best_price}")
                else:
                    logger.info(f"⚡ Mantido: R$ {best_price}")
                return True
        return False

    except Exception:
        return False

def process_batch(products_batch):
    """Processa um lote pequeno de produtos e fecha o navegador"""
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False, # Pode deixar True se quiser, mas False vê o erro
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(viewport={'width': 1280, 'height': 800})
        
        # Bloqueia Imagens e Fontes (Economia de RAM)
        context.route("**/*", lambda route: route.abort() 
            if route.request.resource_type in ["image", "media", "font", "stylesheet"] 
            else route.continue_())
        
        context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        page = context.new_page()

        for product in products_batch:
            result = search_lowest_price(product, page)
            if result == "CAPTCHA":
                browser.close()
                return False # Sinaliza para parar
            
            time.sleep(random.uniform(2, 4))
        
        browser.close()
        return True

def run_bot():
    app = create_app()
    with app.app_context():
        print("♻️ BOT V8 (RECICLAGEM DE RAM) INICIADO")
        
        while True:
            all_products = Component.query.all()
            if not all_products: break
            random.shuffle(all_products)
            
            # Divide em lotes de 15 produtos
            batch_size = 15
            batches = [all_products[i:i + batch_size] for i in range(0, len(all_products), batch_size)]
            
            total_batches = len(batches)
            
            for i, batch in enumerate(batches):
                print(f"\n--- INICIANDO LOTE {i+1}/{total_batches} (RAM LIMPA) ---")
                
                success = process_batch(batch)
                
                if not success:
                    print("⚠️ CAPTCHA detectado ou erro crítico. Pausando 2 minutos...")
                    time.sleep(120)
                
                # Força a limpeza da memória do Python
                gc.collect()
                print("🧹 Memória Reciclada.")
                
            print("💤 Ciclo completo. Dormindo 5 minutos antes de recomeçar...")
            time.sleep(300)

if __name__ == "__main__":
    run_bot()