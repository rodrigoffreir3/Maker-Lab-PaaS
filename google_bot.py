from brain.inference import predict_persona
from score_db import estimar_score 
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

logging.basicConfig(level=logging.INFO, format='%(asctime)s - BOT V19 - %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger("HardwareSniper.Construtor")

def generate_dynamic_targets():
    """Gera alvos com nomes simplificados para facilitar o match no score_db"""
    queries = []
    
    # GPUs NVIDIA e AMD
    for model in ["GTX 1650", "GTX 1660 Super", "RTX 3060", "RTX 4060", "RTX 4060 Ti", "RTX 4070", "RTX 4070 Ti", "RTX 4080"]:
        queries.append({"q": f"Placa de Vídeo {model}", "type": "gpu"})
    for model in ["RX 580 8GB", "RX 6600", "RX 7600", "RX 6750 XT", "RX 7800 XT"]:
        queries.append({"q": f"Placa de Vídeo {model}", "type": "gpu"})

    # CPUs Intel e AMD (Nomes normalizados para o dicionário)
    for model in ["i3-10100F", "i3-12100F", "i5-10400F", "i5-12400F", "i5-13400F", "i7-13700K", "i9-14900K"]:
        queries.append({"q": f"Processador Intel Core {model}", "type": "cpu"})
    for model in ["Ryzen 3 3200G", "Ryzen 5 4600G", "Ryzen 5 5500", "Ryzen 5 5600", "Ryzen 5 5600G", "Ryzen 7 5700X", "Ryzen 7 5700G", "Ryzen 7 5800X3D", "Ryzen 5 7600", "Ryzen 7 7800X3D"]:
        queries.append({"q": f"Processador AMD {model}", "type": "cpu"})

    # RAM e SSD
    for size in ["8GB", "16GB"]:
        queries.append({"q": f"Memoria RAM {size} DDR4 3200MHz", "type": "ram"})
    for size in ["480GB", "1TB", "2TB"]:
        queries.append({"q": f"SSD {size} NVMe M.2", "type": "ssd"})

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

def clean_price_and_check_used(text):
    if not text: return None, False
    try:
        text_lower = text.lower()
        is_used = any(k in text_lower for k in ["usado", "seminovo", "recondicionado", "open box"])
        
        # Limpeza robusta de pontuação brasileira
        text = text.replace('\xa0', ' ').replace('.', '').replace(',', '.')
        match = re.search(r'R\$\s?([\d.]+)', text)
        if match:
            return float(match.group(1)), is_used
        return None, is_used
    except:
        return None, False

def calculate_dynamic_ref_price(score, comp_type):
    """Estima preço base para evitar lixo (cabos/coolers)"""
    if score <= 0: return 500 # Fallback maior para evitar ignorar itens por score zero
    if comp_type == 'gpu': return score * 0.12
    if comp_type == 'cpu': return score * 0.06
    if comp_type == 'ram': return score * 0.08
    if comp_type == 'ssd': return score * 0.15
    return 200

def process_target(target, page):
    db_name = target['q']
    comp_type = target['type']
    
    # NORMALIZAÇÃO: Remove prefixos para bater com as chaves do score_db.py
    score_query = db_name.replace("Placa de Vídeo ", "").replace("Processador ", "").lower()
    score = estimar_score(score_query, comp_type)
    
    ref_price = calculate_dynamic_ref_price(score, comp_type)
    persona_alvo = sniper_audit(score if comp_type == 'cpu' else 10000, score if comp_type == 'gpu' else 1000)
    
    search_url = f"https://www.google.com/search?q={db_name} Novo&tbm=shop&hl=pt-BR"
    logger.info(f"🔎 Buscando: {db_name} | Score: {score} | Ref: R${ref_price:.0f}")
    
    try:
        # Aumento de Timeout para 40s e espera por rede ociosa
        page.goto(search_url, timeout=40000, wait_until='networkidle')
        page.mouse.wheel(0, 1000)
        page.wait_for_timeout(4000)

        if "recaptcha" in page.url:
            logger.warning("🛡️ CAPTCHA Detectado!")
            return "CAPTCHA"

        # Extrator JS focado em contêineres oficiais de produtos
        extracted_data = page.evaluate("""() => {
            let results = [];
            document.querySelectorAll('div[data-docid], .sh-dgr__content, .sh-dlr__list-result').forEach(el => {
                let a = el.querySelector('a');
                if (a && a.href && !a.href.includes('google.com')) {
                    results.push({ link: a.href, text: el.innerText });
                }
            });
            return results;
        }""")
        
        best_price = float('inf')
        best_link = None
        precos_vistos = []

        for item in extracted_data:
            price, is_used = clean_price_and_check_used(item['text'])
            if price and not is_used:
                precos_vistos.append(price)
                # Filtro dinâmico: Aceita de 20% a 400% da referência
                if (ref_price * 0.2) < price < (ref_price * 4.0):
                    if price < best_price:
                        best_price = price
                        best_link = item['link']

        if best_link and best_price != float('inf'):
            component = Component.query.filter_by(name=db_name).first()
            if not component:
                component = Component(
                    name=db_name, type=comp_type, price=best_price, performance_score=score,
                    generation=0, is_integrated_graphics="g" in db_name.lower(),
                    affiliate_link=best_link, ai_recommendation=persona_alvo
                )
                db.session.add(component)
                logger.info(f"✨ CRIADO: {db_name} - R${best_price}")
            else:
                component.old_price, component.price = component.price, best_price
                component.affiliate_link = best_link
                logger.info(f"🎯 ATUALIZADO: {db_name} - R${best_price}")
            
            db.session.commit()
            return True
        else:
            vistos = str(precos_vistos[:5]) if precos_vistos else "Vazio"
            logger.warning(f"⚠️ FALHA: {db_name} não passou no filtro. Vistos: {vistos}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Erro em {db_name}: {e}")
        return False

def process_batch(targets_batch, page):
    for target in targets_batch:
        status = process_target(target, page)
        if status == "CAPTCHA": return False
        time.sleep(random.uniform(5, 10))
    return True

def run_bot():
    app = create_app()
    with app.app_context():
        print("\n" + "="*50)
        print("🏗️  HARDWARE SNIPER BOT V19 - MODO EXTERMINADOR")
        print("🎯 Lógica: Match de Nome Agressivo + Extração de Contêiner")
        print("="*50 + "\n")
        
        while True:
            targets = generate_dynamic_targets()
            batch_size = 10
            
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=False)
                context = browser.new_context(viewport={'width': 1280, 'height': 800})
                page = context.new_page()
                
                for i in range(0, len(targets), batch_size):
                    batch = targets[i:i + batch_size]
                    print(f"\n🚀 LOTE {(i // batch_size) + 1}")
                    if not process_batch(batch, page):
                        print("🛡️ Bloqueio detectado. Pausando 120s...")
                        time.sleep(120)
                        break
                    gc.collect()
                
                browser.close()
            
            print("\n💤 Ciclo finalizado. Reiniciando em 5 minutos...")
            time.sleep(300)

if __name__ == "__main__":
    run_bot()