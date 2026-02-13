import logging
import os
from flask import Flask, render_template, request
from models import db, Component
from sqlalchemy import desc

# --- CONFIGURAÇÃO DE LOGS ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("HardwareSniper.App")

def create_app():
    app = Flask(__name__)
    
    # Caminho absoluto para o banco (Evita erros de pasta)
    basedir = os.path.abspath(os.path.dirname(__file__))
    db_path = os.path.join(basedir, 'instance', 'hardware.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)
    
    with app.app_context():
        db.create_all()
        
    return app

app = create_app()

# --- ROTAS ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/recomendar', methods=['POST'])
def recomendar():
    try:
        # Tratamento de input (R$, pontos, vírgulas)
        try:
            orcamento_str = request.form.get('budget', '0')
            orcamento_clean = str(orcamento_str).replace('R$', '').replace('.', '').replace(',', '.')
            orcamento = float(orcamento_clean)
        except ValueError:
            return render_template('index.html', error="Digite um valor numérico válido.")

        logger.info(f"💰 Novo pedido: R$ {orcamento}")

        if orcamento < 800:
             return render_template('index.html', error=f"Com R$ {orcamento} não dá pra montar um PC. Junte pelo menos R$ 1.000.")

        # --- 1. FATIAMENTO DO ORÇAMENTO ---
        # Definimos quanto gastar em cada peça
        alloc_gpu = 0.40  # 40%
        alloc_cpu = 0.25  # 25%
        alloc_ram = 0.15  # 15%
        
        saldo = orcamento
        bottleneck_warning = None

        # --- 2. ESCOLHA DA GPU (Placa de Vídeo) ---
        target_gpu = orcamento * alloc_gpu
        
        # O '# type: ignore' abaixo silencia o erro do VS Code
        gpu = Component.query.filter(
            Component.type == 'gpu', 
            Component.price <= target_gpu # type: ignore
        ).order_by(desc(Component.performance_score)).first() 

        # Se tem dinheiro mas não achou GPU (porque as do banco são caras), tenta esticar o budget
        if not gpu and orcamento > 2000:
            gpu = Component.query.filter(
                Component.type == 'gpu',
                Component.price <= (orcamento * 0.60) # type: ignore
            ).order_by(desc(Component.performance_score)).first()

        if gpu:
            saldo -= gpu.price
            logger.info(f"✅ GPU: {gpu.name} (R$ {gpu.price})")
        else:
            logger.info("⚠️ Sem GPU dedicada. Focando em Vídeo Integrado.")
            alloc_cpu += 0.35 # Joga o dinheiro da GPU para a CPU

        # --- 3. ESCOLHA DA CPU (Processador) ---
        target_cpu = orcamento * alloc_cpu
        
        query_cpu = Component.query.filter(
            Component.type == 'cpu', 
            Component.price <= target_cpu # type: ignore
        )
        
        # Se NÃO tem GPU, precisamos de vídeo integrado (APU)
        if not gpu:
            # Usamos '== True' com type ignore, é o jeito mais seguro
            query_cpu = query_cpu.filter(Component.is_integrated_graphics == True) # type: ignore
        
        cpu = query_cpu.order_by(desc(Component.performance_score)).first()

        # Fallback: Se não achou CPU ideal, pega a mais barata que funcione
        if not cpu:
            fallback_query = Component.query.filter(Component.type == 'cpu')
            if not gpu:
                fallback_query = fallback_query.filter(Component.is_integrated_graphics == True) # type: ignore
            cpu = fallback_query.order_by(Component.price).first()

        if cpu:
            saldo -= cpu.price
            logger.info(f"✅ CPU: {cpu.name} (R$ {cpu.price})")
        else:
            return render_template('index.html', error="Não encontramos processador para esse valor.")

        # --- 4. ESCOLHA DA RAM ---
        target_ram = orcamento * alloc_ram
        min_score_ram = 0
        if orcamento > 3000: min_score_ram = 2600
        if orcamento > 5000: min_score_ram = 3200
        
        ram = Component.query.filter(
            Component.type == 'ram',
            Component.price <= target_ram, # type: ignore
            Component.performance_score >= min_score_ram # type: ignore
        ).order_by(desc(Component.performance_score)).first()
        
        # Se não achou RAM top, pega qualquer uma que caiba no saldo
        if not ram:
            ram = Component.query.filter(
                Component.type == 'ram',
                Component.price <= saldo # type: ignore
            ).order_by(desc(Component.performance_score)).first()

        if ram:
            saldo -= ram.price
            logger.info(f"✅ RAM: {ram.name} (R$ {ram.price})")

        # --- 5. ESCOLHA DO SSD ---
        # SSD pega a sobra
        ssd = Component.query.filter(
            Component.type == 'ssd',
            Component.price <= saldo # type: ignore
        ).order_by(desc(Component.performance_score)).first()
        
        if not ssd:
             # Tenta o mais barato do banco se o saldo for muito curto
             ssd = Component.query.filter(Component.type == 'ssd').order_by(Component.price).first()
             # Se estourar muito o orçamento (> R$ 150 extra), ignora
             if ssd and ssd.price > (saldo + 150): 
                 ssd = None

        if ssd:
             logger.info(f"✅ SSD: {ssd.name} (R$ {ssd.price})")

        # --- CÁLCULO FINAL ---
        total = (cpu.price if cpu else 0) + \
                (gpu.price if gpu else 0) + \
                (ram.price if ram else 0) + \
                (ssd.price if ssd else 0)

        # --- GARGALO (Cálculo Simples) ---
        if cpu and gpu:
            try:
                c_score = cpu.performance_score if cpu.performance_score > 0 else 1
                g_score = gpu.performance_score if gpu.performance_score > 0 else 1
                ratio = g_score / c_score
                
                if ratio > 1.7:
                    bottleneck_warning = "⚠️ Placa de vídeo muito forte para o processador."
                elif ratio < 0.3:
                    bottleneck_warning = "⚠️ Processador muito forte para placa de vídeo básica."
            except: pass

        return render_template('result.html', 
                               cpu=cpu, gpu=gpu, ram=ram, ssd=ssd, 
                               total=total, orcamento=orcamento,
                               bottleneck=bottleneck_warning)

    except Exception as e:
        logger.error(f"Erro no app: {e}", exc_info=True)
        return render_template('index.html', error="Erro interno. Tente outro valor.")

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')