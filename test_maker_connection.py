import asyncio
import websockets
import json

async def test_lab():
    uri = "ws://localhost:8080/ws/lab?id=projeto_teste_01"
    async with websockets.connect(uri) as websocket:
        print("✅ Conectado ao Maker Lab!")
        
        # Simula o envio de um comando de ligar um LED
        comando = {
            "action": "digitalWrite",
            "pin": 13,
            "value": 1
        }
        
        await websocket.send(json.dumps(comando))
        print(f"📡 Comando enviado: {comando}")
        
        # Espera a resposta do Hub
        response = await websocket.recv()
        print(f"📥 Resposta do Hub: {response}")

asyncio.get_event_loop().run_until_complete(test_lab())