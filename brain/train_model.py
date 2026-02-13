import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
import joblib
import os

def train_sniper_brain():
    dataset_path = 'brain/hardware_data.csv'
    
    if not os.path.exists(dataset_path):
        print("❌ Dataset não encontrado. Rode o simulator.py primeiro!")
        return

    # 1. Carregar Dados
    df = pd.read_csv(dataset_path)
    X = df.drop('label', axis=1) # Features: scores e ram
    y = df['label']              # Alvo: Persona

    # 2. Split (Treino e Teste)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # 3. Treinar a "Patricinha"
    print("🧠 Treinando a inteligência do Sniper...")
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)

    # 4. Salvar o modelo (Onde o App vai consultar depois)
    joblib.dump(model, 'brain/sniper_model.joblib')
    
    accuracy = model.score(X_test, y_test)
    print(f"🎯 Treinamento concluído! Precisão: {accuracy:.2%}")

if __name__ == "__main__":
    train_sniper_brain()