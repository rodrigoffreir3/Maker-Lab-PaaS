from flask import Flask, request, jsonify
from models import db, Component, Project
import os

app = Flask(__name__)
# Certifique-se de que o caminho do banco está correto
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///instance/hardware.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

@app.route('/simulate', methods=['POST'])
def simulate():
    data = request.json
    project_id = data.get('project_id')
    command = data.get('command') # Ex: "digitalWrite 13 HIGH"

    # 1. Busca o projeto no banco
    project = Project.query.get(project_id)
    if not project:
        return jsonify({"status": "error", "message": "Projeto não encontrado"}), 404

    # 2. Lógica Simples de Validação (O MVP Open-Source)
    # Por enquanto, apenas confirmamos que o comando foi recebido
    print(f"🤖 Simulando projeto {project.name}: {command}")
    
    return jsonify({
        "status": "success",
        "result": f"Comando '{command}' executado no simulador.",
        "logic_level": project.board_type
    })

if __name__ == '__main__':
    app.run(port=5000)