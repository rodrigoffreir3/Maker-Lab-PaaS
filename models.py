import logging
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Index

# Configuração de Logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("HardwareSniper.Models")

db = SQLAlchemy()

class Component(db.Model):
    """
    Representa uma peça de hardware.
    Agora com __init__ explícito para o VS Code não reclamar.
    """
    __tablename__ = 'components'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False, unique=True)
    type = db.Column(db.String(20), nullable=False)
    
    price = db.Column(db.Float, nullable=False, default=0.0)
    old_price = db.Column(db.Float, nullable=True)
    affiliate_link = db.Column(db.String(500), nullable=True)
    image_url = db.Column(db.String(500), nullable=True)
    last_updated = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())
    
    performance_score = db.Column(db.Integer, nullable=False, default=0)
    generation = db.Column(db.Integer, nullable=False, default=0)
    is_integrated_graphics = db.Column(db.Boolean, default=False)
    tdp = db.Column(db.Integer, nullable=False, default=65)

    __table_args__ = (
        Index('idx_component_type_price', 'type', 'price'),
        Index('idx_component_score', 'performance_score'),
    )

    # --- A CURA PARA OS ERROS VERMELHOS ---
    def __init__(self, name, type, price, performance_score, generation, is_integrated_graphics=False, affiliate_link=None, image_url=None, tdp=65):
        self.name = name
        self.type = type
        self.price = price
        self.performance_score = performance_score
        self.generation = generation
        self.is_integrated_graphics = is_integrated_graphics
        self.affiliate_link = affiliate_link
        self.image_url = image_url
        self.tdp = tdp

    def calculate_roi(self):
        try:
            if self.performance_score > 0 and self.price > 0:
                return round(self.price / self.performance_score, 4)
            return 9999.0
        except Exception as e:
            logger.error(f"Erro ao calcular ROI para {self.name}: {e}")
            return 9999.0

    def __repr__(self):
        return f"<Component {self.name} | R$ {self.price}>"


class Game(db.Model):
    __tablename__ = 'games'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False, unique=True)
    image_url = db.Column(db.String(500))
    
    min_cpu_score = db.Column(db.Integer, nullable=False)
    min_gpu_score = db.Column(db.Integer, nullable=False)
    min_ram_gb = db.Column(db.Integer, nullable=False, default=8)

    # Adicionando __init__ aqui também para garantir
    def __init__(self, title, min_cpu_score, min_gpu_score, min_ram_gb=8, image_url=None):
        self.title = title
        self.min_cpu_score = min_cpu_score
        self.min_gpu_score = min_gpu_score
        self.min_ram_gb = min_ram_gb
        self.image_url = image_url

    def can_run(self, cpu_score, gpu_score, ram_gb):
        try:
            return (
                cpu_score >= self.min_cpu_score and
                gpu_score >= self.min_gpu_score and
                ram_gb >= self.min_ram_gb
            )
        except Exception as e:
            logger.error(f"Erro ao verificar requisitos para {self.title}: {e}")
            return False

    def __repr__(self):
        return f"<Game {self.title}>"