package hub

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"

	"github.com/gorilla/websocket"
)

var upgrader = websocket.Upgrader{
	ReadBufferSize:  1024,
	WriteBufferSize: 1024,
	CheckOrigin: func(r *http.Request) bool {
		return true // Permite que o Vite (porta 5173) se ligue sem erros de CORS
	},
}

type Client struct {
	Hub  *Hub
	Conn *websocket.Conn
	Send chan []byte
}

// Estrutura que mapeia exatamente o que o React envia
type MessageData struct {
	ProjectID int    `json:"project_id"`
	Type      string `json:"type"`
	Payload   string `json:"payload"`
}

func (c *Client) readPump() {
	defer func() {
		c.Hub.Unregister <- c
		c.Conn.Close()
	}()
	for {
		_, message, err := c.Conn.ReadMessage()
		if err != nil {
			break
		}

		var msgData MessageData
		if err := json.Unmarshal(message, &msgData); err == nil {
			// Se o React mandar o comando de Simular
			if msgData.Type == "simulation_start" {
				fmt.Printf("\n================================================\n")
				fmt.Printf("🎯 [ORQUESTRADOR GO] NOVA SIMULAÇÃO DISPARADA\n")
				fmt.Printf("================================================\n")
				fmt.Printf("ID do Projeto : %d\n", msgData.ProjectID)
				fmt.Printf("Ação          : %s\n\n", msgData.Type)
				fmt.Printf("[⚙️ CÓDIGO PYTHON RECEBIDO PARA EXECUÇÃO]\n")
				fmt.Printf("%s\n", msgData.Payload)
				fmt.Printf("================================================\n\n")

				// Opcional: O Go envia uma mensagem de volta para o React a confirmar
				resposta := `{"status": "executing", "message": "O Orquestrador Go está a preparar o hardware..."}`
				c.Send <- []byte(resposta)
			}
		} else {
			fmt.Printf("Mensagem bruta recebida: %s\n", string(message))
		}
	}
}

func (c *Client) writePump() {
	defer func() {
		c.Conn.Close()
	}()

	// 🔥 Código Refatorado: Loop limpo e idiomático sobre o canal 🔥
	for message := range c.Send {
		err := c.Conn.WriteMessage(websocket.TextMessage, message)
		if err != nil {
			return // Se der erro a escrever, aborta a goroutine
		}
	}

	// Se saiu do 'for range', significa que o c.Send foi fechado.
	// Avisamos o navegador que vamos fechar a conexão.
	c.Conn.WriteMessage(websocket.CloseMessage, []byte{})
}

func ServeWs(hub *Hub, w http.ResponseWriter, r *http.Request) {
	conn, err := upgrader.Upgrade(w, r, nil)
	if err != nil {
		log.Println("Erro no Upgrade WebSocket:", err)
		return
	}
	client := &Client{Hub: hub, Conn: conn, Send: make(chan []byte, 256)}
	client.Hub.Register <- client

	go client.writePump()
	go client.readPump()
}
