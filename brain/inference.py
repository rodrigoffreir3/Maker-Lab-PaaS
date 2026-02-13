import joblib
import os

# Carrega o modelo treinado
MODEL_PATH = os.path.join(os.path.dirname(__file__), 'sniper_model.joblib')

def predict_persona(cpu_score, gpu_score, ram_gb, ssd_nvme, component_obj=None):
    """
    Diz para qual perfil o hardware é ideal e carimba o objeto se fornecido.
    """
    if not os.path.exists(MODEL_PATH):
        return "IA Offline"

    try:
        model = joblib.load(MODEL_PATH)
        prediction = model.predict([[cpu_score, gpu_score, ram_gb, ssd_nvme]])
        
        mapping = {0: 'Gamer', 1: 'Office/Multitask', 2: 'Workstation/Editor'}
        veredito = mapping.get(prediction[0], "Desconhecido")

        if component_obj:
            component_obj.ai_recommendation = veredito
            
        return veredito
    except Exception:
        return "Erro na Predição"