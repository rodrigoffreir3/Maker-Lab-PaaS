import sys
import os

# Força o Python a enxergar a raiz do projeto
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(BASE_DIR)

from flask import Flask, request, jsonify
from models import db, Component, Project

app = Flask(__name__)

# Força o caminho ABSOLUTO para o banco de dados (nunca mais vai falhar)
DB_PATH = os.path.join(BASE_DIR, 'instance', 'hardware.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_PATH}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

@app.route('/simulate', methods=['POST'])
def simulate():
    data = request.json
    project_id = data.get('project_id')
    command = data.get('command')

    # Como o ID vem da URL do Go, ele pode ser String. Precisamos converter para Inteiro.
    try:
        project_id = int(project_id)
    except (TypeError, ValueError):
        return jsonify({"status": "error", "message": "ID do projeto inválido"}), 400

    # Busca no banco (Sintaxe atualizada do SQLAlchemy 2.0)
    project = db.session.get(Project, project_id)
    
    if not project:
        return jsonify({"status": "error", "message": "Projeto não encontrado"}), 404

    # Aqui é onde a IA Física vai entrar no futuro. Por enquanto, a gente aprova:
    print(f"🤖 Simulando projeto [{project.name}]: {command}")
    
    return jsonify({
        "status": "success",
        "result": f"Comando '{command}' executado com sucesso.",
        "logic_level": project.board_type
    })

if __name__ == '__main__':
    app.run(port=5000)