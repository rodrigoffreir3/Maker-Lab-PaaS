import React, { useState, useRef, useCallback, useEffect, useMemo } from 'react';
import axios from 'axios';
import ReactFlow, {
  ReactFlowProvider,
  Background,
  Controls,
  MiniMap,
  addEdge,
  useNodesState,
  useEdgesState,
  Handle,
  Position,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { Cpu, Zap, Activity, Server, Play, Code2, Save, Terminal, Square, Trash2 } from 'lucide-react';
import Editor from '@monaco-editor/react';

// --- NOVO: RENDERIZADOR DE HARDWARE PREMIUM ---
const HardwareRenderer = ({ label, isHigh }) => {
  const name = label ? label.toUpperCase() : '';

  // 1. O Famoso Sensor HC-SR04 (Ultrassônico)
  if (name.includes('HC-SR04') || name.includes('ULTRASSÔNICO')) {
    return (
      <div className="w-24 h-12 bg-blue-600 rounded-sm border-2 border-blue-800 flex flex-col justify-center items-center relative shadow-lg">
        <div className="text-[6px] text-white font-mono absolute top-0.5">HC-SR04</div>
        <div className="flex w-full justify-around mt-2">
          <div className="w-8 h-8 rounded-full bg-gray-200 border-[3px] border-gray-400 flex items-center justify-center shadow-inner">
             <div className="w-3 h-3 rounded-full bg-gray-800 opacity-80 grid place-items-center"><div className="w-1 h-1 bg-gray-900 rounded-full"></div></div>
          </div>
          <div className="w-8 h-8 rounded-full bg-gray-200 border-[3px] border-gray-400 flex items-center justify-center shadow-inner">
             <div className="w-3 h-3 rounded-full bg-gray-800 opacity-80 grid place-items-center"><div className="w-1 h-1 bg-gray-900 rounded-full"></div></div>
          </div>
        </div>
        <div className="absolute -bottom-3 left-1/2 -translate-x-1/2 flex gap-1.5">
          <div className="w-1 h-3 bg-zinc-400 rounded-b-sm"></div>
          <div className="w-1 h-3 bg-zinc-400 rounded-b-sm"></div>
          <div className="w-1 h-3 bg-zinc-400 rounded-b-sm"></div>
          <div className="w-1 h-3 bg-zinc-400 rounded-b-sm"></div>
        </div>
      </div>
    );
  }

  // 2. Arduino Uno R3 (Tailwind Otimizado)
  if (name.includes('ARDUINO')) {
    return (
      <div className="w-32 h-24 bg-teal-700 rounded-lg border-2 border-teal-900 relative shadow-xl overflow-hidden p-2">
         <div className="w-6 h-8 bg-gray-300 border border-gray-400 absolute top-2 -left-0.5 rounded-r flex flex-col justify-around py-1"><div className="h-px w-full bg-gray-400"></div><div className="h-px w-full bg-gray-400"></div></div>
         <div className="w-6 h-6 bg-black absolute bottom-2 -left-0.5 rounded-r"></div>
         <div className="w-16 h-5 bg-gray-900 absolute right-4 bottom-4 rounded-sm border border-gray-700 flex justify-around px-1 items-center">
             <div className="w-px h-full bg-gray-600"></div><div className="w-px h-full bg-gray-600"></div><div className="w-px h-full bg-gray-600"></div><div className="w-px h-full bg-gray-600"></div><div className="w-px h-full bg-gray-600"></div><div className="w-px h-full bg-gray-600"></div>
         </div>
         <div className="h-2 w-16 bg-gray-900 absolute top-1 right-2 flex justify-around"><div className="w-0.5 h-full bg-gray-500"></div><div className="w-0.5 h-full bg-gray-500"></div><div className="w-0.5 h-full bg-gray-500"></div></div>
         <div className="text-white font-bold text-xs absolute top-8 left-8 rotate-90 tracking-widest opacity-80">UNO</div>
         <span className="text-[10px] text-white absolute bottom-1 right-1 opacity-50">MakerLab</span>
      </div>
    );
  }

  // 3. Servo Motor SG90
  if (name.includes('SERVO')) {
    return (
      <div className="w-16 h-20 relative flex flex-col items-center pt-4">
        <div className={`w-14 h-3 bg-white rounded-full border border-gray-300 absolute top-2 z-10 transition-transform duration-300 ease-in-out ${isHigh ? 'rotate-90' : 'rotate-0'}`}>
           <div className="w-2 h-2 bg-gray-400 rounded-full mx-auto mt-0.5"></div>
        </div>
        <div className="w-12 h-14 bg-blue-500 rounded-sm border border-blue-700 shadow-md relative">
           <div className="w-full h-4 bg-blue-600 mt-2 border-y border-blue-700"></div>
           <div className="text-[8px] text-white font-bold text-center mt-2">SG90</div>
        </div>
        <div className="w-4 h-8 border-l-2 border-orange-500 border-r-2 border-brown-700 absolute -bottom-4 right-2 opacity-80">
            <div className="w-0.5 h-full bg-red-500 mx-auto"></div>
        </div>
      </div>
    );
  }

  // 4. LED 
  if (name.includes('LED')) {
    return (
      <div className="flex flex-col items-center">
         <div className={`w-8 h-8 rounded-full border-b-2 border-red-900 transition-all duration-75 ${isHigh ? 'bg-red-500 shadow-[0_0_25px_rgba(239,68,68,1)]' : 'bg-red-800 shadow-none'}`}>
            <div className="w-3 h-3 bg-white opacity-40 rounded-full ml-1 mt-1"></div>
         </div>
         <div className="w-10 h-2 bg-red-900 rounded-b-md border-b-2 border-red-950"></div>
         <div className="flex gap-2 mt-0">
            <div className="w-1 h-6 bg-zinc-400 rounded-b"></div> 
            <div className="w-1 h-8 bg-zinc-400 rounded-b"></div> 
         </div>
      </div>
    );
  }

  // Fallback 
  return (
    <div className={`w-20 h-20 rounded shadow-lg border-2 flex items-center justify-center flex-col transition-colors ${isHigh ? 'bg-emerald-800 border-emerald-500' : 'bg-slate-800 border-slate-600'}`}>
        <Cpu size={32} className={isHigh ? 'text-emerald-300' : 'text-slate-400'} />
        <span className="text-[10px] text-center mt-2 font-bold px-1 text-slate-300">{label}</span>
    </div>
  );
};

const NodeIcon = ({ iconName }) => {
  const iconProps = { size: 16, className: "shrink-0" };
  switch (iconName) {
    case 'cpu': return <Cpu {...iconProps} className="text-emerald-400" />;
    case 'server': return <Server {...iconProps} className="text-blue-400" />;
    case 'zap': return <Zap {...iconProps} className="text-red-400" />;
    case 'activity': return <Activity {...iconProps} className="text-amber-400" />;
    default: return <Server {...iconProps} className="text-slate-400" />;
  }
};

const MakerNode = ({ data }) => {
  const isHigh = data.isHigh || false; 

  return (
    <div className="relative group cursor-pointer flex justify-center items-center">
      <Handle type="target" position={Position.Top} className="w-3 h-3 bg-slate-400 border-2 border-slate-700 hover:scale-150 transition-transform z-20 pointer-events-auto" />
      
      <HardwareRenderer label={data.label} isHigh={isHigh} />
      
      <div className="absolute -top-6 left-1/2 -translate-x-1/2 bg-slate-900 text-white text-[10px] px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none border border-slate-700 z-30">
        {data.label}
      </div>

      <Handle type="source" position={Position.Bottom} className="w-3 h-3 bg-emerald-500 border-2 border-emerald-900 hover:scale-150 transition-transform z-20 pointer-events-auto" />
    </div>
  );
};

// 🔥 CORREÇÃO 1: nodeTypes fora do componente (resolve o aviso amarelo) e usando tipo "maker"
const initialNodeTypes = { maker: MakerNode };

const Sidebar = () => {
  const [components, setComponents] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    axios.get('http://127.0.0.1:5000/components')
      .then(response => {
        setComponents(response.data);
        setLoading(false);
      })
      .catch(error => {
        console.error("Erro ao buscar catálogo:", error);
        setLoading(false);
      });
  }, []);

  const onDragStart = (event, nodeType, label, icon) => {
    // 🔥 CORREÇÃO 2: Envia o tipo 'maker' no arraste (para não usar o default e remover o fundo)
    event.dataTransfer.setData('application/reactflow', JSON.stringify({ nodeType: 'maker', label, icon }));
    event.dataTransfer.effectAllowed = 'move';
  };

  const getStyleByCategory = (category) => {
    const cat = category.toLowerCase();
    if (cat === 'board') return { Icon: Cpu, colorClass: 'text-emerald-400', borderClass: 'border-emerald-500/30 hover:border-emerald-500', typeStr: 'board', iconStr: 'cpu' };
    if (cat === 'actuator') return { Icon: Zap, colorClass: 'text-red-400', borderClass: 'border-red-500/30 hover:border-red-500', typeStr: 'actuator', iconStr: 'zap' };
    if (cat === 'sensor') return { Icon: Activity, colorClass: 'text-amber-400', borderClass: 'border-amber-500/30 hover:border-amber-500', typeStr: 'sensor', iconStr: 'activity' };
    return { Icon: Server, colorClass: 'text-blue-400', borderClass: 'border-blue-500/30 hover:border-blue-500', typeStr: 'default', iconStr: 'server' };
  };

  return (
    <aside className="w-64 bg-slate-900 border-r border-slate-800 p-4 flex flex-col gap-4 shadow-xl z-10 overflow-y-auto shrink-0 font-sans">
      <div className="mb-2">
        <h2 className="text-white font-black tracking-widest uppercase text-sm mb-1">Catálogo Real</h2>
        <p className="text-slate-500 text-[10px] uppercase font-bold italic">Sim-to-Real Engine</p>
      </div>
      {loading ? (
        <div className="text-slate-500 text-xs text-center mt-10 animate-pulse font-mono tracking-tighter uppercase">Buscando Hardware...</div>
      ) : (
        components.map((comp) => {
          const { Icon, colorClass, borderClass, typeStr, iconStr } = getStyleByCategory(comp.category);
          return (
            <div
              key={comp.id}
              className={`bg-slate-800 hover:bg-slate-700 border ${borderClass} p-3 rounded-lg cursor-grab active:cursor-grabbing transition-all flex flex-col gap-2 group`}
              onDragStart={(e) => onDragStart(e, typeStr, comp.name, iconStr)}
              draggable
            >
              <div className="flex items-center gap-3">
                <Icon className={`${colorClass} group-hover:scale-110 transition-transform`} size={20} />
                <span className="text-slate-200 text-sm font-bold">{comp.name}</span>
              </div>
              {comp.spec_sheet && (
                <div className="text-[9px] font-mono text-slate-500 bg-slate-950/50 px-2 py-1 rounded border border-white/5 uppercase">
                  {comp.spec_sheet.vcc ? `VCC: ${comp.spec_sheet.vcc}V` : ''} 
                  {comp.spec_sheet.logic ? ` | Logic: ${comp.spec_sheet.logic}V` : ''}
                </div>
              )}
            </div>
          );
        })
      )}
    </aside>
  );
};

