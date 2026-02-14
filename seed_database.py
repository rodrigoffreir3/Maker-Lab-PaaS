import random
from app import create_app
from models import db, Component

# --- CONFIGURAÇÃO DA SIMULAÇÃO DE MERCADO (FEV 2026) ---
LOJAS = ["Kabum", "Terabyte", "Pichau", "Amazon", "Mercado Livre", "Girafa"]

# --- 1. PLACAS DE VÍDEO ---
BASE_GPUS = [
    {"model": "GeForce GT 210", "score": 180, "price_base": 120, "vram": "1GB"},
    {"model": "GeForce GT 610", "score": 350, "price_base": 180, "vram": "2GB"},
    {"model": "GeForce GT 710", "score": 650, "price_base": 220, "vram": "2GB"},
    {"model": "GeForce GT 730", "score": 900, "price_base": 290, "vram": "4GB"},
    {"model": "GeForce GT 1030", "score": 2600, "price_base": 399, "vram": "2GB"},
    {"model": "Radeon RX 550", "score": 2800, "price_base": 450, "vram": "4GB"},
    {"model": "Radeon RX 580 2048SP", "score": 8700, "price_base": 650, "vram": "8GB"},
    {"model": "GeForce GTX 1650", "score": 7800, "price_base": 799, "vram": "4GB"},
    {"model": "GeForce GTX 1660 Super", "score": 12700, "price_base": 1100, "vram": "6GB"},
    {"model": "Radeon RX 6600", "score": 15000, "price_base": 1299, "vram": "8GB"},
    {"model": "GeForce RTX 3050", "score": 12800, "price_base": 1350, "vram": "8GB"},
    {"model": "GeForce RTX 2060", "score": 14000, "price_base": 1400, "vram": "6GB"},
    {"model": "GeForce RTX 3060", "score": 17000, "price_base": 1699, "vram": "12GB"},
    {"model": "Radeon RX 7600", "score": 16500, "price_base": 1650, "vram": "8GB"},
    {"model": "GeForce RTX 4060", "score": 19500, "price_base": 1850, "vram": "8GB"},
    {"model": "GeForce RTX 4060 Ti", "score": 22500, "price_base": 2400, "vram": "8GB"},
    {"model": "Radeon RX 6750 XT", "score": 22000, "price_base": 2200, "vram": "12GB"},
    {"model": "GeForce RTX 3070", "score": 22000, "price_base": 2600, "vram": "8GB"},
    {"model": "GeForce RTX 4070", "score": 27000, "price_base": 3600, "vram": "12GB"},
    {"model": "Radeon RX 7700 XT", "score": 24000, "price_base": 3100, "vram": "12GB"},
    {"model": "GeForce RTX 4070 Ti", "score": 31000, "price_base": 4800, "vram": "12GB"},
    {"model": "Radeon RX 7800 XT", "score": 28000, "price_base": 3900, "vram": "16GB"},
    {"model": "GeForce RTX 4080", "score": 35000, "price_base": 7000, "vram": "16GB"},
    {"model": "Radeon RX 7900 XTX", "score": 31000, "price_base": 6500, "vram": "24GB"},
    {"model": "GeForce RTX 4090", "score": 39000, "price_base": 11000, "vram": "24GB"},
]
BRANDS_GPU = ["Asus", "Gigabyte", "MSI", "Galax", "Palit", "XFX", "Sapphire", "PowerColor", "Zotac"]

# --- 2. PROCESSADORES ---
BASE_CPUS = [
    {"model": "Athlon 3000G", "score": 4500, "price_base": 250, "integrated": True},
    {"model": "Intel Core i5-3470 (Usado)", "score": 4600, "price_base": 150, "integrated": True},
    {"model": "Intel Core i7-4790 (Usado)", "score": 7200, "price_base": 300, "integrated": True},
    {"model": "Ryzen 3 3200G", "score": 7200, "price_base": 450, "integrated": True},
    {"model": "Ryzen 3 4100", "score": 11000, "price_base": 380, "integrated": False},
    {"model": "Intel Core i3-10100F", "score": 8900, "price_base": 399, "integrated": False},
    {"model": "Intel Core i3-12100F", "score": 14500, "price_base": 599, "integrated": False},
    {"model": "Ryzen 5 4500", "score": 15800, "price_base": 480, "integrated": False},
    {"model": "Ryzen 5 4600G", "score": 16200, "price_base": 620, "integrated": True},
    {"model": "Ryzen 5 5500", "score": 19500, "price_base": 599, "integrated": False},
    {"model": "Ryzen 5 5600G", "score": 19800, "price_base": 850, "integrated": True},
    {"model": "Ryzen 5 5600", "score": 21500, "price_base": 799, "integrated": False},
    {"model": "Intel Core i5-12400F", "score": 19500, "price_base": 850, "integrated": False},
    {"model": "Ryzen 5 5600GT", "score": 20000, "price_base": 830, "integrated": True},
    {"model": "Intel Core i5-10400F", "score": 12500, "price_base": 600, "integrated": False},
    {"model": "Ryzen 7 5700X", "score": 26800, "price_base": 1100, "integrated": False},
    {"model": "Ryzen 7 5700G", "score": 24500, "price_base": 1200, "integrated": True},
    {"model": "Ryzen 7 5800X3D", "score": 28000, "price_base": 1900, "integrated": False},
    {"model": "Intel Core i5-13400F", "score": 26000, "price_base": 1300, "integrated": False},
    {"model": "Intel Core i5-13600K", "score": 38000, "price_base": 2100, "integrated": True},
    {"model": "Ryzen 5 7600", "score": 29000, "price_base": 1400, "integrated": True},
    {"model": "Ryzen 7 7800X3D", "score": 55000, "price_base": 2800, "integrated": True},
    {"model": "Intel Core i7-13700K", "score": 46000, "price_base": 2900, "integrated": True},
    {"model": "Intel Core i9-14900K", "score": 62000, "price_base": 4500, "integrated": True},
]

