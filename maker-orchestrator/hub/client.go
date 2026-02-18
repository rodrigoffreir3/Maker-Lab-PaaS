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
	"sync"

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
	Hub         *Hub
	Conn        *websocket.Conn
	Send        chan []byte
	ActiveCmd   *exec.Cmd
	ActiveStdin io.WriteCloser // 🔥 NOVO: O tubo de entrada do Python
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

			// ==========================================
			// EVENTO: O USUÁRIO CLICOU EM UM COMPONENTE
			// ==========================================
			if msgData.Type == "gpio_input" {
				// Se a simulação estiver rodando e o tubo estiver aberto
				if c.ActiveStdin != nil {
					// Injeta o comando direto no processo Python!
					// Ex: "PIN_14_1\n"
					command := fmt.Sprintf("%s\n", msgData.Payload)
					c.ActiveStdin.Write([]byte(command))
				}
				continue
			}

			// ==========================================
			// EVENTO: PARAR SIMULAÇÃO
			// ==========================================
			if msgData.Type == "simulation_stop" {
				if c.ActiveCmd != nil && c.ActiveCmd.Process != nil {
					c.ActiveCmd.Process.Kill()
					fmt.Println("🛑 [SISTEMA]: Simulação abortada pelo usuário.")
					sendMsg("system", "⚠️ Simulação abortada pelo usuário.")
				}
				continue
			}

			// ==========================================
			// EVENTO: INICIAR SIMULAÇÃO
			// ==========================================
			if msgData.Type == "simulation_start" {
				fmt.Printf("\n🎯 [GO]: INICIANDO MATRIX DE HARDWARE (COM INPUTS)...\n")

				// --- 1. A INJEÇÃO DA MATRIX (AGORA COM THREAD DE ESCUTA) ---
				matrixMock := `
import sys
import threading
import time

class GPIO:
    BCM, BOARD = 10, 11
    OUT, IN = 1, 0
    HIGH, LOW = 1, 0
    
    # Dicionário secreto que guarda a voltagem real dos pinos
    _state = {} 

    @staticmethod
    def setmode(mode): pass
    
    @staticmethod
    def setup(pin, mode): pass
    
    @staticmethod
    def output(pin, state):
        print(f"[GPIO_ACTION]: PIN {pin} -> {state}")

    @staticmethod
    def input(pin):
        # O código do usuário vai ler este dicionário
        return GPIO._state.get(pin, GPIO.LOW)

# --- THREAD DE ESCUTA DA MATRIX ---
# Fica rodando em background lendo o que o Go escreve no terminal
def _listen_to_go():
    while True:
        try:
            line = sys.stdin.readline()
            if not line: break
            line = line.strip()
            # Formato esperado do Go: PIN_14_1 ou PIN_14_0
            if line.startswith("PIN_"):
                parts = line.split("_")
                pin = int(parts[1])
                state = int(parts[2])
                GPIO._state[pin] = state # Atualiza a física virtual!
        except:
            break

# Inicia a escuta invisível
t = threading.Thread(target=_listen_to_go, daemon=True)
t.start()

from types import ModuleType
rpi = ModuleType("RPi")
rpi.GPIO = GPIO
sys.modules["RPi"] = rpi
sys.modules["RPi.GPIO"] = GPIO

def digitalWrite(pin, state):
    GPIO.output(pin, state)
    
def digitalRead(pin):
    return GPIO.input(pin)
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

				// 🔥 A MÁGICA CONTRA O BUG DO WINDOWS 🔥
				// Forçamos o Python a cuspir texto em UTF-8, aceitando emojis e acentos nativamente
				cmd.Env = append(os.Environ(), "PYTHONIOENCODING=utf-8")

				c.ActiveCmd = cmd

				stdout, _ := cmd.StdoutPipe()
				stderr, _ := cmd.StderrPipe()

				// 🔥 NOVO: Abrimos a boca do Python para podermos falar com ele
				stdin, _ := cmd.StdinPipe()
				c.ActiveStdin = stdin

				if err := cmd.Start(); err != nil {
					sendMsg("error", "Falha ao iniciar motor físico.")
					os.Remove(tmpFile.Name())
					continue
				}

				readPipe := func(pipe io.ReadCloser, isError bool) {
					scanner := bufio.NewScanner(pipe)
					for scanner.Scan() {
						line := scanner.Text()
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
					wg.Wait()
					cmd.Wait()
					os.Remove(tmpFile.Name())
					c.ActiveCmd = nil
					c.ActiveStdin = nil // Limpa o tubo
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
