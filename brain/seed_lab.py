from simulation_gateway import db, app, Component

def seed_database():
    with app.app_context():
        db.create_all()

        # Limpa o banco antigo para não duplicar
        Component.query.delete()

        components = [
            Component(
                name="Arduino Uno R3",
                category="board",
                spec_sheet={"vcc": 5.0, "logic": 5.0, "chip": "ATmega328P", "pins": 14}
            ),
            Component(
                name="Raspberry Pi 4",
                category="board",
                spec_sheet={"vcc": 5.0, "logic": 3.3, "chip": "BCM2711", "pins": 40}
            ),
            Component(
                name="LED Vermelho",
                category="actuator",
                spec_sheet={"vcc": 2.0, "logic": 5.0, "color": "red", "pins": 2}
            ),
            Component(
                name="Sensor Ultrassônico HC-SR04",
                category="sensor",
                spec_sheet={"vcc": 5.0, "logic": 5.0, "type": "distance", "pins": 4}
            ),
            Component(
                name="Micro Servo SG90",
                category="actuator",
                spec_sheet={"vcc": 5.0, "logic": 5.0, "type": "pwm", "pins": 3}
            )
        ]

        db.session.add_all(components)
        db.session.commit()
        print("✅ Catálogo Premium de Hardware injetado no Banco de Dados!")

if __name__ == '__main__':
    seed_database()