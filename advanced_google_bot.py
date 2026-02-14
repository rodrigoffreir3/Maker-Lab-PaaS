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
logging.basicConfig(level=logging.INFO, format='%(asctime)s - BOT V18 ADVANCED - %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger("HardwareSniper.AdvancedBuilder")

# ==========================================
# 🎯 DYNAMIC TARGET GENERATION
# ==========================================
def generate_search_queries():
    """Generates a more realistic and comprehensive list of search queries."""
    queries = []

    # GPUs - NVIDIA
    for series, models in {
        "GTX": ["750 Ti", "960", "970", "1050 Ti", "1060 6GB", "1070", "1080 Ti", "1650", "1660 Super"],
        "RTX": ["2060", "2060 Super", "2070", "2080 Ti", "3050", "3060", "3060 Ti", "3070", "3080", "3090", "4060", "4060 Ti", "4070", "4080", "4090"]
    }.items():
        for model in models:
            queries.append({"q": f"Placa de Vídeo GeForce {series} {model}", "type": "gpu"})

    # GPUs - AMD
    for series, models in {
        "RX": ["550", "560", "570 4GB", "580 8GB", "5500 XT", "5600 XT", "5700 XT", "6600", "6600 XT", "6700 XT", "6800", "6900 XT", "7600", "7700 XT", "7800 XT", "7900 XTX"]
    }.items():
        for model in models:
            queries.append({"q": f"Placa de Vídeo Radeon {series} {model}", "type": "gpu"})

    # CPUs - Intel
    for series, gens in {
        "Core i3": ["2100", "3220", "4130", "6100", "7100", "8100", "9100F", "10100F", "12100F"],
        "Core i5": ["2500K", "3570K", "4690K", "6600K", "7600K", "8400", "9400F", "10400F", "11400F", "12400F", "13400F"],
        "Core i7": ["2600K", "3770K", "4790K", "6700K", "7700K", "8700K", "9700K", "10700K", "11700K", "12700K", "13700K"],
        "Core i9": ["9900K", "10900K", "11900K", "12900K", "13900K"]
    }.items():
        for gen_model in gens:
            queries.append({"q": f"Processador Intel {series} {gen_model}", "type": "cpu"})

    # CPUs - AMD
    for series, models in {
        "Ryzen 3": ["1200", "2200G", "3200G", "4100"],
        "Ryzen 5": ["1600", "2600", "3600", "4600G", "5500", "5600", "5600X", "7600X"],
        "Ryzen 7": ["1700", "2700X", "3700X", "5700G", "5700X", "5800X", "5800X3D", "7700X"],
        "Ryzen 9": ["3900X", "5900X", "5950X", "7900X", "7950X"]
    }.items():
        for model in models:
            queries.append({"q": f"Processador AMD {series} {model}", "type": "cpu"})

    # RAM
    for ddr_type in ["DDR3", "DDR4", "DDR5"]:
        for size in [4, 8, 16, 32]:
            # DDR3 has lower speeds
            if ddr_type == "DDR3":
                speeds = [1333, 1600, 1866]
            # DDR5 has higher speeds
            elif ddr_type == "DDR5":
                speeds = [4800, 5200, 5600, 6000, 6400]
            else: # DDR4
                speeds = [2133, 2400, 2666, 3000, 3200, 3600]
            for speed in speeds:
                queries.append({"q": f"Memoria RAM {size}GB {ddr_type} {speed}MHz", "type": "ram"})

    # SSDs
    for size in [120, 240, 256, 480, 500, 512, 1000, 2000, 4000]:
        for tech in ["SATA", "NVMe M.2"]:
            queries.append({"q": f"SSD {size}GB {tech}", "type": "ssd"})

    # HDs
    for size in [500, 1000, 2000, 4000, 8000]:
        queries.append({"q": f"HD {size}GB SATA 3.5", "type": "hd"})

    # Power Supplies
    for wattage in [450, 500, 550, 600, 650, 750, 850, 1000, 1200]:
        for cert in ["80 Plus", "80 Plus Bronze", "80 Plus Gold"]:
            queries.append({"q": f"Fonte {wattage}W {cert}", "type": "power_supply"})

    # Motherboards
    for chipset in ["A320M", "B450M", "B550", "X570", "A520M", "H310M", "B360M", "H410M", "B460M", "Z490", "H510M", "B560M", "Z590", "B660M", "Z690", "B760", "Z790"]:
        queries.append({"q": f"Placa Mae {chipset}", "type": "motherboard"})

    random.shuffle(queries)
    return queries


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
    if not text: return None, False
    try:
        text_lower = text.lower()
        # More robust check for used items
        is_used = any(keyword in text_lower for keyword in ["usado", "seminovo", "recondicionado", "open box", "de vitrine"])

        text = text.replace('\xa0', ' ').strip()
        # Price cleaning logic remains the same
        blacklist = [r'/mês', r'x\s\d+', r'\d+x', r'juros', r'entrada', r'cada', r'\(']
        for term in blacklist:
            if re.search(term, text, re.IGNORECASE): return None, is_used
        match = re.search(r'R\$\s*([\d.,]+)', text)
        if match:
            num_str = match.group(1)
            if num_str.count('.') > 1:
                num_str = num_str.replace('.', '', num_str.count('.') - 1)
            return float(num_str.replace('.', '').replace(',', '.')), is_used
        return None, is_used
    except:
        return None, False

def process_target(target, page):
    db_name = target['q']
    
    search_url = f"https://www.google.com/search?q={db_name}&tbm=shop&hl=pt-BR"
    logger.info(f"🔎 Buscando: {db_name}")
    
    try:
        page.goto(search_url, timeout=25000, wait_until='domcontentloaded')
        
        page.mouse.wheel(0, 800)
        page.wait_for_timeout(2500)

        if "recaptcha" in page.url:
            logger.warning("🛡️ CAPTCHA Detectado!")
            return "CAPTCHA"

        js_extractor = """
        () => {
            let items = [];
            document.querySelectorAll('a').forEach(a => {
                let href = a.href;
                if (href && !href.startsWith('javascript') && !href.includes('google.com/search') && !href.includes('google.com/preferences')) {
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
        
        new_items = []
        for item in extracted_data:
            price, is_used = clean_price(item.get('text', ''))
            # CRITICAL CHANGE: If the item is marked as used, we do not process it further.
            if price and item.get('link') and not is_used:
                new_items.append({'price': price, 'link': item.get('link')})
        
        if not new_items:
            logger.warning(f"⚠️ Nenhuma oferta de produto NOVO encontrada para {db_name}")
            return False

        # Find the best price among the new items
        for item in new_items:
            if item['price'] < best_price:
                best_price = item['price']
                best_link = item['link']

        if best_price != float('inf') and best_link:
            # The rest of the logic for saving to the database
            component = Component.query.filter_by(name=db_name).first()
            
            performance_score = get_performance_score(db_name, target['type'])
            generation = get_generation(db_name)
            is_integrated_graphics = "g" in db_name.lower() and target['type'] == 'cpu'
            
            persona_alvo = sniper_audit(performance_score, performance_score)

            if not component:
                component = Component(
                    name=db_name,
                    type=target['type'],
                    price=best_price,
                    performance_score=performance_score,
                    generation=generation,
                    is_integrated_graphics=is_integrated_graphics,
                    affiliate_link=best_link,
                    ai_recommendation=persona_alvo,
                    is_used=False # It will always be false here
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
                component.is_used = False # It will always be false here
                
                logger.info(f"🎯 PREÇO ATUALIZADO: R$ {old} -> R$ {best_price}")
            
            db.session.commit()
            return True
        else:
            logger.warning(f"⚠️ Nenhuma oferta encontrada para {db_name}")
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

def clear_database():
    """Clears all the data from the Component table."""
    try:
        db.session.query(Component).delete()
        db.session.commit()
        logger.info("🧹 Banco de dados limpo com sucesso!")
    except Exception as e:
        logger.error(f"Erro ao limpar o banco de dados: {e}")
        db.session.rollback()

def run_bot(total_items_to_process=1000, sleep_time_between_cycles_in_minutes=60):
    app = create_app()
    with app.app_context():
        print("="*50)
        print("🚀 ADVANCED HARDWARE SNIPER BOT V19 - O CONSTRUTOR MELHORADO")
        print("🎯 Lógica: Geração Dinâmica de Alvos, Exclusão de Usados, Operação Contínua")
        print("="*50)
        
        while True:
            clear_database()
            
            targets = generate_search_queries()
            random.shuffle(targets) # Shuffle to get different items each run
            
            # Limit the number of items to process in this cycle
            targets_to_process = targets[:total_items_to_process]
            
            batch_size = 5
            items_processed = 0
            
            for i in range(0, len(targets_to_process), batch_size):
                batch = targets_to_process[i:i + batch_size]
                print(f"\n🚀 LOTE {(i // batch_size) + 1} de {len(targets_to_process) // batch_size}")
                
                if not process_batch(batch):
                    print("🛡️ Bloqueio ou Captcha. Aguardando 120s...")
                    time.sleep(120)
                
                items_processed += len(batch)
                gc.collect()
                print(f"🧹 RAM Reciclada. {items_processed} de {len(targets_to_process)} itens processados neste ciclo.")
            
            print(f"\n🏁 Ciclo finalizado. O bot processou {items_processed} itens.")
            print(f"💤 Aguardando {sleep_time_between_cycles_in_minutes} minutos para o próximo ciclo...")
            time.sleep(sleep_time_between_cycles_in_minutes * 60)

if __name__ == "__main__":
    run_bot(total_items_to_process=10, sleep_time_between_cycles_in_minutes=1)