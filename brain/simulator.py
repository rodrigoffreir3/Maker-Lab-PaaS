import pandas as pd
import random
import os

def generate_hardware_dataset(samples=22000):
    """
    Simulador que gera cenários de necessidades vs hardware ideal.
    DNA vindo do Imunno System, mas focado em ROI de Hardware.
    """
    data = []
    
    # Personas: 0=Gamer, 1=Office/Multi-abas, 2=Workstation/Editor
    for _ in range(samples):
        persona = random.randint(0, 2)
        
        if persona == 0: # GAMER
            # Precisa de GPU forte, CPU equilibrada, RAM padrão
            cpu_score = random.randint(8000, 30000)
            gpu_score = random.randint(12000, 40000)
            ram_gb = random.choice([8, 16, 32])
            ssd_type = 1 # NVMe
            label = 0 

        elif persona == 1: # OFFICE / 50 ABAS
            # Precisa de muita RAM e SSD rápido, GPU pode ser integrada
            cpu_score = random.randint(4000, 15000)
            gpu_score = random.randint(300, 3000) # GT 610 / Integrada
            ram_gb = random.choice([16, 32, 64])
            ssd_type = 1 # NVMe obrigatório para aguentar o swap
            label = 1

        elif persona == 2: # WORKSTATION / EDITOR
            # Precisa de muito núcleo (CPU) e muita VRAM/RAM
            cpu_score = random.randint(20000, 50000)
            gpu_score = random.randint(15000, 40000)
            ram_gb = random.choice([32, 64, 128])
            ssd_type = 1
            label = 2

        data.append([cpu_score, gpu_score, ram_gb, ssd_type, label])

    columns = ['cpu_score', 'gpu_score', 'ram_gb', 'ssd_nvme', 'label']
    df = pd.DataFrame(data, columns=columns)
    
    # Salva na pasta brain para o train_model.py ler
    df.to_csv('brain/hardware_data.csv', index=False)
    print(f"✅ Dataset com {samples} simulações gerado em brain/hardware_data.csv")

if __name__ == "__main__":
    generate_hardware_dataset()