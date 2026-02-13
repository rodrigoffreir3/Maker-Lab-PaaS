from brain.inference import predict_persona
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

def sniper_audit(component):
    """
    Usa a ML (Patricinha) para classificar o componente antes ou depois da coleta.
    Isso ajuda a entender para qual nicho o Sniper está atirando.
    """
    try:
        # Se for CPU ou GPU, usamos o score real. Para RAM/SSD usamos valores base.
        c_score = component.performance_score if component.type == 'cpu' else 10000
        g_score = component.performance_score if component.type == 'gpu' else 1000
        # Simplificação: assumimos 16GB e NVMe (1) para auditoria individual
        
        persona = predict_persona(c_score, g_score, 16, 1)
        return persona
    except Exception as e:
        logger.error(f"Erro na auditoria da IA: {e}")
        return "Desconhecido"

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
    
    # Auditoria da IA antes de pesquisar
    persona_alvo = sniper_audit(component)
    
    url = f"https://www.google.com/search?q={clean_name}&tbm=shop&tbs=p_ord:p&hl=pt-BR"
    logger.info(f"🔎 Buscando: {clean_name} | Foco IA: {persona_alvo}")
    
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
        for card in product_cards[:6]: # Top 6 para performance
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
                    logger.info(f"🎯 [Sniper AI] R$ {old} -> R$ {best_price} (OK!)")
                else:
                    logger.info(f"🎯 [Sniper AI] Preço estável: R$ {best_price}")
                return True
        return False

    except Exception:
        return False

def process_batch(products_batch):
    """Processa um lote pequeno de produtos e fecha o navegador"""
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False, # Mantenha False para monitorar o comportamento humano da IA
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(viewport={'width': 1280, 'height': 800})
        
        # Bloqueia Imagens e Fontes (Economia de RAM drástica)
        context.route("**/*", lambda route: route.abort() 
            if route.request.resource_type in ["image", "media", "font", "stylesheet"] 
            else route.continue_())
        
        context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        page = context.new_page()

        for product in products_batch:
            result = search_lowest_price(product, page)
            if result == "CAPTCHA":
                browser.close()
                return False 
            
            # Navegação "humana": tempos aleatórios entre pesquisas
            time.sleep(random.uniform(3, 7))
        
        browser.close()
        return True

def run_bot():
    app = create_app()
    with app.app_context():
        print("\n" + "="*50)
        print("♻️  HARDWARE SNIPER BOT V8 + AI BRAIN ACTIVATED")
        print("="*50 + "\n")
        
        while True:
            all_products = Component.query.all()
            if not all_products: 
                print("❌ Nenhum produto encontrado no banco para monitorar.")
                break
            
            random.shuffle(all_products)
            
            # Lotes de 15 para manter a RAM do seu PC de R$ 1.500 sempre saudável
            batch_size = 15
            batches = [all_products[i:i + batch_size] for i in range(0, len(all_products), batch_size)]
            
            total_batches = len(batches)
            
            for i, batch in enumerate(batches):
                print(f"\n🚀 LOTE {i+1}/{total_batches}")
                
                success = process_batch(batch)
                
                if not success:
                    print("🛡️ Bloqueio detectado. Resfriando motores (120s)...")
                    time.sleep(120)
                
                # O segredo da longevidade do bot:
                gc.collect()
                print("🧹 Memória Reciclada pela Inteligência Sniper.")
                
            print("\n💤 Ciclo Finalizado. Próxima varredura em 5 minutos...")
            time.sleep(300)

if __name__ == "__main__":
    run_bot()