from brain.inference import predict_persona
import time
import random
import re
import os
import gc
import warnings
from playwright.sync_api import sync_playwright
from app import create_app
from models import db, Component
import logging

# --- SILENCIADOR DA IA ---
warnings.filterwarnings("ignore", category=UserWarning)

# --- LOGS ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - BOT V17 - %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger("HardwareSniper.Construtor")

# ==========================================
# 🎯 MASTER TARGET LIST
# ==========================================
MASTER_LIST = [
    # --- GPUs ---
    {"q": "Placa de Vídeo GeForce GT 730 4GB", "type": "gpu", "score": 900, "ref_price": 300, "is_int": False},
    {"q": "Placa de Vídeo GeForce GT 1030 2GB", "type": "gpu", "score": 2600, "ref_price": 450, "is_int": False},
    {"q": "Placa de Vídeo Radeon RX 580 8GB", "type": "gpu", "score": 8700, "ref_price": 600, "is_int": False},
    {"q": "Placa de Vídeo GeForce GTX 1650 4GB", "type": "gpu", "score": 7800, "ref_price": 850, "is_int": False},
    {"q": "Placa de Vídeo GeForce GTX 1660 Super 6GB", "type": "gpu", "score": 12700, "ref_price": 1200, "is_int": False},
    {"q": "Placa de Vídeo Radeon RX 6600 8GB", "type": "gpu", "score": 15000, "ref_price": 1350, "is_int": False},
    {"q": "Placa de Vídeo GeForce RTX 3050 8GB", "type": "gpu", "score": 12800, "ref_price": 1400, "is_int": False},
    {"q": "Placa de Vídeo GeForce RTX 3060 12GB", "type": "gpu", "score": 17000, "ref_price": 1700, "is_int": False},
    {"q": "Placa de Vídeo Radeon RX 7600 8GB", "type": "gpu", "score": 16500, "ref_price": 1750, "is_int": False},
    {"q": "Placa de Vídeo GeForce RTX 4060 8GB", "type": "gpu", "score": 19500, "ref_price": 1900, "is_int": False},
    {"q": "Placa de Vídeo GeForce RTX 4060 Ti 8GB", "type": "gpu", "score": 22500, "ref_price": 2500, "is_int": False},
    {"q": "Placa de Vídeo Radeon RX 6750 XT 12GB", "type": "gpu", "score": 22000, "ref_price": 2400, "is_int": False},
    {"q": "Placa de Vídeo GeForce RTX 4070 12GB", "type": "gpu", "score": 27000, "ref_price": 3800, "is_int": False},
    {"q": "Placa de Vídeo GeForce RTX 4070 Ti 12GB", "type": "gpu", "score": 31000, "ref_price": 5000, "is_int": False},
    {"q": "Placa de Vídeo Radeon RX 7800 XT 16GB", "type": "gpu", "score": 28000, "ref_price": 4200, "is_int": False},
    {"q": "Placa de Vídeo GeForce RTX 4080 16GB", "type": "gpu", "score": 35000, "ref_price": 7500, "is_int": False},

    # --- CPUs ---
    {"q": "Processador Intel Core i3 10100F", "type": "cpu", "score": 8900, "ref_price": 450, "is_int": False},
    {"q": "Processador Intel Core i3 12100F", "type": "cpu", "score": 14500, "ref_price": 600, "is_int": False},
    {"q": "Processador Intel Core i5 10400F", "type": "cpu", "score": 12500, "ref_price": 600, "is_int": False},
    {"q": "Processador Intel Core i5 12400F", "type": "cpu", "score": 19500, "ref_price": 850, "is_int": False},
    {"q": "Processador Intel Core i5 13400F", "type": "cpu", "score": 26000, "ref_price": 1300, "is_int": False},
    {"q": "Processador Intel Core i7 13700K", "type": "cpu", "score": 46000, "ref_price": 2800, "is_int": True},
    {"q": "Processador Ryzen 3 3200G", "type": "cpu", "score": 7200, "ref_price": 450, "is_int": True},
    {"q": "Processador Ryzen 5 4600G", "type": "cpu", "score": 16200, "ref_price": 650, "is_int": True},
    {"q": "Processador Ryzen 5 5500", "type": "cpu", "score": 19500, "ref_price": 600, "is_int": False},
    {"q": "Processador Ryzen 5 5600G", "type": "cpu", "score": 19800, "ref_price": 850, "is_int": True},
    {"q": "Processador Ryzen 5 5600", "type": "cpu", "score": 21500, "ref_price": 850, "is_int": False},
    {"q": "Processador Ryzen 7 5700X", "type": "cpu", "score": 26800, "ref_price": 1200, "is_int": False},
    {"q": "Processador Ryzen 7 5700G", "type": "cpu", "score": 24500, "ref_price": 1250, "is_int": True},
    {"q": "Processador Ryzen 7 5800X3D", "type": "cpu", "score": 28000, "ref_price": 2000, "is_int": False},
    {"q": "Processador Ryzen 5 7600", "type": "cpu", "score": 29000, "ref_price": 1400, "is_int": True},

    # --- RAM ---
    {"q": "Memoria RAM 8GB DDR4 2666MHz", "type": "ram", "score": 2666, "ref_price": 130, "is_int": False},
    {"q": "Memoria RAM 8GB DDR4 3200MHz", "type": "ram", "score": 3200, "ref_price": 140, "is_int": False},
    {"q": "Memoria RAM 16GB DDR4 3200MHz", "type": "ram", "score": 3200, "ref_price": 250, "is_int": False},
    {"q": "Memoria RAM 16GB DDR5 5200MHz", "type": "ram", "score": 5200, "ref_price": 350, "is_int": False},
    {"q": "Memoria RAM 32GB DDR5 6000MHz", "type": "ram", "score": 6000, "ref_price": 750, "is_int": False},

    # --- SSD ---
    {"q": "SSD 240GB SATA", "type": "ssd", "score": 500, "ref_price": 120, "is_int": False},
    {"q": "SSD 480GB SATA", "type": "ssd", "score": 550, "ref_price": 180, "is_int": False},
    {"q": "SSD 500GB NVMe M.2", "type": "ssd", "score": 3500, "ref_price": 250, "is_int": False},
    {"q": "SSD 1TB NVMe M.2", "type": "ssd", "score": 4000, "ref_price": 400, "is_int": False},
    {"q": "SSD 2TB NVMe M.2", "type": "ssd", "score": 4200, "ref_price": 800, "is_int": False},
]

