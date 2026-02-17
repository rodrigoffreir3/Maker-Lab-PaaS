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
import { Cpu, Zap, Activity, Server, Play, Code2, Save, Terminal, Square, Trash2 } from 'lucide-react'; // 🔥 Importamos o Trash2
import Editor from '@monaco-editor/react';

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
  return (
    <div className="relative">
      <Handle type="target" position={Position.Top} className="w-2 h-2 bg-slate-500! border-none" />
      <div className="flex items-center gap-2 font-bold min-w-30 px-1">
        <NodeIcon iconName={data.icon} />
        <span className="truncate">{data.label}</span>
      </div>
      <Handle type="source" position={Position.Bottom} className="w-2 h-2 bg-emerald-500! border-none" />
    </div>
  );
};

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
    event.dataTransfer.setData('application/reactflow', JSON.stringify({ nodeType, label, icon }));
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
  
  const defaultCode = "# Maker Lab Studio\nimport RPi.GPIO as GPIO\nimport time\n\nwhile True:\n    print('Ligando LED...')\n    digitalWrite(13, GPIO.HIGH)\n    time.sleep(1)\n    \n    print('Desligando LED...')\n    digitalWrite(13, GPIO.LOW)\n    time.sleep(1)";
  const [code, setCode] = useState(defaultCode);
  
  const [logs, setLogs] = useState(["[SISTEMA]: Inicializando Ambiente Maker Lab..."]);
  const [isSimulating, setIsSimulating] = useState(false);

  const nodeTypes = useMemo(() => ({ default: MakerNode }), []);

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
                
                setNodes((nds) => nds.map((node) => {
                    if (node.data.label.toUpperCase().includes("LED")) {
                        return { 
                            ...node, 
                            style: { 
                                ...node.style, 
                                background: isHigh ? '#ef4444' : '#1e293b',
                                boxShadow: isHigh ? '0 0 20px rgba(239, 68, 68, 0.8)' : '0 4px 6px -1px rgba(0, 0, 0, 0.5)'
                            } 
                        };
                    }
                    return node;
                }));
                
                setLogs(prev => [...prev, `[SISTEMA_ELETRICO]: ${data.message}`]);
                return;
            }

            let prefix = "";
            if (data.status === "stdout") prefix = "[HW]: ";
            else if (data.status === "stderr") prefix = "[ERRO]: ";
            else if (data.status === "system") prefix = "[GO]: ";

            setLogs(prev => [...prev, `${prefix}${data.message}`]);
        } catch (e) {
            setLogs(prev => [...prev, `[ERRO DESCONHECIDO]: ${event.data}`]);
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
          setNodes(data.circuit_data.nodes);
          setEdges(data.circuit_data.edges || []);
        }
        if (data.code_content) setCode(data.code_content);
        setLogs(prev => [...prev, "[SISTEMA]: Projeto carregado com sucesso."]);
      })
      .catch(error => {
          setLogs(prev => [...prev, "[ERRO]: Falha ao carregar o projeto."]);
      });
  }, [setNodes, setEdges]);

  const onConnect = useCallback((params) => setEdges((eds) => addEdge({ ...params, animated: true, style: { stroke: '#10b981', strokeWidth: 2 } }, eds)), [setEdges]);

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
      
      let borderColor = '#334155';
      if (nodeType === 'board') borderColor = '#10b981';
      if (nodeType === 'actuator') borderColor = '#ef4444';
      if (nodeType === 'sensor') borderColor = '#f59e0b';
      
      const newNode = {
        id: `comp_${Date.now()}`,
        type: 'default',
        position,
        data: { label, icon }, 
        style: { 
            background: '#1e293b', 
            color: '#fff', 
            border: `1px solid ${borderColor}`, 
            borderRadius: '8px', 
            padding: '12px', 
            boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.5)',
            transition: 'all 0.1s ease-in-out'
        }
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

  // 🔥 NOVA FUNÇÃO: LIMPAR BANCADA 🔥
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

  return (
    <div className="flex flex-col h-screen bg-slate-950 font-sans select-none text-slate-200">
      <header className="h-16 border-b border-slate-800 bg-slate-900 flex justify-between items-center px-6 z-20 shrink-0 uppercase">
        <h1 className="text-xl font-black text-white flex items-center gap-2 tracking-tighter">
          MAKER<span className="text-emerald-500">LAB</span> 
          <span className="px-2 py-0.5 text-[10px] bg-emerald-500/10 text-emerald-500 border border-emerald-500/20 rounded font-bold tracking-widest uppercase">Studio</span>
        </h1>
        
        <div className="flex gap-4">
          {/* 🔥 BOTÃO LIMPAR 🔥 */}
          <button 
            onClick={handleClear} 
            disabled={isSimulating} 
            className="bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-300 border border-slate-700 px-5 py-2 rounded-lg font-bold text-sm transition-all flex items-center gap-2 uppercase"
          >
            <Trash2 size={16} /> Limpar
          </button>

          <button 
            onClick={handleSave} 
            disabled={isSimulating} 
            className="bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-300 border border-slate-700 px-5 py-2 rounded-lg font-bold text-sm transition-all flex items-center gap-2 uppercase"
          >
            <Save size={16} /> Salvar
          </button>
          
          {!isSimulating ? (
            <button 
                onClick={handleSimulate}
                className="bg-emerald-600 hover:bg-emerald-500 text-white px-5 py-2 rounded-lg font-bold text-sm transition-all shadow-[0_0_15px_rgba(16,185,129,0.2)] flex items-center gap-2 active:scale-95 uppercase"
            >
                <Play size={16} className="fill-current" /> Simular
            </button>
          ) : (
            <button 
                onClick={handleStop}
                className="bg-red-600 hover:bg-red-500 text-white px-5 py-2 rounded-lg font-bold text-sm transition-all shadow-[0_0_15px_rgba(239,68,68,0.3)] flex items-center gap-2 active:scale-95 uppercase animate-pulse"
            >
                <Square size={16} className="fill-current" /> Parar
            </button>
          )}
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        <Sidebar />
        
        <div className="flex-1 h-full relative" ref={reactFlowWrapper}>
          <ReactFlow nodes={nodes} edges={edges} onNodesChange={onNodesChange} onEdgesChange={onEdgesChange} onConnect={onConnect} onInit={setReactFlowInstance} onDrop={onDrop} onDragOver={(e) => { e.preventDefault(); e.dataTransfer.dropEffect = 'move'; }} nodeTypes={nodeTypes} fitView>
            <Background color="#334155" gap={24} size={1.5} />
            <Controls className="bg-slate-800 border-slate-700 fill-emerald-500" />
            <MiniMap nodeColor={(n) => n.style?.border?.split(' ')[2] || '#10b981'} maskColor="rgba(15, 23, 42, 0.8)" className="bg-slate-800 border border-slate-700 rounded-lg" />
          </ReactFlow>
        </div>

        <div className="w-112.5 border-l border-slate-800 flex flex-col shrink-0 z-10 shadow-2xl bg-slate-900">
          <div className="flex flex-col h-[70%] border-b border-slate-800">
             <div className="h-10 bg-slate-900 flex items-center px-4 gap-2 text-slate-300 text-xs font-bold tracking-widest uppercase shrink-0">
               <Code2 size={16} className="text-emerald-500" /> Sandbox Python
             </div>
             <div className="flex-1 pt-2 bg-[#1e1e1e]">
               <Editor height="100%" defaultLanguage="python" theme="vs-dark" value={code} onChange={setCode} options={{ minimap: { enabled: false }, fontSize: 14, fontFamily: "Fira Code, monospace" }} />
             </div>
          </div>

          <div className="flex flex-col h-[30%] bg-[#0d1117]">
             <div className="h-8 bg-slate-900 flex items-center justify-between px-4 text-slate-400 text-[10px] font-bold tracking-widest uppercase shrink-0 border-b border-slate-800">
                <div className="flex items-center gap-2"><Terminal size={12} className="text-slate-400" /> Console Output</div>
                {isSimulating && <span className="text-emerald-500 animate-pulse">Running...</span>}
             </div>
             <div className="flex-1 p-3 overflow-y-auto font-mono text-xs text-slate-300 space-y-1">
                {logs.map((logStr, index) => (
                  <div key={index} className="wrap-break-word">
                    <span className="text-slate-500 mr-2">{new Date().toLocaleTimeString('pt-BR', {hour12: false})}</span>
                    <span className={`whitespace-pre-wrap ${logStr.includes('ERRO') || logStr.includes('AVISO') || logStr.includes('Erro') || logStr.includes('PARADA') ? 'text-red-400' : logStr.includes('✅') || logStr.includes('GO') ? 'text-emerald-400' : logStr.includes('HW') || logStr.includes('ELETRICO') ? 'text-blue-300' : 'text-slate-300'}`}>
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