const MakerStudio = () => {
  const reactFlowWrapper = useRef(null);
  const socketRef = useRef(null);
  const logEndRef = useRef(null);
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [reactFlowInstance, setReactFlowInstance] = useState(null);
  
  const defaultCode = `# Maker Lab Studio
import RPi.GPIO as GPIO
import time

PINO_LED = 13
PINO_BOTAO = 14

print("Aguardando Interação (Clique na peça na tela)...")
ultimo_estado = -1

while True:
    estado_botao = digitalRead(PINO_BOTAO)
    
    if estado_botao != ultimo_estado:
        if estado_botao == GPIO.HIGH:
            print("🟢 COMPONENTE ATIVADO!")
            digitalWrite(PINO_LED, GPIO.HIGH) # Acende LED
            digitalWrite(15, GPIO.HIGH)       # Roda Servo Motor (se houver)
        else:
            print("🔴 COMPONENTE DESATIVADO!")
            digitalWrite(PINO_LED, GPIO.LOW)  # Apaga LED
            digitalWrite(15, GPIO.LOW)        # Volta Servo Motor
            
        ultimo_estado = estado_botao
        
    time.sleep(0.1)`;
  
  const [code, setCode] = useState(defaultCode);
  const [logs, setLogs] = useState(["[SISTEMA]: Inicializando Ambiente Maker Lab..."]);
  const [isSimulating, setIsSimulating] = useState(false);

  const lastClickRef = useRef(0);
  const pin14StateRef = useRef(0); 

  // 🔥 CORREÇÃO 1: Usando a constante definida externamente
  const nodeTypes = useMemo(() => initialNodeTypes, []);

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  useEffect(() => {
    socketRef.current = new WebSocket('ws://localhost:8080/ws/lab');
    socketRef.current.onopen = () => setLogs(prev => [...prev, "[SISTEMA]: Conectado ao Orquestrador Go."]);
    
    socketRef.current.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            
            if (data.status === "finished") {
                setIsSimulating(false);
                return;
            }

            if (data.status === "gpio_update") {
                const isHigh = data.message.includes("-> 1");
                const isPin15 = data.message.includes("PIN 15"); 
                
                setNodes((nds) => nds.map((node) => {
                    const label = node.data.label ? node.data.label.toUpperCase() : '';
                    if (label.includes("LED") || (isPin15 && label.includes("SERVO"))) {
                        return { 
                            ...node, 
                            data: { ...node.data, isHigh: isHigh } 
                        };
                    }
                    return node;
                }));
                return; 
            }

            let prefix = "";
            if (data.status === "stdout") prefix = "[HW]: ";
            else if (data.status === "stderr") prefix = "[ERRO]: ";
            else if (data.status === "system") prefix = "[GO]: ";
            
            if (data.message && data.message.trim() !== "") {
                setLogs(prev => [...prev, `${prefix}${data.message}`]);
            }
        } catch (e) {
            console.error(e);
        }
    };
    
    socketRef.current.onclose = () => setLogs(prev => [...prev, "[SISTEMA]: Conexão com o Orquestrador encerrada."]);
    return () => { if(socketRef.current) socketRef.current.close(); };
  }, [setNodes]);

  useEffect(() => {
    axios.get('http://127.0.0.1:5000/project/1')
      .then(response => {
        const data = response.data;
        if (data.circuit_data?.nodes) {
          // 🔥 CORREÇÃO 3: Forçamos as peças salvas a virarem 'maker' e removemos o estilo antigo (caixa branca) 🔥
          const cleanedNodes = data.circuit_data.nodes.map(n => ({
            ...n,
            type: 'maker',
            style: {} 
          }));
          setNodes(cleanedNodes);
          setEdges(data.circuit_data.edges || []);
        }
        if (data.code_content) setCode(data.code_content);
        setLogs(prev => [...prev, "[SISTEMA]: Projeto carregado com sucesso."]);
      })
      .catch(error => { console.error(error); });
  }, [setNodes, setEdges]);

  const onConnect = useCallback((params) => setEdges((eds) => addEdge({ ...params, animated: true, style: { stroke: '#10b981', strokeWidth: 3 } }, eds)), [setEdges]);

  const onDrop = useCallback((event) => {
      event.preventDefault();
      const reactFlowBounds = reactFlowWrapper.current.getBoundingClientRect();
      const rawData = event.dataTransfer.getData('application/reactflow');
      if (!rawData) return;
      
      const { nodeType, label, icon } = JSON.parse(rawData);
      const position = reactFlowInstance.screenToFlowPosition({
        x: event.clientX - reactFlowBounds.left,
        y: event.clientY - reactFlowBounds.top,
      });
      
      const newNode = {
        id: `comp_${Date.now()}`,
        type: nodeType, // Será 'maker' agora
        position,
        data: { label, icon, isHigh: false },
        style: {} // 🔥 CORREÇÃO 4: Garante que as novas peças também não venham com a caixa branca 🔥
      };
      setNodes((nds) => nds.concat(newNode));
  }, [reactFlowInstance, setNodes]);

  const handleSave = async () => {
    try {
      await axios.post('http://127.0.0.1:5000/save', { project_id: 1, nodes, edges, code });
      setLogs(prev => [...prev, "[SISTEMA]: 💾 Projeto salvo no SQLite com sucesso!"]);
    } catch (error) {
      setLogs(prev => [...prev, "[ERRO]: Falha ao salvar o projeto."]);
    }
  };

  const handleClear = () => {
    if (window.confirm("Limpar a bancada? Isso removerá as peças não salvas da tela.")) {
        setNodes([]);
        setEdges([]);
        setCode(defaultCode);
        setLogs(["[SISTEMA]: Bancada limpa. Pronto para um novo circuito."]);
    }
  };

  const handleSimulate = async () => {
    if (nodes.length === 0) {
      setLogs(prev => [...prev, "[AVISO]: A bancada está vazia. Adicione componentes antes de simular."]);
      return;
    }

    pin14StateRef.current = 0; 

    setIsSimulating(true);
    setLogs(prev => [...prev, "-----------------------------------", "[SISTEMA]: Iniciando rotina de simulação..."]);
    try {
      const response = await axios.post('http://127.0.0.1:5000/simulate', {
        project_id: 1, 
        command: `Simulação de ${nodes.length} peças`
      });
      setLogs(prev => [...prev, `[CÉREBRO PYTHON]: ✅ Física Aprovada. Nível Lógico: ${response.data.logic_level}`]);
      if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
        socketRef.current.send(JSON.stringify({ project_id: 1, type: "simulation_start", payload: code }));
      } else {
        setLogs(prev => [...prev, "[ERRO]: WebSocket fechado."]);
        setIsSimulating(false);
      }
    } catch (error) {
      setLogs(prev => [...prev, `[ERRO]: Falha na simulação -> ${error.message}`]);
      setIsSimulating(false);
    }
  };

  const handleStop = () => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
        socketRef.current.send(JSON.stringify({ project_id: 1, type: "simulation_stop", payload: "" }));
    }
  };

  const onNodeClick = useCallback((event, node) => {
    if (!isSimulating) return;
    
    const now = Date.now();
    if (now - lastClickRef.current < 100) return;
    lastClickRef.current = now;

    pin14StateRef.current = pin14StateRef.current === 0 ? 1 : 0;

    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
        socketRef.current.send(JSON.stringify({ 
            project_id: 1, 
            type: "gpio_input", 
            payload: `PIN_14_${pin14StateRef.current}`
        }));
    }
  }, [isSimulating]);

  const onPaneClick = useCallback(() => {}, []);

  return (
    <div className="flex flex-col h-screen bg-slate-950 font-sans select-none text-slate-200">
      <header className="h-16 border-b border-slate-800 bg-slate-900 flex justify-between items-center px-6 z-20 shrink-0 uppercase">
        <h1 className="text-xl font-black text-white flex items-center gap-2 tracking-tighter">
          MAKER<span className="text-emerald-500">LAB</span> 
          <span className="px-2 py-0.5 text-[10px] bg-emerald-500/10 text-emerald-500 border border-emerald-500/20 rounded font-bold tracking-widest uppercase">Studio Premium</span>
        </h1>
        
        <div className="flex gap-4">
          <button onClick={handleClear} disabled={isSimulating} className="bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-300 border border-slate-700 px-5 py-2 rounded-lg font-bold text-sm transition-all flex items-center gap-2 uppercase">
            <Trash2 size={16} /> Limpar
          </button>
          <button onClick={handleSave} disabled={isSimulating} className="bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-300 border border-slate-700 px-5 py-2 rounded-lg font-bold text-sm transition-all flex items-center gap-2 uppercase">
            <Save size={16} /> Salvar
          </button>
          {!isSimulating ? (
            <button onClick={handleSimulate} className="bg-emerald-600 hover:bg-emerald-500 text-white px-5 py-2 rounded-lg font-bold text-sm transition-all shadow-[0_0_15px_rgba(16,185,129,0.2)] flex items-center gap-2 active:scale-95 uppercase">
                <Play size={16} className="fill-current" /> Simular
            </button>
          ) : (
            <button onClick={handleStop} className="bg-red-600 hover:bg-red-500 text-white px-5 py-2 rounded-lg font-bold text-sm transition-all shadow-[0_0_15px_rgba(239,68,68,0.3)] flex items-center gap-2 active:scale-95 uppercase animate-pulse">
                <Square size={16} className="fill-current" /> Parar
            </button>
          )}
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        <Sidebar />
        
        {/* 🔥 CORREÇÃO 2: Adicionado w-full h-full para não perder largura e resolver aviso do log 🔥 */}
        <div className="flex-1 w-full h-full relative" ref={reactFlowWrapper}>
          <ReactFlow 
            nodes={nodes} 
            edges={edges} 
            onNodesChange={onNodesChange} 
            onEdgesChange={onEdgesChange} 
            onConnect={onConnect} 
            onInit={setReactFlowInstance} 
            onDrop={onDrop} 
            onDragOver={(e) => { e.preventDefault(); e.dataTransfer.dropEffect = 'move'; }} 
            nodeTypes={nodeTypes} 
            onNodeClick={onNodeClick} 
            onPaneClick={onPaneClick} 
            fitView
          >
            <Background color="#475569" gap={20} size={2} variant="dots" className="bg-[#0f172a]" />
            <Controls className="bg-slate-800 border-slate-700 fill-emerald-500" />
            <MiniMap nodeColor="#10b981" maskColor="rgba(15, 23, 42, 0.8)" className="bg-slate-800 border border-slate-700 rounded-lg" />
          </ReactFlow>
        </div>

        <div className="w-112.5 border-l border-slate-800 flex flex-col shrink-0 z-10 shadow-2xl bg-slate-900">
          <div className="flex flex-col h-[60%] border-b border-slate-800">
             <div className="h-10 bg-slate-900 flex items-center px-4 gap-2 text-slate-300 text-xs font-bold tracking-widest uppercase shrink-0">
               <Code2 size={16} className="text-emerald-500" /> Sandbox Python
             </div>
             <div className="flex-1 pt-2 bg-[#1e1e1e]">
               <Editor height="100%" defaultLanguage="python" theme="vs-dark" value={code} onChange={setCode} options={{ minimap: { enabled: false }, fontSize: 14, fontFamily: "Fira Code, monospace" }} />
             </div>
          </div>
          <div className="flex flex-col h-[40%] bg-[#0d1117]">
             <div className="h-8 bg-slate-900 flex items-center justify-between px-4 text-slate-400 text-[10px] font-bold tracking-widest uppercase shrink-0 border-b border-slate-800">
                <div className="flex items-center gap-2"><Terminal size={12} className="text-slate-400" /> Console Output</div>
                {isSimulating && <span className="text-emerald-500 animate-pulse">Running...</span>}
             </div>
             <div className="flex-1 p-3 overflow-y-auto font-mono text-xs text-slate-300 space-y-1">
                {logs.map((logStr, index) => (
                  <div key={index} className="wrap-break-word">
                    <span className="text-slate-500 mr-2">{new Date().toLocaleTimeString('pt-BR', {hour12: false})}</span>
                    <span className={`whitespace-pre-wrap ${logStr.includes('ERRO') || logStr.includes('🔴') ? 'text-red-400' : logStr.includes('🟢') || logStr.includes('✅') ? 'text-emerald-400' : logStr.includes('HW') ? 'text-blue-300' : 'text-slate-300'}`}>
                        {logStr}
                    </span>
                  </div>
                ))}
                <div ref={logEndRef} />
             </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default function App() {
  return (
    <ReactFlowProvider>
      <MakerStudio />
    </ReactFlowProvider>
  );
}