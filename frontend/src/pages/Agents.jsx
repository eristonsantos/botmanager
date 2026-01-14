import { useEffect, useState } from 'react';
import {
    Monitor, Activity, AlertCircle, Trash2, RefreshCw,
    Cpu, Network, Clock, UserPlus // <--- Adicionado UserPlus
} from 'lucide-react';
import api from '../services/api';

export function Agents() {
    const [agents, setAgents] = useState([]);
    const [loading, setLoading] = useState(true);

    // --- NOVOS ESTADOS PARA O MODAL ---
    const [showModal, setShowModal] = useState(false);
    const [robotForm, setRobotForm] = useState({ name: '', email: '', password: '' });

    // --- BUSCAR ROBÔS ---
    async function fetchAgents() {
        try {
            const response = await api.get('/agents');
            setAgents(response.data.items || []);
        } catch (error) {
            console.error("Erro ao buscar agentes:", error);
        } finally {
            setLoading(false);
        }
    }

    // Polling: Atualiza a cada 5 segundos
    useEffect(() => {
        fetchAgents();
        const interval = setInterval(fetchAgents, 5000);
        return () => clearInterval(interval);
    }, []);

    // --- EXCLUIR ROBÔ ---
    async function handleDelete(id, name) {
        if (!confirm(`Tem certeza que deseja remover o robô "${name}"?`)) return;

        try {
            await api.delete(`/agents/${id}`);
            setAgents(prev => prev.filter(agent => agent.id !== id));
        } catch (error) {
            alert("Erro ao excluir robô: " + (error.response?.data?.detail || error.message));
        }
    }

    // --- NOVO: CRIAR USUÁRIO ROBÔ ---
    async function handleCreateRobotUser(e) {
        e.preventDefault();
        try {
            await api.post('/auth/register-robot', robotForm);
            alert(`Sucesso! \n\nConfigure no arquivo .env do robô:\n\nROBOT_EMAIL=${robotForm.email}\nROBOT_PASSWORD=${robotForm.password}`);
            setShowModal(false);
            setRobotForm({ name: '', email: '', password: '' });
        } catch (error) {
            alert("Erro ao criar usuário: " + (error.response?.data?.detail || error.message));
        }
    }

    // --- HELPERS VISUAIS (Mantidos da sua versão bonita) ---
    const formatDate = (dateString) => {
        if (!dateString) return 'Nunca';
        return new Date(dateString).toLocaleTimeString('pt-BR');
    };

    const getStatusBadge = (agent) => {
        if (agent.is_online) {
            return (
                <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 shadow-sm shadow-emerald-900/20">
                    <span className="relative flex h-2 w-2">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                    </span>
                    ONLINE
                </span>
            );
        }
        return (
            <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium bg-slate-800 text-slate-500 border border-slate-700">
                <span className="w-2 h-2 rounded-full bg-slate-600" />
                OFFLINE
            </span>
        );
    };

    return (
        <div>
            <div className="flex justify-between items-center mb-8">
                <div>
                    <h1 className="text-3xl font-bold text-white mb-2">Meus Robôs</h1>
                    <p className="text-slate-400">Monitore a saúde e conectividade da sua força de trabalho digital.</p>
                </div>

                <div className="flex gap-3">
                    {/* BOTÃO NOVO ACESSO */}
                    <button
                        onClick={() => setShowModal(true)}
                        className="text-sm bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg transition-colors flex items-center gap-2 font-medium shadow-lg shadow-blue-900/20"
                    >
                        <UserPlus size={18} />
                        Novo Acesso
                    </button>

                    {/* BOTÃO ATUALIZAR */}
                    <button
                        onClick={() => { setLoading(true); fetchAgents(); }}
                        className="text-sm bg-slate-800 hover:bg-slate-700 text-slate-300 px-4 py-2 rounded-lg transition-colors flex items-center gap-2"
                    >
                        <RefreshCw size={16} className={loading ? "animate-spin" : ""} />
                        Atualizar
                    </button>
                </div>
            </div>

            {/* TABELA RICA (MANTIDA) */}
            {loading && agents.length === 0 ? (
                <div className="text-center py-20 text-slate-500">
                    <Activity className="animate-spin mx-auto mb-4 text-blue-500" size={40} />
                    <p>Buscando sinais dos robôs...</p>
                </div>
            ) : (
                <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-xl">
                    <table className="w-full text-left">
                        <thead className="bg-slate-950 text-slate-400 uppercase text-xs font-semibold">
                            <tr>
                                <th className="px-6 py-4 w-32">Status</th>
                                <th className="px-6 py-4">Nome / ID</th>
                                <th className="px-6 py-4">Ambiente</th>
                                <th className="px-6 py-4">Versão</th>
                                <th className="px-6 py-4">Último Sinal</th>
                                <th className="px-6 py-4 text-right">Ações</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800 text-slate-300">
                            {agents.length === 0 ? (
                                <tr>
                                    <td colSpan="6" className="px-6 py-16 text-center text-slate-500">
                                        <div className="flex flex-col items-center gap-4">
                                            <div className="p-4 bg-slate-800/50 rounded-full ring-1 ring-slate-700">
                                                <AlertCircle size={32} />
                                            </div>
                                            <div>
                                                <p className="text-lg font-medium text-white mb-1">Nenhum robô conectado</p>
                                                <p className="text-sm max-w-md mx-auto">
                                                    Para conectar um robô, crie um "Novo Acesso" e configure o script na máquina alvo.
                                                </p>
                                            </div>
                                        </div>
                                    </td>
                                </tr>
                            ) : (
                                agents.map((agent) => (
                                    <tr key={agent.id} className="hover:bg-slate-800/50 transition-colors group">

                                        <td className="px-6 py-4">
                                            {getStatusBadge(agent)}
                                        </td>

                                        <td className="px-6 py-4">
                                            <div className="flex items-center gap-3">
                                                <div className={`p-2.5 rounded-lg border ${agent.is_online ? 'bg-blue-500/10 border-blue-500/20 text-blue-400' : 'bg-slate-800 border-slate-700 text-slate-500'}`}>
                                                    <Monitor size={20} />
                                                </div>
                                                <div>
                                                    <div className="font-bold text-white text-base">{agent.name}</div>
                                                    <div className="text-xs text-slate-500 font-mono flex items-center gap-1" title="ID do Agente">
                                                        <span className="select-all">ID: {agent.id.slice(0, 8)}...</span>
                                                    </div>
                                                </div>
                                            </div>
                                        </td>

                                        <td className="px-6 py-4">
                                            <div className="flex flex-col gap-1">
                                                <div className="flex items-center gap-2 text-sm text-slate-300" title="Nome da Máquina">
                                                    <Cpu size={14} className="text-slate-500" />
                                                    {agent.machine_name}
                                                </div>
                                                <div className="flex items-center gap-2 text-xs text-slate-500 font-mono" title="Endereço IP">
                                                    <Network size={14} />
                                                    {agent.ip_address}
                                                </div>
                                            </div>
                                        </td>

                                        <td className="px-6 py-4">
                                            <span className="px-2 py-1 bg-slate-950 border border-slate-800 rounded text-xs font-mono text-slate-400">
                                                v{agent.version || '1.0.0'}
                                            </span>
                                        </td>

                                        <td className="px-6 py-4">
                                            <div className="flex items-center gap-2 text-sm text-slate-400" title={`Último sinal recebido às ${formatDate(agent.last_heartbeat)}`}>
                                                <Clock size={16} className={agent.is_online ? "text-emerald-500" : "text-slate-600"} />
                                                {formatDate(agent.last_heartbeat)}
                                            </div>
                                        </td>

                                        <td className="px-6 py-4 text-right">
                                            <button
                                                onClick={() => handleDelete(agent.id, agent.name)}
                                                className="p-2 text-slate-500 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-all opacity-0 group-hover:opacity-100"
                                                title="Remover Robô"
                                            >
                                                <Trash2 size={18} />
                                            </button>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            )}

            {/* --- MODAL PARA CRIAR USUÁRIO DO ROBÔ (ADICIONADO NO FINAL) --- */}
            {showModal && (
                <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4 backdrop-blur-sm">
                    <div className="bg-slate-900 border border-slate-800 rounded-xl w-full max-w-md p-6 shadow-2xl animate-in fade-in zoom-in duration-200">
                        <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
                            <UserPlus className="text-blue-500" /> Provisionar Robô
                        </h2>
                        <p className="text-slate-400 text-sm mb-6">
                            Crie um usuário para que o robô possa se autenticar na API.
                        </p>
                        <form onSubmit={handleCreateRobotUser} className="space-y-4">
                            <div>
                                <label className="text-sm text-slate-300 block mb-1">Nome do Robô</label>
                                <input className="w-full bg-slate-950 border border-slate-700 rounded p-2.5 text-white outline-none focus:border-blue-500" placeholder="Ex: Robô Financeiro 02" value={robotForm.name} onChange={e => setRobotForm({ ...robotForm, name: e.target.value })} required />
                            </div>
                            <div>
                                <label className="text-sm text-slate-300 block mb-1">Email de Acesso</label>
                                <input type="email" className="w-full bg-slate-950 border border-slate-700 rounded p-2.5 text-white outline-none focus:border-blue-500" placeholder="robo02@empresa.com" value={robotForm.email} onChange={e => setRobotForm({ ...robotForm, email: e.target.value })} required />
                            </div>
                            <div>
                                <label className="text-sm text-slate-300 block mb-1">Senha de Acesso</label>
                                <input className="w-full bg-slate-950 border border-slate-700 rounded p-2.5 text-white outline-none focus:border-blue-500" placeholder="••••••••" value={robotForm.password} onChange={e => setRobotForm({ ...robotForm, password: e.target.value })} required />
                            </div>

                            <div className="flex gap-3 pt-4">
                                <button type="button" onClick={() => setShowModal(false)} className="flex-1 py-2 border border-slate-700 text-slate-300 rounded hover:bg-slate-800">Cancelar</button>
                                <button type="submit" className="flex-1 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 font-medium">Criar Acesso</button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}