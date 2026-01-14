import { useEffect, useState } from 'react';
import {
    ListTodo,
    CheckCircle2,
    XCircle,
    Clock,
    Loader2,
    PlayCircle
} from 'lucide-react';
import api from '../services/api';

export function Tasks() {
    const [tasks, setTasks] = useState([]);
    const [loading, setLoading] = useState(true);

    async function fetchTasks() {
        try {
            // Busca os últimos 50 itens
            const response = await api.get('/workload/items?limit=50');
            setTasks(response.data);
        } catch (error) {
            console.error("Erro ao buscar tarefas:", error);
        } finally {
            setLoading(false);
        }
    }

    // Atualiza a cada 3 segundos para ver "Pending" virar "Completed" ao vivo
    useEffect(() => {
        fetchTasks();
        const interval = setInterval(fetchTasks, 3000);
        return () => clearInterval(interval);
    }, []);

    const formatDate = (dateString) => {
        if (!dateString) return '-';
        return new Date(dateString).toLocaleString('pt-BR');
    };

    // Badge Colorida de Status
    const StatusBadge = ({ status }) => {
        const styles = {
            pending: "bg-slate-700 text-slate-300 border-slate-600",
            in_progress: "bg-blue-500/10 text-blue-400 border-blue-500/20 animate-pulse",
            running: "bg-blue-500/10 text-blue-400 border-blue-500/20 animate-pulse", // <--- ADICIONE ESTA LINHA
            completed: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
            failed: "bg-red-500/10 text-red-400 border-red-500/20",
        };

        const icons = {
            pending: <Clock size={14} />,
            in_progress: <PlayCircle size={14} />,
            running: <PlayCircle size={14} />, // <--- E ADICIONE O ÍCONE AQUI TAMBÉM
            completed: <CheckCircle2 size={14} />,
            failed: <XCircle size={14} />,
        };

        return (
            <span className={`inline-flex items-center gap-2 px-2.5 py-1 rounded-full text-xs font-medium border ${styles[status] || styles.pending}`}>
                {icons[status] || <Clock size={14} />}
                <span className="uppercase">{status?.replace('_', ' ')}</span>
            </span>
        );
    };

    return (
        <div>
            <div className="flex justify-between items-center mb-8">
                <h1 className="text-3xl font-bold text-white">Fila de Tarefas</h1>
                <button onClick={fetchTasks} className="text-sm text-blue-400 hover:text-blue-300 hover:underline">
                    Atualizar agora
                </button>
            </div>

            {loading ? (
                <div className="text-slate-400 flex items-center gap-2">
                    <Loader2 className="animate-spin" size={20} /> Carregando fila...
                </div>
            ) : (
                <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-xl">
                    <table className="w-full text-left">
                        <thead className="bg-slate-950 text-slate-400 uppercase text-xs font-semibold">
                            <tr>
                                <th className="px-6 py-4">Status</th>
                                <th className="px-6 py-4">Fila / Processo</th>
                                <th className="px-6 py-4">ID da Tarefa</th>
                                <th className="px-6 py-4">Criação</th>
                                <th className="px-6 py-4">Conclusão</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800 text-slate-300">
                            {tasks.length === 0 ? (
                                <tr>
                                    <td colSpan="5" className="px-6 py-8 text-center text-slate-500">
                                        Nenhuma tarefa encontrada. Envie um POST para criar uma!
                                    </td>
                                </tr>
                            ) : (
                                tasks.map((task) => (
                                    <tr key={task.id} className="hover:bg-slate-800/50 transition-colors">
                                        <td className="px-6 py-4">
                                            <StatusBadge status={task.status} />
                                        </td>
                                        <td className="px-6 py-4 font-medium text-white">
                                            {task.queue_name}
                                        </td>
                                        <td className="px-6 py-4 font-mono text-xs text-slate-500">
                                            {task.id}
                                        </td>
                                        <td className="px-6 py-4 text-sm text-slate-400">
                                            {formatDate(task.created_at)}
                                        </td>
                                        <td className="px-6 py-4 text-sm text-slate-400">
                                            {formatDate(task.completed_at)}
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}