from brain.inference import predict_persona
import time
import random
import re
import os
import gc
from playwright.sync_api import sync_playwright
from app import create_app
from models import db, Component
import logging

# --- LOGS ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - BOT V10 - %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger("GoogleShoppingBot")

def sniper_audit(component):
    """Usa a ML para classificar o componente antes da pesquisa."""
    try:
        c_score = component.performance_score if component.type == 'cpu' else 10000
        g_score = component.performance_score if component.type == 'gpu' else 1000
        persona = predict_persona(c_score, g_score, 16, 1)
        
        # --- CORREÇÃO DO SELO DA IA ---
        # Garante que a IA devolva exatamente as strings esperadas pelo HTML
        if "gamer" in persona.lower(): return "Gamer"
        if "office" in persona.lower() or "multitask" in persona.lower(): return "Office/Multitask"
        if "workstation" in persona.lower() or "editor" in persona.lower(): return "Workstation/Editor"
        return "Gamer" # Fallback seguro
    except:
        return "Desconhecido"

def clean_price(text):
    """Limpa e converte o texto do preço para float."""
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
    except:
        return None

def search_lowest_price(component, page):
    """Busca o menor preço com seletores agressivos para o Google Shopping atual."""
    clean_name = re.sub(r'\[.*?\]', '', component.name).strip()
    persona_alvo = sniper_audit(component)
    
    url = f"https://www.google.com/search?q={clean_name}&tbm=shop&tbs=p_ord:p&hl=pt-BR"
    logger.info(f"🔎 Buscando: {clean_name} | Foco IA: {persona_alvo}")
    
    try:
        page.goto(url, timeout=25000, wait_until='domcontentloaded')
        page.wait_for_timeout(2000) # Pausa tática para o JS do Google renderizar os preços

        if "recaptcha" in page.url:
            logger.warning("🛡️ CAPTCHA Detectado!")
            return "CAPTCHA"

        # --- A CURA DA CEGUEIRA: Seletores Múltiplos e Agressivos ---
        cards = page.locator(".sh-dgr__grid-result, .sh-dlr__list-result, .sh-dgr__content, div[data-docid]").all()
        
        if not cards:
            # Fallback extremo se o Google mudar toda a interface
            cards = page.locator("div").filter(has_text=re.compile(r"R\$")).all()

        best_price = float('inf')
        best_link = None
        target_ref = component.price if component.price > 10 else 500

        for card in cards[:8]: # Analisa os 8 primeiros
            try:
                if not card.is_visible(): continue
                
                card_text = card.inner_text()
                price = clean_price(card_text)
                
                # Busca a primeira tag de link dentro deste card
                link_el = card.locator("a[href*='shopping/product'], a[href*='aclk']").first()
                if not link_el.count():
                    link_el = card.locator("a").first()
                
                if link_el.count() > 0:
                    href = link_el.get_attribute("href")
                    
                    if href and price and price > 50:
                        # --- FILTRO ALARGADO --- 
                        # Aceita desde super promoções (-75%) até mercado inflacionado (+400%) em relação ao Seed
                        if (target_ref * 0.25) < price < (target_ref * 4.0):
                            if price < best_price:
                                best_price = price
                                best_link = f"https://www.google.com{href}" if href.startswith('/') else href
            except Exception:
                continue

        if best_price != float('inf') and best_link:
            # --- LÓGICA DE HISTÓRICO E PERSISTÊNCIA ---
            if component.min_price_historic is None or best_price < component.min_price_historic:
                component.min_price_historic = best_price
            
            # Cálculo de Média Móvel
            count = component.price_update_count or 0
            avg = component.avg_price_historic or best_price
            component.avg_price_historic = ((avg * count) + best_price) / (count + 1)
            component.price_update_count = count + 1
            
            # Atualização dos dados do componente
            old = component.price
            component.old_price = old
            component.price = best_price
            component.affiliate_link = best_link  # VINCULA O LINK REAL AQUI
            component.ai_recommendation = persona_alvo
            
            db.session.commit()
            
            logger.info(f"🎯 LINK CAPTURADO: R$ {old} -> R$ {best_price}")
            return True
            
        return False
    except Exception as e:
        logger.error(f"Erro na busca do componente {component.name}: {e}")
        return False

def process_batch(products_batch):
    """Inicia o navegador e processa um lote de produtos."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])
        context = browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        )
        
        # Bloqueio de recursos pesados para economizar RAM
        context.route("**/*", lambda route: route.abort() 
                      if route.request.resource_type in ["image", "media", "font", "stylesheet"] 
                      else route.continue_())
        
        page = context.new_page()
        
        for product in products_batch:
            status = search_lowest_price(product, page)
            if status == "CAPTCHA":
                browser.close()
                return False
            # Delay aleatório para simular comportamento humano
            time.sleep(random.uniform(4, 8))
            
        browser.close()
        return True

def run_bot():
    """Loop principal do bot Sniper."""
    app = create_app()
    with app.app_context():
        print("\n" + "="*50)
        print("♻️  HARDWARE SNIPER BOT V10 - MONITORAMENTO ATIVO")
        print("🎯 Lógica: Histórico + Médias + Links Reais + Anti-Cegueira")
        print("="*50 + "\n")
        
        while True:
            all_products = Component.query.all()
            if not all_products:
                print("❌ Banco de dados vazio. Encerrando.")
                break
                
            random.shuffle(all_products)
            batch_size = 15
            
            for i in range(0, len(all_products), batch_size):
                batch = all_products[i:i + batch_size]
                print(f"\n🚀 LOTE {(i // batch_size) + 1} de {(len(all_products) // batch_size) + 1}")
                
                if not process_batch(batch):
                    print("🛡️ Bloqueio ou Captcha. Aguardando 120s...")
                    time.sleep(120)
                
                # Limpeza de memória
                gc.collect()
                print("🧹 RAM Reciclada.")
            
            print("\n💤 Ciclo finalizado. Reiniciando em 5 minutos...")
            time.sleep(300)

if __name__ == "__main__":
    run_bot()