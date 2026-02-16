import sys
import os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(BASE_DIR)

from flask import Flask, request, jsonify
from flask_cors import CORS
from models import db, Component, Project

app = Flask(__name__)
CORS(app)

DB_PATH = os.path.join(BASE_DIR, 'instance', 'hardware.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_PATH}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

@app.route('/components', methods=['GET'])
def get_components():
    try:
        components = db.session.query(Component).all()
        catalogo = [{"id": c.id, "name": c.name, "category": c.category, "spec_sheet": c.spec_sheet, "image_url": c.image_url} for c in components]
        return jsonify(catalogo)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# --- NOVA ROTA: CARREGAR O PROJETO SALVO ---
@app.route('/project/<int:project_id>', methods=['GET'])
def get_project(project_id):
    project = db.session.get(Project, project_id)
    if not project:
        return jsonify({"status": "error", "message": "Projeto não encontrado"}), 404

    return jsonify({
        "status": "success",
        "circuit_data": project.circuit_data or {"nodes": [], "edges": []},
        "code_content": project.code_content or ""
    })

# --- NOVA ROTA: GUARDAR O PROJETO NO BANCO DE DADOS ---
@app.route('/save', methods=['POST'])
def save_project():
    data = request.json
    project_id = data.get('project_id')
    
    project = db.session.get(Project, project_id)
    if not project:
        return jsonify({"status": "error", "message": "Projeto não encontrado"}), 404

    # Atualiza o JSON da bancada e o Texto do código
    project.circuit_data = {
        "nodes": data.get('nodes', []),
        "edges": data.get('edges', [])
    }
    project.code_content = data.get('code', '')
    
    try:
        db.session.commit()
        return jsonify({"status": "success", "message": "Projeto salvo com sucesso!"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/simulate', methods=['POST'])
def simulate():
    data = request.json
    project_id = data.get('project_id')
    command = data.get('command')

    try:
        project_id = int(project_id)
    except (TypeError, ValueError):
        return jsonify({"status": "error", "message": "ID do projeto inválido"}), 400

    project = db.session.get(Project, project_id)
    if not project:
        return jsonify({"status": "error", "message": "Projeto não encontrado"}), 404

    print(f"🤖 Simulando projeto [{project.name}]: {command}")
    
    return jsonify({
        "status": "success",
        "result": f"Comando '{command}' executado com sucesso.",
        "logic_level": project.board_type
    })

if __name__ == '__main__':
    app.run(port=5000)