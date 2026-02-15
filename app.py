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
ADMIN_PASSWORD_HASH = "scrypt:32768:8:1$xh8JQsLoZHBp9NxB$5c19d9b9c3e648645b9dfa61233ae4435f8b80ce5ad71dbd432d5c7ad8ef0365298b2266cdb727d04c5b2e78738018d3f45c4832ea1541495d41ffcd389c8632"
ADMIN_TOTP_SECRET = "MIVUSKVOEVOSKRE5KYZJMPORB26B5YY5"

# --- MEMÓRIA ANTI-BRUTE FORCE ---
FAILED_LOGINS = {}

def create_app():
    app = Flask(__name__)
    
    basedir = os.path.abspath(os.path.dirname(__file__))
    db_path = os.path.join(basedir, 'instance', 'hardware.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    app.secret_key = os.environ.get('SECRET_KEY', os.urandom(32))
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['PERMANENT_SESSION_LIFETIME'] = 3600
    
    db.init_app(app)
    
    with app.app_context():
        db.create_all()
        
    return app

app = create_app()

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    ip = request.remote_addr
    current_time = time.time()

    if ip in FAILED_LOGINS:
        attempts, lockout_expiry = FAILED_LOGINS[ip]
        if current_time < lockout_expiry:
            remaining = int(lockout_expiry - current_time)
            return render_template('login.html', error=f"IP Bloqueado. Defesa ativa. Tente em {remaining}s.")
        elif current_time > lockout_expiry and attempts >= 5:
            FAILED_LOGINS.pop(ip)

    if request.method == 'POST':
        password_attempt = request.form.get('password')
        token_attempt = request.form.get('totp_token')
        totp = pyotp.TOTP(ADMIN_TOTP_SECRET)
        
        if password_attempt and check_password_hash(ADMIN_PASSWORD_HASH, password_attempt) and token_attempt and totp.verify(token_attempt):
            if ip in FAILED_LOGINS: FAILED_LOGINS.pop(ip)
            session.permanent = True
            session['admin_logged_in'] = True
            logger.info(f"✅ Acesso Admin Autorizado. IP: {ip}")
            return redirect(url_for('admin_panel'))
        else:
            attempts = FAILED_LOGINS.get(ip, (0, 0))[0] + 1
            lockout = current_time + 300 if attempts >= 5 else 0
            FAILED_LOGINS[ip] = (attempts, lockout)
            logger.error(f"❌ Falha de Autenticação. IP: {ip} | Tentativa {attempts}/5")
            return render_template('login.html', error="Credenciais ou Token 2FA inválidos.")
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('index'))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/recomendar', methods=['POST'])
def recomendar():
    try:
        orcamento_str = request.form.get('budget', '0')
        orcamento_clean = str(orcamento_str).replace('R$', '').replace('.', '').replace(',', '.')
        orcamento = float(orcamento_clean)

        if orcamento < 800:
             return render_template('index.html', error="Com R$ 800 não dá pra montar um PC. Junte pelo menos R$ 1.000.")

        # Uso de type: ignore para silenciar avisos de ambiguidade nas consultas
        cpu = Component.query.filter(Component.type == 'cpu', Component.price <= orcamento * 0.35).order_by(desc(Component.performance_score)).first() # type: ignore
        gpu = Component.query.filter(Component.type == 'gpu', Component.price <= orcamento * 0.45).order_by(desc(Component.performance_score)).first() # type: ignore
        ram = Component.query.filter(Component.type == 'ram', Component.price <= orcamento * 0.15).order_by(desc(Component.performance_score)).first() # type: ignore
        ssd = Component.query.filter(Component.type == 'ssd', Component.price <= orcamento * 0.15).order_by(desc(Component.performance_score)).first() # type: ignore

        setup_veredito = "Análise Indisponível"
        if cpu:
            setup_veredito = predict_persona(cpu.performance_score, gpu.performance_score if gpu else 0, 16, 1)

        total = (cpu.price if cpu else 0) + (gpu.price if gpu else 0) + (ram.price if ram else 0) + (ssd.price if ssd else 0)

        return render_template('result.html', cpu=cpu, gpu=gpu, ram=ram, ssd=ssd, total=total, orcamento=orcamento, ai_label=setup_veredito)

    except Exception as e:
        logger.error(f"Erro no app: {e}", exc_info=True)
        return render_template('index.html', error="Erro interno. Tente outro valor.")

@app.route('/admin')
@admin_required
def admin_panel():
    try:
        total = Component.query.count() # type: ignore
        
        # CORREÇÃO: Usando != None para evitar erro de atributo em consultas
        links = Component.query.filter(Component.affiliate_link != None).count() # type: ignore
        
        ofertas = Component.query.filter(Component.avg_price_historic > Component.price).order_by(desc(Component.avg_price_historic - Component.price)).limit(10).all() # type: ignore
        
        stats = dict(db.session.query(Component.type, func.count(Component.id)).group_by(Component.type).all()) # type: ignore
        
        return render_template('admin.html', total=total, links=links, ofertas=ofertas, stats=stats)
    except Exception as e:
        logger.error(f"Erro no Admin: {e}")
        return render_template('index.html', error="Erro ao carregar o Painel.")

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)