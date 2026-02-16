import os
from app import app, db
from models import Component, User, Project

def seed_lab():
    # Garante que a pasta 'instance' exista para não dar erro no SQLite
    os.makedirs('instance', exist_ok=True)
    
    with app.app_context():
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
            # Agora passando os parâmetros exatamente como o VS Code exigiu
            c = Component(name=data["name"], category=data["category"], spec_sheet=data["spec_sheet"])
            db.session.add(c)
        
        print("🧑‍💻 Criando Tony Stark e Projeto de Teste...")
        tony = User(username="tony_stark", password="password_segura")
        db.session.add(tony)
        db.session.commit() # Salva para gerar o ID do usuário

        projeto_teste = Project(
            name="Armadura Mark I",
            description="Primeiro teste de física no Maker Lab",
            user_id=tony.id,
            board_type="Raspberry Pi 4",
            circuit_data={"led_1": {"pin": 13}}, 
            code_content="print('Hello World')"
        )
        db.session.add(projeto_teste)
        
        try:
            db.session.commit()
            print("✅ Lab pronto!")
            print(f"🚀 O ID do projeto de teste é: {projeto_teste.id}")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Erro ao salvar: {e}")

if __name__ == "__main__":
    seed_lab()