def sniper_audit(c_score, g_score):
    try:
        persona = predict_persona(c_score, g_score, 16, 1)
        if "gamer" in persona.lower(): return "Gamer"
        if "office" in persona.lower() or "multitask" in persona.lower(): return "Office/Multitask"
        if "workstation" in persona.lower() or "editor" in persona.lower(): return "Workstation/Editor"
        return "Gamer"
    except:
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
    except:
        return None

def process_target(target, page):
    db_name = target['q']
    c_score = target['score'] if target['type'] == 'cpu' else 10000
    g_score = target['score'] if target['type'] == 'gpu' else 1000
    persona_alvo = sniper_audit(c_score, g_score)
    ref_price = target['ref_price']
    
    # Adicionando o "Novo" de volta para garantir foco do algoritmo do Google, sem quebrar a busca
    search_url = f"https://www.google.com/search?q={db_name} Novo&tbm=shop&hl=pt-BR"
    logger.info(f"🔎 Buscando: {db_name} | Foco IA: {persona_alvo}")
    
    try:
        page.goto(search_url, timeout=25000, wait_until='domcontentloaded')
        
        # Scroll para descer e ativar imagens (Lazy Loading)
        page.mouse.wheel(0, 800)
        page.wait_for_timeout(2500)

        if "recaptcha" in page.url:
            logger.warning("🛡️ CAPTCHA Detectado!")
            return "CAPTCHA"

        # JS Extractor focado em capturar links de produtos reais
        js_extractor = """
        () => {
            let items = [];
            let links = document.querySelectorAll('a');
            links.forEach(a => {
                let href = a.href;
                // Exclui links internos irrelevantes do google
                if (href && !href.startsWith('javascript') && !href.includes('google.com/search') && !href.includes('google.com/preferences')) {
                    // Tem que ser um link de redirecionamento de oferta ou da própria loja
                    let is_product = href.includes('/shopping/product') || href.includes('/aclk') || href.includes('url?url=') || !href.includes('google.com');
                    
                    if(is_product) {
                        let container = a.parentElement;
                        for(let i = 0; i < 6; i++) {
                            if (container && container.innerText && container.innerText.includes('R$')) {
                                items.push({ link: href, text: container.innerText });
                                break;
                            }
                            if (container) container = container.parentElement;
                        }
                    }
                }
            });
            return items;
        }
        """
        
        extracted_data = page.evaluate(js_extractor)
        
        best_price = float('inf')
        best_link = None
        
        # --- RADAR DE DEBUG ---
        precos_vistos = []

        for item in extracted_data:
            price = clean_price(item.get('text', ''))
            href = item.get('link', '')
            
            if price and href:
                precos_vistos.append(price)
                # Filtro: A peça tem que custar no mínimo 35% e no máximo 300% (3.0x) do preço base
                if (ref_price * 0.35) < price < (ref_price * 3.0):
                    if price < best_price:
                        best_price = price
                        best_link = f"https://www.google.com{href}" if href.startswith('/') else href

        if best_price != float('inf') and best_link:
            component = Component.query.filter_by(name=db_name).first()
            
            if not component:
                component = Component(
                    name=db_name,
                    type=target['type'],
                    price=best_price,
                    performance_score=target['score'],
                    generation=0,
                    is_integrated_graphics=target['is_int'],
                    affiliate_link=best_link,
                    ai_recommendation=persona_alvo
                )
                db.session.add(component)
                logger.info(f"✨ NOVA PEÇA CRIADA: {db_name} por R$ {best_price}")
            else:
                if component.min_price_historic is None or best_price < component.min_price_historic:
                    component.min_price_historic = best_price
                
                count = component.price_update_count or 0
                avg = component.avg_price_historic or best_price
                component.avg_price_historic = ((avg * count) + best_price) / (count + 1)
                component.price_update_count = count + 1
                
                old = component.price
                component.old_price = old
                component.price = best_price
                component.affiliate_link = best_link  
                component.ai_recommendation = persona_alvo
                
                logger.info(f"🎯 PREÇO ATUALIZADO: R$ {old} -> R$ {best_price}")
            
            db.session.commit()
            return True
        else:
            # Se falhou, me avisa O QUE ele enxergou na tela para diagnosticarmos
            vistos_str = str(precos_vistos[:5]) if precos_vistos else "Nenhum R$ lido"
            logger.warning(f"⚠️ IGNORADO. Ref: R${ref_price} | Lidos na tela: {vistos_str}")
            return False
            
    except Exception as e:
        logger.error(f"Erro na busca de {db_name}: {e}")
        return False

