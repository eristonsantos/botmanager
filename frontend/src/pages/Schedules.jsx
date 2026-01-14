import { useEffect, useState } from 'react';
import {
    CalendarClock, Plus, Trash2, PlayCircle, PauseCircle,
    RefreshCw, Info, Bot
} from 'lucide-react';
import api from '../services/api';

export function Schedules() {
    const [schedules, setSchedules] = useState([]);
    const [processes, setProcesses] = useState([]); // Lista para o Dropdown
    const [loading, setLoading] = useState(true);
    const [showModal, setShowModal] = useState(false);

    const [formData, setFormData] = useState({
        name: '',
        cron_expression: '0 8 * * *',
        process_id: '', // Novo campo para o ID do processo
        is_active: true
    });

    // Busca Agendamentos e Processos em paralelo
    async function fetchData() {
        setLoading(true);
        try {
            const [schedRes, procRes] = await Promise.all([
                api.get('/governance/schedules'),
                api.get('/processes?size=100') // Traz os 100 primeiros para o dropdown
            ]);
            setSchedules(schedRes.data);
            setProcesses(procRes.data.items || []);
        } catch (error) {
            console.error("Erro ao buscar dados:", error);
        } finally {
            setLoading(false);
        }
    }

    useEffect(() => { fetchData(); }, []);

    async function handleCreate(e) {
        e.preventDefault();
        try {
            // Envia o process_id (ou null se estiver vazio)
            const payload = {
                ...formData,
                process_id: formData.process_id || null
            };

            await api.post('/governance/schedules', payload);

            setShowModal(false);
            setFormData({ name: '', cron_expression: '0 8 * * *', process_id: '', is_active: true });
            fetchData();
            alert("Agendamento criado!");
        } catch (error) {
            alert("Erro ao criar: " + (error.response?.data?.detail || error.message));
        }
    }

    async function handleDelete(id) {
        if (!confirm("Excluir agendamento?")) return;
        try {
            await api.delete(`/governance/schedules/${id}`);
            fetchData();
        } catch (error) {
            alert("Erro ao excluir.");
        }
    }

    async function toggleStatus(item) {
        try {
            await api.patch(`/governance/schedules/${item.id}`, {
                is_active: !item.is_active
            });
            fetchData();
        } catch (error) {
            alert("Erro ao atualizar status.");
        }
    }

    // Helper para achar o nome do processo pelo ID
    const getProcessName = (procId) => {
        if (!procId) return <span className="text-slate-600 italic">Sem processo (ID Nulo)</span>;

        // Procura na lista de processos carregada
        const proc = processes.find(p => p.id === procId);

        if (proc) {
            return (
                <span className="flex items-center gap-2 text-blue-400 font-medium">
                    <Bot size={16} /> {proc.name}
                </span>
            );
        }

        // Se não achou na lista (pode ser paginação ou ID antigo)
        return (
            <span className="text-slate-500 text-xs" title={procId}>
                ID: {procId.slice(0, 8)}... (Não encontrado)
            </span>
        );
    };

    return (
        <div>
            <div className="flex justify-between items-center mb-8">
                <div>
                    <h1 className="text-3xl font-bold text-white mb-2">Agendamentos (Triggers)</h1>
                    <p className="text-slate-400">Vincule processos a horários de execução.</p>
                </div>
                <button onClick={() => setShowModal(true)} className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg flex gap-2 items-center shadow-lg shadow-blue-900/20">
                    <Plus size={20} /> Novo Agendamento
                </button>
            </div>

            {loading ? <div className="text-center py-10 text-slate-500"><RefreshCw className="animate-spin inline mr-2" />Carregando...</div> : (
                <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-xl">
                    <table className="w-full text-left">
                        <thead className="bg-slate-950 text-slate-400 uppercase text-xs">
                            <tr>
                                <th className="px-6 py-4">Status</th>
                                <th className="px-6 py-4">Nome do Agendamento</th>
                                <th className="px-6 py-4">Processo Vinculado</th>
                                <th className="px-6 py-4">Cron (Frequência)</th>
                                <th className="px-6 py-4">Próxima Execução</th>
                                <th className="px-6 py-4 text-right">Ações</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800 text-slate-300">
                            {schedules.length === 0 ? <tr><td colSpan="6" className="text-center py-12 text-slate-500">Nenhum agendamento ativo.</td></tr> : schedules.map(item => (
                                <tr key={item.id} className="hover:bg-slate-800/50 transition-colors">
                                    <td className="px-6 py-4">
                                        <button onClick={() => toggleStatus(item)} title={item.is_active ? "Desativar" : "Ativar"}>
                                            {item.is_active
                                                ? <span className="flex items-center gap-2 text-emerald-400 font-medium"><PlayCircle size={18} /> Ativo</span>
                                                : <span className="flex items-center gap-2 text-slate-500"><PauseCircle size={18} /> Pausado</span>
                                            }
                                        </button>
                                    </td>
                                    <td className="px-6 py-4 font-medium text-white">{item.name}</td>

                                    {/* Coluna do Processo */}
                                    <td className="px-6 py-4 flex items-center gap-2">
                                        <Bot size={16} className="text-slate-500" />
                                        {getProcessName(item.process_id)}
                                    </td>

                                    <td className="px-6 py-4">
                                        <code className="bg-slate-950 border border-slate-700 px-2 py-1 rounded text-purple-300 font-mono text-xs">
                                            {item.cron_expression}
                                        </code>
                                    </td>
                                    <td className="px-6 py-4 text-sm text-slate-400">
                                        {item.next_run ? new Date(item.next_run).toLocaleString() : '---'}
                                    </td>
                                    <td className="px-6 py-4 text-right">
                                        <button onClick={() => handleDelete(item.id)} className="text-slate-500 hover:text-red-400 p-2 hover:bg-slate-800 rounded transition-colors"><Trash2 size={18} /></button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}

            {showModal && (
                <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4 backdrop-blur-sm">
                    <div className="bg-slate-900 border border-slate-800 rounded-xl w-full max-w-md p-6 shadow-2xl animate-in fade-in zoom-in duration-200">
                        <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
                            <CalendarClock className="text-blue-500" /> Novo Agendamento
                        </h2>
                        <form onSubmit={handleCreate} className="space-y-4">

                            {/* Seleção de Processo */}
                            <div>
                                <label className="text-sm text-slate-400 mb-1 block">Processo a Executar</label>
                                <select
                                    className="w-full bg-slate-950 border border-slate-700 rounded-lg p-3 text-white outline-none focus:border-blue-500"
                                    value={formData.process_id}
                                    onChange={e => setFormData({ ...formData, process_id: e.target.value })}
                                    required
                                >
                                    <option value="">Selecione um processo...</option>
                                    {processes.map(proc => (
                                        <option key={proc.id} value={proc.id}>{proc.name}</option>
                                    ))}
                                </select>
                            </div>

                            <div>
                                <label className="text-sm text-slate-400 mb-1 block">Nome do Agendamento</label>
                                <input
                                    className="w-full bg-slate-950 border border-slate-700 rounded-lg p-3 text-white outline-none focus:border-blue-500"
                                    placeholder="Ex: Rodar Notas Manhã"
                                    value={formData.name}
                                    onChange={e => setFormData({ ...formData, name: e.target.value })}
                                    required
                                />
                            </div>

                            <div>
                                <label className="text-sm text-slate-400 mb-1 block flex justify-between">
                                    Expressão CRON
                                    <a href="https://crontab.guru/" target="_blank" className="text-blue-400 text-xs hover:underline flex items-center gap-1"><Info size={12} /> Ajuda</a>
                                </label>
                                <input
                                    className="w-full bg-slate-950 border border-slate-700 rounded-lg p-3 text-white font-mono outline-none focus:border-blue-500"
                                    placeholder="Ex: 0 8 * * *"
                                    value={formData.cron_expression}
                                    onChange={e => setFormData({ ...formData, cron_expression: e.target.value })}
                                    required
                                />
                                <p className="text-xs text-slate-500 mt-2">
                                    Ex: <code className="text-slate-400">*/10 * * * *</code> (A cada 10 min)
                                </p>
                            </div>

                            <div className="flex gap-3 pt-4">
                                <button type="button" onClick={() => setShowModal(false)} className="flex-1 py-2 border border-slate-700 text-slate-300 rounded-lg hover:bg-slate-800 transition-colors">Cancelar</button>
                                <button type="submit" className="flex-1 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors shadow-lg shadow-blue-900/20">Salvar</button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}