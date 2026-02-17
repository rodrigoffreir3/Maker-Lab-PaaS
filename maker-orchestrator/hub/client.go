package hub

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"os/exec"
	"strings"
	"sync" // <--- Importante para sincronizar as rotinas

	"github.com/gorilla/websocket"
)

var upgrader = websocket.Upgrader{
	ReadBufferSize:  1024,
	WriteBufferSize: 1024,
	CheckOrigin: func(r *http.Request) bool {
		return true
	},
}

type Client struct {
	Hub       *Hub
	Conn      *websocket.Conn
	Send      chan []byte
	ActiveCmd *exec.Cmd
}

type MessageData struct {
	ProjectID int    `json:"project_id"`
	Type      string `json:"type"`
	Payload   string `json:"payload"`
}

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

			sendMsg := func(status, msg string) {
				resp := HubResponse{Status: status, Message: msg}
				b, _ := json.Marshal(resp)
				c.Send <- b
			}

			if msgData.Type == "simulation_stop" {
				if c.ActiveCmd != nil && c.ActiveCmd.Process != nil {
					c.ActiveCmd.Process.Kill()
					fmt.Println("🛑 [SISTEMA]: Simulação abortada pelo usuário.")
					sendMsg("system", "⚠️ Simulação abortada pelo usuário.")
				}
				continue
			}

			if msgData.Type == "simulation_start" {
				fmt.Printf("\n🎯 [GO]: INICIANDO MATRIX DE HARDWARE...\n")

				// --- 1. A INJEÇÃO DA MATRIX ---
				matrixMock := `
class GPIO:
    BCM, BOARD = 10, 11
    OUT, IN = 1, 0
    HIGH, LOW = 1, 0
    @staticmethod
    def setmode(mode): pass
    @staticmethod
    def setup(pin, mode): pass
    @staticmethod
    def output(pin, state):
        print(f"[GPIO_ACTION]: PIN {pin} -> {state}")

import sys
from types import ModuleType
rpi = ModuleType("RPi")
rpi.GPIO = GPIO
sys.modules["RPi"] = rpi
sys.modules["RPi.GPIO"] = GPIO

def digitalWrite(pin, state):
    GPIO.output(pin, state)
`
				fullCode := matrixMock + "\n" + msgData.Payload

				tmpFile, err := os.CreateTemp("", "maker_script_*.py")
				if err != nil {
					sendMsg("error", "Erro ao criar ambiente.")
					continue
				}

				if _, err := tmpFile.Write([]byte(fullCode)); err != nil {
					sendMsg("error", "Erro ao gravar memória flash.")
					os.Remove(tmpFile.Name())
					continue
				}
				tmpFile.Close()

				cmd := exec.Command("python", "-u", tmpFile.Name())
				c.ActiveCmd = cmd

				stdout, _ := cmd.StdoutPipe()
				stderr, _ := cmd.StderrPipe()

				if err := cmd.Start(); err != nil {
					sendMsg("error", "Falha ao iniciar motor físico.")
					os.Remove(tmpFile.Name())
					continue
				}

				// --- 2. O ESCUTADOR DE EVENTOS (COM ESPELHO NO LUBUNTU) ---
				readPipe := func(pipe io.ReadCloser, isError bool) {
					scanner := bufio.NewScanner(pipe)
					for scanner.Scan() {
						line := scanner.Text()

						// ESPELHO: Imprime no seu terminal SSH para você ver a mágica
						fmt.Printf("[PYTHON-STREAM]: %s\n", line)

						if strings.HasPrefix(line, "[GPIO_ACTION]:") {
							sendMsg("gpio_update", line)
						} else {
							status := "stdout"
							if isError {
								status = "stderr"
							}
							sendMsg(status, line)
						}
					}
				}

				// 🔥 CORREÇÃO DE CONCORRÊNCIA (WAITGROUP) 🔥
				var wg sync.WaitGroup
				wg.Add(2)

				go func() {
					defer wg.Done()
					readPipe(stdout, false)
				}()
				go func() {
					defer wg.Done()
					readPipe(stderr, true)
				}()

				go func() {
					wg.Wait()  // Trava aqui até o Python cuspir a última letra
					cmd.Wait() // Agora sim fecha o processo com segurança
					os.Remove(tmpFile.Name())
					c.ActiveCmd = nil
					fmt.Println("✅ [GO]: Processo finalizado com sucesso.")
					sendMsg("finished", "EXECUÇÃO_CONCLUÍDA")
				}()
			}
		}
	}
}

func (c *Client) writePump() {
	defer c.Conn.Close()
	for message := range c.Send {
		c.Conn.WriteMessage(websocket.TextMessage, message)
	}
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
