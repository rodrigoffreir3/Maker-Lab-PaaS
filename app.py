import logging
import os
import time
import pyotp
from functools import wraps
from flask import Flask, render_template, request, session, redirect, url_for
from werkzeug.security import check_password_hash
from models import db, Component
from sqlalchemy import desc, func
from brain.inference import predict_persona

# --- CONFIGURAÇÃO DE LOGS ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("HardwareSniper.App")

# --- CREDENCIAIS DE SEGURANÇA MÁXIMA ---
# 1. Seu hash de senha gerado anteriormente
ADMIN_PASSWORD_HASH = "scrypt:32768:8:1$xh8JQsLoZHBp9NxB$5c19d9b9c3e648645b9dfa61233ae4435f8b80ce5ad71dbd432d5c7ad8ef0365298b2266cdb727d04c5b2e78738018d3f45c4832ea1541495d41ffcd389c8632" 
# 2. O Secret do Google Authenticator gerado no Passo 1
ADMIN_TOTP_SECRET = "MIVUSKVOEVOSKRE5KYZJMPORB26B5YY5" 

# --- MEMÓRIA ANTI-BRUTE FORCE ---
# Dicionário que guarda: {'IP': (tentativas, tempo_de_bloqueio_timestamp)}
FAILED_LOGINS = {} 

def create_app():
    app = Flask(__name__)
    
    basedir = os.path.abspath(os.path.dirname(__file__))
    db_path = os.path.join(basedir, 'instance', 'hardware.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Configurações de Segurança de Sessão
    app.secret_key = os.environ.get('SECRET_KEY', os.urandom(32))
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['PERMANENT_SESSION_LIFETIME'] = 3600
    
    db.init_app(app)
    
    with app.app_context():
        db.create_all()
        
    return app

app = create_app()

# --- DECORATOR DE SEGURANÇA ---
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- ROTAS DE AUTENTICAÇÃO (BLINDADAS) ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    ip = request.remote_addr
    current_time = time.time()

    # 1. VERIFICAÇÃO ANTI-BRUTE FORCE
    if ip in FAILED_LOGINS:
        attempts, lockout_expiry = FAILED_LOGINS[ip]
        if current_time < lockout_expiry:
            remaining = int(lockout_expiry - current_time)
            return render_template('login.html', error=f"IP Bloqueado. Defesa ativa. Tente em {remaining}s.")
        elif current_time > lockout_expiry and attempts >= 5:
            # Reseta o contador se o tempo de punição já passou
            FAILED_LOGINS.pop(ip)

    if request.method == 'POST':
        password_attempt = request.form.get('password')
        token_attempt = request.form.get('totp_token')

        # 2. VALIDAÇÃO DUPLA (SENHA + GOOGLE AUTHENTICATOR)
        totp = pyotp.TOTP(ADMIN_TOTP_SECRET)
        
        is_pass_valid = password_attempt and check_password_hash(ADMIN_PASSWORD_HASH, password_attempt)
        is_token_valid = token_attempt and totp.verify(token_attempt)

        if is_pass_valid and is_token_valid:
            if ip in FAILED_LOGINS:
                FAILED_LOGINS.pop(ip) # Limpa o histórico do IP logado com sucesso
                
            session.permanent = True
            session['admin_logged_in'] = True
            logger.info(f"✅ Acesso Administrativo Autorizado. IP: {ip}")
            return redirect(url_for('admin_panel'))
        else:
            # Punição por falha
            attempts = FAILED_LOGINS.get(ip, (0, 0))[0] + 1
            lockout = 0
            if attempts >= 5:
                lockout = current_time + 300 # Bloqueia por 5 minutos (300 segundos)
                logger.warning(f"🚨 ATAQUE DETECTADO! IP {ip} bloqueado no firewall da aplicação.")
            
            FAILED_LOGINS[ip] = (attempts, lockout)
            logger.error(f"❌ Falha de Autenticação. IP: {ip} | Tentativa {attempts}/5")
            
            return render_template('login.html', error="Credenciais ou Token 2FA inválidos.")
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('index'))

