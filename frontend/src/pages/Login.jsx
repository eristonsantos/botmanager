import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../auth'; // Ajuste o caminho se necessário
import { Lock, User, Activity, ShieldCheck, Zap } from 'lucide-react';

const Login = () => {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const navigate = useNavigate();
    const { login } = useAuth();

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setLoading(true);

        try {
            await login(username, password);
            navigate('/');
        } catch (err) {
            setError('Credenciais inválidas. Tente novamente.');
        } finally {
            setLoading(false);
        }
    };

    return (
        // MUDANÇA 1: Fundo da tela usando a cor da CognitX
        <div className="min-h-screen flex items-center justify-center bg-cognitx-dark p-4 relative overflow-hidden">

            {/* Efeitos de fundo (Glow) */}
            <div className="absolute top-0 left-0 w-full h-full overflow-hidden pointer-events-none">
                <div className="absolute top-[-10%] left-[-10%] w-96 h-96 bg-cognitx-main/10 rounded-full blur-3xl animate-pulse-slow"></div>
                <div className="absolute bottom-[-10%] right-[-10%] w-96 h-96 bg-cognitx-teal/10 rounded-full blur-3xl animate-pulse-slow delay-1000"></div>
            </div>

            {/* Card de Login */}
            {/* MUDANÇA 2: Cores do painel e bordas */}
            <div className="bg-cognitx-panel/80 backdrop-blur-xl p-8 rounded-2xl border border-cognitx-border shadow-2xl w-full max-w-md relative z-10">

                {/* Cabeçalho */}
                <div className="text-center mb-8">
                    <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-cognitx-dark border border-cognitx-border mb-4 shadow-lg group hover:border-cognitx-teal transition-colors duration-300">
                        {/* MUDANÇA 3: Ícone em Verde-Água (Teal) */}
                        <Activity className="w-8 h-8 text-cognitx-teal group-hover:scale-110 transition-transform duration-300" />
                    </div>
                    <h1 className="text-3xl font-bold text-white tracking-tight">
                        Bot<span className="text-cognitx-teal">Manager</span>
                    </h1>
                    <p className="text-slate-400 mt-2 text-sm">Orquestrador de Processos Inteligentes</p>
                </div>

                {error && (
                    <div className="mb-6 p-4 bg-red-500/10 border border-red-500/20 rounded-xl flex items-center gap-3 text-red-400 text-sm animate-shake">
                        <ShieldCheck className="w-5 h-5 shrink-0" />
                        {error}
                    </div>
                )}

                <form onSubmit={handleSubmit} className="space-y-6">
                    <div className="space-y-2">
                        <label className="text-sm font-medium text-slate-300 ml-1">Usuário</label>
                        <div className="relative group">
                            <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                                <User className="h-5 w-5 text-slate-500 group-focus-within:text-cognitx-main transition-colors" />
                            </div>
                            <input
                                type="text"
                                value={username}
                                onChange={(e) => setUsername(e.target.value)}
                                className="block w-full pl-11 pr-4 py-3 bg-cognitx-dark border border-cognitx-border rounded-xl text-slate-200 placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-cognitx-main/50 focus:border-cognitx-main transition-all duration-300"
                                placeholder="nome.sobrenome"
                                required
                            />
                        </div>
                    </div>

                    <div className="space-y-2">
                        <label className="text-sm font-medium text-slate-300 ml-1">Senha</label>
                        <div className="relative group">
                            <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                                <Lock className="h-5 w-5 text-slate-500 group-focus-within:text-cognitx-main transition-colors" />
                            </div>
                            <input
                                type="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                className="block w-full pl-11 pr-4 py-3 bg-cognitx-dark border border-cognitx-border rounded-xl text-slate-200 placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-cognitx-main/50 focus:border-cognitx-main transition-all duration-300"
                                placeholder="••••••••"
                                required
                            />
                        </div>
                    </div>

                    <div className="flex items-center justify-between text-sm">
                        <label className="flex items-center gap-2 cursor-pointer group">
                            <input type="checkbox" className="rounded border-cognitx-border bg-cognitx-dark text-cognitx-main focus:ring-offset-0 focus:ring-1 focus:ring-cognitx-main/50" />
                            <span className="text-slate-400 group-hover:text-slate-300 transition-colors">Lembrar-me</span>
                        </label>
                        <a href="#" className="text-cognitx-main hover:text-cognitx-teal font-medium transition-colors">
                            Esqueceu a senha?
                        </a>
                    </div>

                    <button
                        type="submit"
                        disabled={loading}
                        className="w-full bg-cognitx-main hover:bg-cognitx-hover text-white font-bold py-3 px-4 rounded-xl transition-all duration-300 transform hover:scale-[1.02] active:scale-[0.98] shadow-lg shadow-blue-900/20 flex items-center justify-center disabled:opacity-70 disabled:cursor-not-allowed group"
                    >
                        {loading ? (
                            <div className="w-6 h-6 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                        ) : (
                            <>
                                <span>Acessar Painel</span>
                                <Zap className="w-5 h-5 ml-2 group-hover:text-yellow-300 transition-colors" />
                            </>
                        )}
                    </button>
                </form>

                <div className="mt-8 text-center">
                    <p className="text-slate-500 text-xs">
                        © 2026 BotManager Automation Systems. <br />Todos os direitos reservados.
                    </p>
                </div>
            </div>
        </div>
    );
};

export default Login;