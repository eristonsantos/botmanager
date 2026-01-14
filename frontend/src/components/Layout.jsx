import React from 'react';
import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import { LayoutDashboard, Bot, ListTodo, ShieldCheck, LogOut, Rocket, CalendarClock, Package } from 'lucide-react';
import { useAuth } from '../auth'; // <--- IMPORTANTE: Importar o hook

export function Layout() {
    const navigate = useNavigate();
    const { logout } = useAuth(); // <--- IMPORTANTE: Pegar a função logout do contexto

    function handleLogout() {
        logout(); // Limpa token, estado global e header da API
        navigate('/login');
    }

    // Estilo do link ativo vs inativo (Atualizado com cores CognitX)
    const linkStyle = ({ isActive }) =>
        `flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 font-medium ${isActive
            ? 'bg-cognitx-main text-white shadow-lg shadow-blue-900/20'
            : 'text-slate-400 hover:bg-slate-800 hover:text-white'
        }`;

    return (
        <div className="min-h-screen bg-cognitx-dark flex">

            {/* --- SIDEBAR --- */}
            <aside className="w-64 bg-cognitx-panel border-r border-cognitx-border flex flex-col fixed h-full shadow-xl z-20">
                <div className="p-6 flex items-center gap-3 border-b border-cognitx-border">
                    <div className="bg-cognitx-main/10 p-2 rounded-xl border border-cognitx-main/20">
                        <Rocket size={24} className="text-cognitx-main" />
                    </div>
                    <span className="font-bold text-slate-100 text-lg tracking-tight">BotManager</span>
                </div>

                <nav className="flex-1 px-4 py-6 space-y-2 overflow-y-auto custom-scrollbar">
                    <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-4 px-2">
                        Operacional
                    </div>

                    <NavLink to="/dashboard" className={linkStyle}>
                        <LayoutDashboard size={20} />
                        <span>Visão Geral</span>
                    </NavLink>

                    <NavLink to="/agents" className={linkStyle}>
                        <Bot size={20} />
                        <span>Agentes (Robôs)</span>
                    </NavLink>

                    <NavLink to="/processes" className={linkStyle}>
                        <Package size={20} />
                        <span>Processos</span>
                    </NavLink>

                    <div className="pt-4 text-xs font-semibold text-slate-500 uppercase tracking-wider mb-4 px-2">
                        Execução
                    </div>

                    <NavLink to="/tasks" className={linkStyle}> {/* Era Workload, mudei para Tasks se for a lista */}
                        <ListTodo size={20} />
                        <span>Tarefas & Logs</span>
                    </NavLink>

                    <NavLink to="/workload" className={linkStyle}>
                        {/* Se Workload for "Criar Carga", mantenha. Se for igual a Tasks, ajuste */}
                        <ListTodo size={20} />
                        <span>Carga de Trabalho</span>
                    </NavLink>

                    <NavLink to="/schedules" className={linkStyle}>
                        <CalendarClock size={20} />
                        <span>Agendamentos</span>
                    </NavLink>

                    <div className="pt-4 text-xs font-semibold text-slate-500 uppercase tracking-wider mb-4 px-2">
                        Administração
                    </div>

                    <NavLink to="/governance" className={linkStyle}>
                        <ShieldCheck size={20} />
                        <span>Cofre & Assets</span>
                    </NavLink>
                </nav>

                <div className="p-4 border-t border-cognitx-border bg-cognitx-dark/30">
                    <button
                        onClick={handleLogout}
                        className="flex items-center gap-3 px-4 py-3 text-red-400 hover:bg-red-500/10 hover:text-red-300 rounded-xl w-full transition-all duration-200 group"
                    >
                        <LogOut size={20} className="group-hover:-translate-x-1 transition-transform" />
                        <span className="font-medium">Sair do Sistema</span>
                    </button>
                </div>
            </aside>

            {/* --- ÁREA DE CONTEÚDO --- */}
            <main className="flex-1 ml-64 p-8 overflow-y-auto">
                <div className="max-w-7xl mx-auto animate-fade-in">
                    <Outlet />
                </div>
            </main>
        </div>
    );
}