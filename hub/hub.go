package hub

import (
	"log"
)

// Hub mantém o conjunto de clientes ativos e gerencia as mensagens.
type Hub struct {
	Clients    map[*Client]bool
	Broadcast  chan []byte
	Register   chan *Client
	Unregister chan *Client
}

// NewHub cria uma nova instância de Hub (Sem dependência de DB).
func NewHub() *Hub {
	return &Hub{
		Broadcast:  make(chan []byte),
		Register:   make(chan *Client),
		Unregister: make(chan *Client),
		Clients:    make(map[*Client]bool),
	}
}

// Run inicia o loop principal do hub.
func (h *Hub) Run() {
	for {
		select {
		case client := <-h.Register:
			h.Clients[client] = true
			log.Printf("🔌 Novo Maker conectado (ID: %s)", client.AgentID)
		case client := <-h.Unregister:
			if _, ok := h.Clients[client]; ok {
				delete(h.Clients, client)
				close(client.Send)
				log.Printf("🔌 Maker desconectado (ID: %s)", client.AgentID)
			}
		case message := <-h.Broadcast:
			for client := range h.Clients {
				select {
				case client.Send <- message:
				default:
					close(client.Send)
					delete(h.Clients, client)
				}
			}
		}
	}
}

// SendCommandToAgent encontra um cliente específico pelo ID e envia uma mensagem.
func (h *Hub) SendCommandToAgent(agentID string, message []byte) {
	for client := range h.Clients {
		if client.AgentID == agentID {
			select {
			case client.Send <- message:
				log.Printf("📡 Comando enviado para o projeto %s.", agentID)
			default:
				log.Printf("⚠️ Erro: Buffer cheio para o projeto %s.", agentID)
			}
			return
		}
	}
	log.Printf("⚠️ Projeto %s não encontrado no Lab.", agentID)
}
