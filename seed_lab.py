import os
from app import app, db
from models import Component, User, Project

def seed_lab():
    with app.app_context():
        # Caminho do banco (ajuste se o nome for diferente no seu app.py)
        db_path = 'instance/hardware_sniper.db' # ou o nome que estiver no seu SQLALCHEMY_DATABASE_URI
        
        print("🧨 Resetando banco de dados físico...")
        db.drop_all()
        db.create_all()

        components_data = [
            {"name": "Raspberry Pi 4", "category": "Board", "spec_sheet": {"vcc": 5.0, "logic": 3.3}},
            {"name": "Arduino Uno R3", "category": "Board", "spec_sheet": {"vcc": 5.0, "logic": 5.0}},
            {"name": "LED Vermelho", "category": "Actuator", "spec_sheet": {"v_forward": 2.0}},
            {"name": "Sensor HC-SR04", "category": "Sensor", "spec_sheet": {"vcc": 5.0}}
        ]

        print(f"🌱 Populando Lab com {len(components_data)} componentes...")
        for data in components_data:
            # Forçando a criação sem o construtor automático se ele falhar
            c = Component()
            c.name = data["name"]
            c.category = data["category"]
            c.spec_sheet = data["spec_sheet"]
            db.session.add(c)
        
        try:
            db.session.commit()
            print("✅ Lab pronto e banco populado!")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Erro ao salvar: {e}")

if __name__ == "__main__":
    seed_lab()