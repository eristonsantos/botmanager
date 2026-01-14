import { useEffect, useState } from 'react';
import { Bot, Activity, CheckCircle2, Clock, AlertTriangle, PlayCircle, Layers } from 'lucide-react';
import api from '../services/api';
import { Link } from 'react-router-dom';

export function Dashboard() {
    const [stats, setStats] = useState({
        totalAgents: 0,
        onlineAgents: 0,
        pendingTasks: 0,
        completedTasks: 0
    });

    const [recentActivity, setRecentActivity] = useState([]);
    const [loading, setLoading] = useState(true);

    async function fetchDashboardData() {
        try {
            // Executamos requisições em paralelo
            const [agentsRes, workloadRes] = await Promise.all([
                api.get('/agents?size=100'),
                // Baixa as últimas 100 tarefas para calcular estatísticas rápidas
                // (Em produção, o ideal é ter uma rota /stats no backend para não baixar dados demais)
                api.get('/workload/items?limit=100')
            ]);

            // --- 1. ESTATÍSTICAS DE ROBÔS ---
            // A rota /agents retorna paginação: { items: [...], total: ... }
            const agentsList = agentsRes.data.items || [];
            const onlineCount = agentsList.filter(a => a.is_online).length;

            // --- 2. ESTATÍSTICAS DE TAREFAS ---
            // A rota /workload/items retorna LISTA DIRETA: [...]
            // Aqui estava o erro: não existe .items no workloadRes.data
            const allTasks = Array.isArray(workloadRes.data) ? workloadRes.data : [];

            // Conta status (backend usa 'pending' minúsculo)
            const pendingCount = allTasks.filter(t => t.status === 'pending' || t.status === 'queued').length;
            const completedCount = allTasks.filter(t => t.status === 'completed').length;

            setStats({
                totalAgents: agentsRes.data.total || agentsList.length,
                onlineAgents: onlineCount,
                pendingTasks: pendingCount,
                completedTasks: completedCount
            });

            // --- 3. ATIVIDADE RECENTE ---
            // Pegamos as 5 primeiras do array que já baixamos (o backend já ordena por data)
            setRecentActivity(allTasks.slice(0, 5));

        } catch (error) {
            console.error("Erro ao carregar dashboard:", error);
        } finally {
            setLoading(false);
        }
    }

    useEffect(() => {
        fetchDashboardData();
        const interval = setInterval(fetchDashboardData, 10000); // 10s polling
        return () => clearInterval(interval);
    }, []);

    // Helper para ícones de status
    const getStatusIcon = (status) => {
        const map = {
            pending: <Clock size={16} className="text-slate-400" />,
            processing: <PlayCircle size={16} className="text-blue-400 animate-pulse" />,
            running: <PlayCircle size={16} className="text-blue-400 animate-pulse" />,
            completed: <CheckCircle2 size={16} className="text-emerald-400" />,
            failed: <AlertTriangle size={16} className="text-red-400" />
        };
        return map[status] || <Layers size={16} className="text-slate-500" />;
    };

    return (
        <div>
            <div className="flex justify-between items-center mb-8">
                <h1 className="text-3xl font-bold text-white">Visão Geral</h1>
                <span className="text-xs text-slate-500 bg-slate-900 border border-slate-800 px-3 py-1 rounded-full flex items-center gap-2">
                    <span className="relative flex h-2 w-2">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                    </span>
                    Tempo Real
                </span>
            </div>

            {/* GRID DE CARDS (KPIs) */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
                <Card
                    title="Total de Robôs"
                    value={stats.totalAgents}
                    icon={Bot}
                    color="blue"
                    subtitle={`${stats.onlineAgents} Online agora`}
                />
                <Card
                    title="Fila Pendente"
                    value={stats.pendingTasks}
                    icon={Clock}
                    color="amber"
                    subtitle="Aguardando execução"
                />
                <Card
                    title="Tarefas Concluídas"
                    value={stats.completedTasks}
                    icon={CheckCircle2}
                    color="emerald"
                    subtitle="Últimos 100 itens"
                />
                <Card
                    title="Saúde da Frota"
                    value={stats.totalAgents > 0 ? `${Math.round((stats.onlineAgents / stats.totalAgents) * 100)}%` : "0%"}
                    icon={Activity}
                    color="violet"
                    subtitle="Disponibilidade"
                />
            </div>

            {/* ÚLTIMAS ATIVIDADES */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-lg">
                <div className="p-6 border-b border-slate-800 flex justify-between items-center">
                    <h3 className="font-bold text-white flex items-center gap-2">
                        <Activity className="text-blue-500" size={20} />
                        Últimas Atividades
                    </h3>
                    <Link to="/workload" className="text-sm text-blue-400 hover:text-blue-300 hover:underline">
                        Ver fila completa
                    </Link>
                </div>

                <div className="divide-y divide-slate-800">
                    {loading && recentActivity.length === 0 ? (
                        <div className="p-8 text-center text-slate-500">Carregando atividades...</div>
                    ) : recentActivity.length === 0 ? (
                        <div className="p-8 text-center text-slate-500">Nenhuma atividade recente encontrada.</div>
                    ) : (
                        recentActivity.map(item => (
                            <div key={item.id} className="p-4 flex items-center justify-between hover:bg-slate-800/50 transition-colors">
                                <div className="flex items-center gap-4">
                                    <div className={`p-2 rounded-lg bg-slate-950 border border-slate-800`}>
                                        {getStatusIcon(item.status)}
                                    </div>
                                    <div>
                                        <p className="text-white font-medium text-sm">{item.queue_name}</p>
                                        <div className="flex gap-2 text-xs text-slate-500 font-mono mt-0.5">
                                            <span>ID: {item.id.slice(0, 8)}...</span>
                                            {item.reference && (
                                                <span className="bg-slate-800 px-1 rounded text-slate-400">Ref: {item.reference}</span>
                                            )}
                                        </div>
                                    </div>
                                </div>

                                <div className="text-right">
                                    <span className={`text-xs px-2 py-1 rounded font-medium border capitalize ${item.status === 'completed' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
                                            item.status === 'failed' ? 'bg-red-500/10 text-red-400 border-red-500/20' :
                                                item.status === 'processing' || item.status === 'running' ? 'bg-blue-500/10 text-blue-400 border-blue-500/20' :
                                                    'bg-slate-800 text-slate-400 border-slate-700'
                                        }`}>
                                        {item.status}
                                    </span>
                                    <p className="text-xs text-slate-500 mt-1">
                                        {new Date(item.updated_at || item.created_at).toLocaleTimeString()}
                                    </p>
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </div>
        </div>
    );
}

// Componente Card (Mantido)
function Card({ title, value, icon: Icon, color, subtitle }) {
    const colors = {
        blue: "bg-blue-500/10 text-blue-500 border-blue-500/20",
        emerald: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
        amber: "bg-amber-500/10 text-amber-400 border-amber-500/20",
        violet: "bg-violet-500/10 text-violet-400 border-violet-500/20",
        red: "bg-red-500/10 text-red-400 border-red-500/20",
    };

    const baseColorClass = colors[color] || colors.blue;
    const borderColor = baseColorClass.split(' ').find(c => c.startsWith('border-'));

    return (
        <div className={`p-6 rounded-xl border bg-slate-900 shadow-lg relative overflow-hidden group hover:border-slate-600 transition-all ${borderColor}`}>
            <div className="flex justify-between items-start mb-4 relative z-10">
                <div>
                    <p className="text-slate-400 font-medium text-sm mb-1">{title}</p>
                    <h3 className="text-3xl font-bold text-white">{value}</h3>
                </div>
                <div className={`p-3 rounded-lg ${baseColorClass}`}>
                    <Icon size={24} />
                </div>
            </div>
            {subtitle && (
                <div className="text-xs text-slate-500 relative z-10">
                    {subtitle}
                </div>
            )}
            <div className={`absolute -bottom-4 -right-4 w-24 h-24 rounded-full opacity-5 blur-2xl ${baseColorClass.replace('bg-', 'bg-').split(' ')[1]}`}></div>
        </div>
    );
}