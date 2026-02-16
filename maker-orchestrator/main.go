package main

import (
	"log"
	"maker-orchestrator/hub" // Certifique-se de que o nome do módulo no go.mod é 'maker-orchestrator'
	"net/http"
)

func main() {
	log.Println("🚀 Maker Lab PaaS: Orquestrador Iniciado")

	// 1. Iniciando o Hub de Conexões (Tecnologia Imunno)
	h := hub.NewHub()
	go h.Run()

	// 2. Rota para os Simuladores (WebSockets)
	http.HandleFunc("/ws/lab", func(w http.ResponseWriter, r *http.Request) {
		hub.ServeWs(h, w, r)
	})

	// 3. Rota de Health Check
	http.HandleFunc("/status", func(w http.ResponseWriter, r *http.Request) {
		w.Write([]byte("Maker Lab Orchestrator is Running..."))
	})

	// 4. Porta de entrada
	port := ":8080"
	log.Printf("📡 Ouvindo comandos na porta %s", port)

	err := http.ListenAndServe(port, nil)
	if err != nil {
		log.Fatal("Erro ao iniciar servidor: ", err)
	}
}