# --- ROTAS ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/recomendar', methods=['POST'])
def recomendar():
    try:
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
        alloc_gpu = 0.40  
        alloc_cpu = 0.25  
        alloc_ram = 0.15  
        
        saldo = orcamento
        bottleneck_warning = None

        # --- 2. ESCOLHA DA GPU ---
        target_gpu = orcamento * alloc_gpu
        
        gpu = Component.query.filter( # type: ignore
            Component.type == 'gpu', # type: ignore
            Component.price <= target_gpu # type: ignore
        ).order_by(desc(Component.performance_score)).first() # type: ignore

        if not gpu and orcamento > 2000:
            gpu = Component.query.filter( # type: ignore
                Component.type == 'gpu', # type: ignore
                Component.price <= (orcamento * 0.60) # type: ignore
            ).order_by(desc(Component.performance_score)).first() # type: ignore

        if gpu:
            saldo -= gpu.price
            logger.info(f"✅ GPU: {gpu.name} (R$ {gpu.price})")
        else:
            logger.info("⚠️ Sem GPU dedicada. Focando em Vídeo Integrado.")
            alloc_cpu += 0.35 

        # --- 3. ESCOLHA DA CPU ---
        target_cpu = orcamento * alloc_cpu
        
        query_cpu = Component.query.filter( # type: ignore
            Component.type == 'cpu', # type: ignore
            Component.price <= target_cpu # type: ignore
        )
        
        if not gpu:
            query_cpu = query_cpu.filter(Component.is_integrated_graphics == True) # type: ignore
        
        cpu = query_cpu.order_by(desc(Component.performance_score)).first() # type: ignore

        if not cpu:
            fallback_query = Component.query.filter(Component.type == 'cpu') # type: ignore
            if not gpu:
                fallback_query = fallback_query.filter(Component.is_integrated_graphics == True) # type: ignore
            cpu = fallback_query.order_by(Component.price).first() # type: ignore

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
        
        ram = Component.query.filter( # type: ignore
            Component.type == 'ram', # type: ignore
            Component.price <= target_ram, # type: ignore
            Component.performance_score >= min_score_ram # type: ignore
        ).order_by(desc(Component.performance_score)).first() # type: ignore
        
        if not ram:
            ram = Component.query.filter( # type: ignore
                Component.type == 'ram', # type: ignore
                Component.price <= saldo # type: ignore
            ).order_by(desc(Component.performance_score)).first() # type: ignore

        if ram:
            saldo -= ram.price
            logger.info(f"✅ RAM: {ram.name} (R$ {ram.price})")

        # --- 5. ESCOLHA DO SSD ---
        ssd = Component.query.filter( # type: ignore
            Component.type == 'ssd', # type: ignore
            Component.price <= saldo # type: ignore
        ).order_by(desc(Component.performance_score)).first() # type: ignore
        
        if not ssd:
             ssd = Component.query.filter(Component.type == 'ssd').order_by(Component.price).first() # type: ignore
             if ssd and ssd.price > (saldo + 150): 
                 ssd = None

        if ssd:
             logger.info(f"✅ SSD: {ssd.name} (R$ {ssd.price})")

        # --- 6. O VEREDITO DA PATRICINHA ---
        setup_veredito = "Análise Indisponível"
        if cpu:
            c_score = cpu.performance_score
            g_score = gpu.performance_score if gpu else 0
            r_gb = 16 if (ram and ram.performance_score > 2600) else 8
            s_nvme = 1 if (ssd and 'nvme' in ssd.name.lower()) else 0
            
            setup_veredito = predict_persona(c_score, g_score, r_gb, s_nvme)

            predict_persona(c_score, 0, 0, 0, component_obj=cpu)
            if gpu: predict_persona(0, g_score, 0, 0, component_obj=gpu)
            
            db.session.commit()

        # --- CÁLCULO FINAL ---
        total = (cpu.price if cpu else 0) + \
                (gpu.price if gpu else 0) + \
                (ram.price if ram else 0) + \
                (ssd.price if ssd else 0)

        # --- GARGALO ---
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
                               bottleneck=bottleneck_warning,
                               ai_label=setup_veredito)

    except Exception as e:
        logger.error(f"Erro no app: {e}", exc_info=True)
        return render_template('index.html', error="Erro interno. Tente outro valor.")

# --- ROTA ADMINISTRATIVA ---
@app.route('/admin')
@admin_required
def admin_panel():
    try:
        total_items = Component.query.count() # type: ignore
        
        links_capturados = Component.query.filter( # type: ignore
            Component.affiliate_link.notlike('%fake-link%') # type: ignore
        ).count()
        
        melhores_ofertas = Component.query.filter( # type: ignore
            Component.avg_price_historic > Component.price # type: ignore
        ).order_by(desc(Component.avg_price_historic - Component.price)).limit(10).all() # type: ignore

        stats_tipo = db.session.query(
            Component.type, func.count(Component.id) # type: ignore
        ).group_by(Component.type).all() # type: ignore
        
        return render_template('admin.html', 
                               total=total_items, 
                               links=links_capturados, 
                               ofertas=melhores_ofertas,
                               stats=dict(stats_tipo))
    except Exception as e:
        logger.error(f"Erro no Painel Admin: {e}")
        return render_template('index.html', error="Erro ao carregar o Painel Admin.")

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)