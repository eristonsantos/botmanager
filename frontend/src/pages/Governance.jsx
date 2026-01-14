import { useEffect, useState } from 'react';
import {
    Shield, Key, FileText, Plus, Copy, RefreshCw, Database,
    Trash2, X, Check, Lock
} from 'lucide-react';
import api from '../services/api';

export function Governance() {
    const [activeTab, setActiveTab] = useState('assets');
    const [data, setData] = useState([]);
    const [loading, setLoading] = useState(true);

    // Estados do Modal e Formulário
    const [showModal, setShowModal] = useState(false);
    const [formData, setFormData] = useState({ name: '', value: '', description: '' });
    const [submitting, setSubmitting] = useState(false);

    // --- BUSCA DE DADOS (READ) ---
    async function fetchData() {
        setLoading(true);
        try {
            const endpoint = activeTab === 'assets' ? '/governance/assets' : '/governance/credentials';
            const response = await api.get(endpoint);
            setData(response.data);
        } catch (error) {
            console.error(`Erro ao carregar ${activeTab}:`, error);
        } finally {
            setLoading(false);
        }
    }

    useEffect(() => {
        fetchData();
    }, [activeTab]);

    // --- CRIAÇÃO (CREATE) ---
    async function handleCreate(e) {
        e.preventDefault();
        setSubmitting(true);
        try {
            const endpoint = activeTab === 'assets' ? '/governance/assets' : '/governance/credentials';

            // 🔧 PREPARAÇÃO DO PAYLOAD (CORREÇÃO DO ERRO 422)
            let payload = {
                name: formData.name,
                description: formData.description
            };

            if (activeTab === 'assets') {
                // Para Assets, enviamos 'value' e o tipo padrão
                payload.value = formData.value;
                payload.tipo = 'text';
            } else {
                // Para Credenciais, o backend espera 'password', não 'value'
                payload.password = formData.value;
                payload.username = 'robot_user'; // Valor padrão se não tivermos campo de user
            }

            // Envia o payload correto
            await api.post(endpoint, payload);

            // Sucesso
            setShowModal(false);
            setFormData({ name: '', value: '', description: '' });
            fetchData();
            alert("Item criado com sucesso!");

        } catch (error) {
            console.error(error);
            // Mostra o erro detalhado que vem do backend (ajuda a debugar)
            const msg = error.response?.data?.detail
                ? JSON.stringify(error.response.data.detail)
                : error.message;
            alert("Erro ao criar: " + msg);
        } finally {
            setSubmitting(false);
        }
    }

    // --- EXCLUSÃO (DELETE) ---
    async function handleDelete(id) {
        if (!confirm("Tem certeza que deseja excluir este item?")) return;

        try {
            const endpoint = activeTab === 'assets'
                ? `/governance/assets/${id}`
                : `/governance/credentials/${id}`;

            await api.delete(endpoint);
            fetchData();
        } catch (error) {
            alert("Erro ao excluir. (Verifique se a rota de delete existe no backend)");
        }
    }

    const copyToClipboard = (text) => {
        navigator.clipboard.writeText(text);
    };

    return (
        <div className="relative">
            {/* CABEÇALHO */}
            <div className="flex justify-between items-center mb-8">
                <div>
                    <h1 className="text-3xl font-bold text-white mb-2">Cofre & Governança</h1>
                    <p className="text-slate-400">Gerencie variáveis globais e credenciais seguras.</p>
                </div>
                <button
                    onClick={() => setShowModal(true)}
                    className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg flex items-center gap-2 transition-colors font-medium shadow-lg shadow-blue-900/20"
                >
                    <Plus size={20} />
                    <span>Novo {activeTab === 'assets' ? 'Asset' : 'Item'}</span>
                </button>
            </div>

            {/* ABAS */}
            <div className="flex gap-4 border-b border-slate-800 mb-6">
                <button
                    onClick={() => setActiveTab('assets')}
                    className={`flex items-center gap-2 px-4 py-3 border-b-2 transition-all ${activeTab === 'assets'
                        ? 'border-blue-500 text-blue-400 font-medium'
                        : 'border-transparent text-slate-500 hover:text-slate-300'
                        }`}
                >
                    <Database size={18} />
                    Variables (Assets)
                </button>
                <button
                    onClick={() => setActiveTab('credentials')}
                    className={`flex items-center gap-2 px-4 py-3 border-b-2 transition-all ${activeTab === 'credentials'
                        ? 'border-amber-500 text-amber-400 font-medium'
                        : 'border-transparent text-slate-500 hover:text-slate-300'
                        }`}
                >
                    <Shield size={18} />
                    Credentials (Vault)
                </button>
            </div>

            {/* LISTAGEM */}
            {loading ? (
                <div className="text-slate-400 flex items-center gap-2 py-10 justify-center">
                    <RefreshCw className="animate-spin" size={24} />
                    <span>Carregando...</span>
                </div>
            ) : (
                <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-xl min-h-[300px]">
                    <table className="w-full text-left">
                        <thead className="bg-slate-950 text-slate-400 uppercase text-xs font-semibold">
                            <tr>
                                <th className="px-6 py-4 w-16">Tipo</th>
                                <th className="px-6 py-4">Nome (Chave)</th>
                                <th className="px-6 py-4">Valor / Descrição</th>
                                <th className="px-6 py-4 text-right">Ações</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800 text-slate-300">
                            {data.length === 0 ? (
                                <tr>
                                    <td colSpan="4" className="px-6 py-12 text-center text-slate-500">
                                        <div className="flex flex-col items-center gap-3">
                                            <div className="p-4 bg-slate-800/50 rounded-full">
                                                {activeTab === 'assets' ? <Database size={32} /> : <Lock size={32} />}
                                            </div>
                                            <p>Nenhum item cadastrado.</p>
                                        </div>
                                    </td>
                                </tr>
                            ) : (
                                data.map((item) => (
                                    <tr key={item.id} className="hover:bg-slate-800/50 transition-colors group">
                                        <td className="px-6 py-4">
                                            {activeTab === 'assets' ? (
                                                <div className="p-2 bg-blue-500/10 text-blue-400 rounded-lg w-fit"><FileText size={18} /></div>
                                            ) : (
                                                <div className="p-2 bg-amber-500/10 text-amber-400 rounded-lg w-fit"><Key size={18} /></div>
                                            )}
                                        </td>
                                        <td className="px-6 py-4 font-mono text-white font-medium">{item.name}</td>
                                        <td className="px-6 py-4 text-slate-400">
                                            {activeTab === 'assets' ? (
                                                <div className="flex flex-col">
                                                    <span className="bg-slate-800 px-2 py-1 rounded text-sm text-slate-300 border border-slate-700 w-fit max-w-md truncate">
                                                        {item.value}
                                                    </span>
                                                    <span className="text-xs text-slate-600 mt-1">{item.description}</span>
                                                </div>
                                            ) : (
                                                <div className="flex items-center gap-2">
                                                    <span className="font-mono tracking-widest text-slate-600 text-xs bg-slate-950 px-2 py-1 rounded">••••••••••••••••</span>
                                                    <span className="text-xs text-slate-500 italic">(Seguro)</span>
                                                </div>
                                            )}
                                        </td>
                                        <td className="px-6 py-4 text-right">
                                            <div className="flex justify-end gap-2">
                                                <button onClick={() => copyToClipboard(item.name)} className="text-slate-500 hover:text-blue-400 p-2 hover:bg-blue-500/10 rounded transition-all" title="Copiar Chave">
                                                    <Copy size={18} />
                                                </button>
                                                <button onClick={() => handleDelete(item.id)} className="text-slate-500 hover:text-red-400 p-2 hover:bg-red-500/10 rounded transition-all" title="Excluir">
                                                    <Trash2 size={18} />
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            )}

            {/* --- MODAL DE CRIAÇÃO --- */}
            {showModal && (
                <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4 backdrop-blur-sm">
                    <div className="bg-slate-900 border border-slate-800 rounded-xl shadow-2xl w-full max-w-md animate-in fade-in zoom-in duration-200">
                        <div className="flex justify-between items-center p-6 border-b border-slate-800">
                            <h2 className="text-xl font-bold text-white flex items-center gap-2">
                                {activeTab === 'assets' ? <Database size={20} className="text-blue-500" /> : <Shield size={20} className="text-amber-500" />}
                                Novo {activeTab === 'assets' ? 'Asset' : 'Credencial'}
                            </h2>
                            <button onClick={() => setShowModal(false)} className="text-slate-400 hover:text-white">
                                <X size={24} />
                            </button>
                        </div>

                        <form onSubmit={handleCreate} className="p-6 space-y-4">
                            <div>
                                <label className="block text-sm text-slate-400 mb-1">Nome da Chave (ex: {activeTab === 'assets' ? 'URL_SITE' : 'SENHA_SAP'})</label>
                                <input
                                    type="text"
                                    required
                                    className="w-full bg-slate-950 border border-slate-700 rounded-lg p-3 text-white focus:border-blue-500 outline-none uppercase font-mono"
                                    value={formData.name}
                                    onChange={e => setFormData({ ...formData, name: e.target.value.toUpperCase().replace(/\s/g, '_') })}
                                    placeholder="MINHA_VARIAVEL"
                                />
                            </div>

                            <div>
                                <label className="block text-sm text-slate-400 mb-1">
                                    {activeTab === 'assets' ? 'Valor' : 'Senha / Segredo'}
                                </label>
                                {activeTab === 'assets' ? (
                                    <input
                                        type="text"
                                        required
                                        className="w-full bg-slate-950 border border-slate-700 rounded-lg p-3 text-white focus:border-blue-500 outline-none"
                                        value={formData.value}
                                        onChange={e => setFormData({ ...formData, value: e.target.value })}
                                        placeholder="https://exemplo.com"
                                    />
                                ) : (
                                    <input
                                        type="password"
                                        required
                                        className="w-full bg-slate-950 border border-slate-700 rounded-lg p-3 text-white focus:border-amber-500 outline-none"
                                        value={formData.value}
                                        onChange={e => setFormData({ ...formData, value: e.target.value })}
                                        placeholder="••••••••"
                                    />
                                )}
                            </div>

                            <div>
                                <label className="block text-sm text-slate-400 mb-1">Descrição (Opcional)</label>
                                <input
                                    type="text"
                                    className="w-full bg-slate-950 border border-slate-700 rounded-lg p-3 text-white focus:border-blue-500 outline-none"
                                    value={formData.description}
                                    onChange={e => setFormData({ ...formData, description: e.target.value })}
                                    placeholder="Para que serve isso?"
                                />
                            </div>

                            <div className="pt-4 flex gap-3">
                                <button
                                    type="button"
                                    onClick={() => setShowModal(false)}
                                    className="flex-1 px-4 py-2 rounded-lg border border-slate-700 text-slate-300 hover:bg-slate-800 transition-colors"
                                >
                                    Cancelar
                                </button>
                                <button
                                    type="submit"
                                    disabled={submitting}
                                    className={`flex-1 px-4 py-2 rounded-lg text-white font-medium flex justify-center items-center gap-2 transition-colors ${activeTab === 'assets' ? 'bg-blue-600 hover:bg-blue-700' : 'bg-amber-600 hover:bg-amber-700'
                                        }`}
                                >
                                    {submitting ? <RefreshCw className="animate-spin" size={18} /> : <Check size={18} />}
                                    Salvar
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}