def process_batch(targets_batch):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])
        context = browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        )
        
        context.route("**/*", lambda route: route.abort() 
                      if route.request.resource_type in ["image", "media", "font", "stylesheet"] 
                      else route.continue_())
        
        page = context.new_page()
        
        for target in targets_batch:
            status = process_target(target, page)
            if status == "CAPTCHA":
                browser.close()
                return False
            time.sleep(random.uniform(4, 7))
            
        browser.close()
        return True

def run_bot():
    app = create_app()
    with app.app_context():
        print("\n" + "="*50)
        print("🏗️  HARDWARE SNIPER BOT V17 - O VIDENTE")
        print("🎯 Lógica: Remoção de -usado + Radar de Preços")
        print("="*50 + "\n")
        
        while True:
            targets_shuffled = MASTER_LIST.copy()
            random.shuffle(targets_shuffled)
            
            batch_size = 10
            
            for i in range(0, len(targets_shuffled), batch_size):
                batch = targets_shuffled[i:i + batch_size]
                print(f"\n🚀 LOTE {(i // batch_size) + 1} de {(len(targets_shuffled) // batch_size) + 1}")
                
                if not process_batch(batch):
                    print("🛡️ Bloqueio ou Captcha. Aguardando 120s...")
                    time.sleep(120)
                
                gc.collect()
                print("🧹 RAM Reciclada.")
            
            print("\n💤 Ciclo finalizado. Reiniciando em 5 minutos...")
            time.sleep(300)

if __name__ == "__main__":
    run_bot()