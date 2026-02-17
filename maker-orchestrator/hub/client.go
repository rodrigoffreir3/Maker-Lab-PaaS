package hub

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/exec"

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

type MessageData struct {
	ProjectID int    `json:"project_id"`
	Type      string `json:"type"`
	Payload   string `json:"payload"`
}

// Estrutura para devolver um JSON limpo para o React
type HubResponse struct {
	Status  string `json:"status"`
	Message string `json:"message"`
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

			if msgData.Type == "simulation_start" {
				fmt.Printf("\n🎯 [ORQUESTRADOR GO] EXECUTANDO CÓDIGO NO HARDWARE VIRTUAL...\n")

				// Função auxiliar para enviar mensagens de volta ao React
				sendMsg := func(status, msg string) {
					resp := HubResponse{Status: status, Message: msg}
					b, _ := json.Marshal(resp)
					c.Send <- b
				}

				sendMsg("executing", "O Orquestrador Go está a preparar o hardware...")

				// 1. Cria um arquivo Python temporário no servidor
				tmpFile, err := os.CreateTemp("", "maker_script_*.py")
				if err != nil {
					sendMsg("error", fmt.Sprintf("Erro ao criar ambiente: %v", err))
					continue
				}

				// 2. Grava o código que você digitou no navegador dentro do arquivo
				if _, err := tmpFile.Write([]byte(msgData.Payload)); err != nil {
					sendMsg("error", "Erro ao gravar na memória flash.")
					tmpFile.Close()
					os.Remove(tmpFile.Name())
					continue
				}
				tmpFile.Close() // Fecha para o interpretador poder ler

				// 3. Executa o comando "python <arquivo>" no Lubuntu
				cmd := exec.Command("python", tmpFile.Name())
				output, err := cmd.CombinedOutput() // Captura os prints e os erros

				// 4. Envia o resultado direto para a tela preta do seu React!
				if err != nil {
					sendMsg("error", fmt.Sprintf("Erro de Compilação/Execução:\n%s", string(output)))
				} else {
					sendMsg("success", fmt.Sprintf("Saída do Sistema:\n%s", string(output)))
				}

				// 5. Apaga o arquivo temporário (Limpeza)
				os.Remove(tmpFile.Name())
			}
		}
	}
}

func (c *Client) writePump() {
	defer func() {
		c.Conn.Close()
	}()
	for message := range c.Send {
		err := c.Conn.WriteMessage(websocket.TextMessage, message)
		if err != nil {
			return
		}
	}
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