# --- 3. MEMÓRIA RAM ---
BASE_RAMS = [
    {"type": "DDR3", "cap": "4GB", "mhz": 1333, "price": 30},
    {"type": "DDR3", "cap": "8GB", "mhz": 1600, "price": 60},
    {"type": "DDR4", "cap": "4GB", "mhz": 2400, "price": 50},
    {"type": "DDR4", "cap": "8GB", "mhz": 2666, "price": 110},
    {"type": "DDR4", "cap": "8GB", "mhz": 3200, "price": 140},
    {"type": "DDR4", "cap": "16GB", "mhz": 3200, "price": 230},
    {"type": "DDR4", "cap": "8GB", "mhz": 3600, "price": 160},
    {"type": "DDR4", "cap": "16GB", "mhz": 3600, "price": 280},
    {"type": "DDR4", "cap": "32GB", "mhz": 3200, "price": 450},
    {"type": "DDR5", "cap": "16GB", "mhz": 5200, "price": 350},
    {"type": "DDR5", "cap": "16GB", "mhz": 6000, "price": 420},
    {"type": "DDR5", "cap": "32GB", "mhz": 6000, "price": 750},
]
BRANDS_RAM = ["Kingston", "XPG", "Corsair", "HyperX", "Crucial", "Mancer", "Husky", "TeamGroup"]

# --- 4. SSDs ---
BASE_SSDS = [
    {"type": "SATA", "cap": "120GB", "price": 60, "score": 450},
    {"type": "SATA", "cap": "240GB", "price": 100, "score": 500},
    {"type": "SATA", "cap": "480GB", "price": 200, "score": 550},
    {"type": "SATA", "cap": "960GB", "price": 350, "score": 600},
    {"type": "NVMe", "cap": "250GB", "price": 130, "score": 2500},
    {"type": "NVMe", "cap": "500GB", "price": 230, "score": 3500},
    {"type": "NVMe", "cap": "1TB", "price": 390, "score": 4000},
    {"type": "NVMe", "cap": "2TB", "price": 750, "score": 4200},
    {"type": "NVMe Gen4", "cap": "1TB", "price": 550, "score": 7000},
    {"type": "NVMe Gen4", "cap": "2TB", "price": 990, "score": 7500},
]
BRANDS_SSD = ["Kingston", "WD Green", "WD Blue", "Samsung", "Crucial", "XPG", "Gigabyte", "Mancer"]

def generate_products():
    final_list = []
    names_seen = set()

    def add_product(item):
        original_name = item['name']
        counter = 2
        while item['name'] in names_seen:
            item['name'] = f"{original_name} V{counter}"
            counter += 1
        names_seen.add(item['name'])
        final_list.append(item)

    # --- GERADORES ---
    categories = [
        ('gpu', BASE_GPUS, BRANDS_GPU, 'price_base', 'vram'),
        ('cpu', BASE_CPUS, None, 'price_base', None),
        ('ram', BASE_RAMS, BRANDS_RAM, 'price', 'type'),
        ('ssd', BASE_SSDS, BRANDS_SSD, 'price', 'cap')
    ]

    for p_type, base_list, brands, p_key, extra_key in categories:
        target = 50
        count = 0
        while count < target:
            base = random.choice(base_list)
            store = random.choice(LOJAS)
            p_base = base[p_key]
            price_var = round(p_base * random.uniform(0.9, 1.15), 2)
            
            if p_type == 'gpu':
                brand = random.choice(brands)
                name = f"[{store}] Placa de Vídeo {brand} {base['model']} {base['vram']}"
                is_int = False
            elif p_type == 'cpu':
                suffix = random.choice(["Box", "Tray", "OEM", ""])
                name = f"[{store}] Processador {base['model']} {suffix}".strip()
                is_int = base['integrated']
            elif p_type == 'ram':
                brand = random.choice(brands)
                name = f"[{store}] Memória RAM {brand} {base['cap']} {base['type']} {base['mhz']}MHz"
                is_int = False
            else: # ssd
                brand = random.choice(brands)
                name = f"[{store}] SSD {brand} {base['cap']} {base['type']}"
                is_int = False

            add_product({
                "name": name, "type": p_type, "price": price_var,
                "score": base['score'] if p_type != 'ram' else base['mhz'],
                "is_int": is_int, "link": f"https://fake-link.com/{p_type}/{random.randint(1000,99999)}"
            })
            count += 1
    return final_list

def seed():
    app = create_app()
    with app.app_context():
        print("🧹 Limpando banco de dados...")
        db.drop_all()
        db.create_all()
        
        print("🌱 Populando 200 itens com Histórico Inicial...")
        produtos = generate_products()
        
        for p in produtos:
            novo = Component(
                name=p['name'],
                type=p['type'],
                price=p['price'],
                performance_score=p['score'],
                generation=0,
                is_integrated_graphics=p['is_int'],
                affiliate_link=p['link']
            )
            # Garantindo que o histórico inicial não seja nulo
            novo.min_price_historic = p['price']
            novo.avg_price_historic = p['price']
            novo.price_update_count = 1
            db.session.add(novo)
        
        db.session.commit()
        print("\n🚀 Banco Resetado e Populado! Todos os campos de Histórico estão ativos.")

if __name__ == "__main__":
    seed()