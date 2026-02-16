from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    projects = db.relationship('Project', backref='author', lazy=True)

    # Construtor explícito para o VS Code parar de chorar
    def __init__(self, username, password):
        self.username = username
        self.password = password

class Project(db.Model):
    __tablename__ = 'projects'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    board_type = db.Column(db.String(50), default="Raspberry Pi 4")
    circuit_data = db.Column(db.JSON) 
    code_content = db.Column(db.Text)

    # Construtor explícito
    def __init__(self, name, description, user_id, board_type, circuit_data, code_content):
        self.name = name
        self.description = description
        self.user_id = user_id
        self.board_type = board_type
        self.circuit_data = circuit_data
        self.code_content = code_content

class Component(db.Model):
    """ Catálogo oficial de peças do seu Lab """
    __tablename__ = 'components'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    spec_sheet = db.Column(db.JSON) 
    image_url = db.Column(db.String(200))

    # Construtor explícito
    def __init__(self, name, category, spec_sheet, image_url=None):
        self.name = name
        self.category = category
        self.spec_sheet = spec_sheet
        self.image_url = image_url