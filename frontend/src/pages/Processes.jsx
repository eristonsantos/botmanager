import { useEffect, useState } from 'react';
import {
    Package, Plus, Search, MoreHorizontal, FileCode,
    GitBranch, CheckCircle2, PlayCircle, Clock, Trash2, Tag
} from 'lucide-react';
import api from '../services/api';

export function Processes() {
    const [processes, setProcesses] = useState([]);
    const [loading, setLoading] = useState(true);

    // Modais
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [showVersionsModal, setShowVersionsModal] = useState(false);

    // Seleção e Dados
    const [selectedProcess, setSelectedProcess] = useState(null);
    const [versions, setVersions] = useState([]);
    const [loadingVersions, setLoadingVersions] = useState(false);

    // Forms
    const [processForm, setProcessForm] = useState({ name: '', description: '', tipo: 'unattended', tags: '' });
    const [versionForm, setVersionForm] = useState({ version: '', package_path: '', release_notes: '' });
    const [showNewVersionForm, setShowNewVersionForm] = useState(false);

    // --- CARREGAR PROCESSOS ---
    async function fetchProcesses() {
        setLoading(true);
        try {
            const response = await api.get('/processes');
            setProcesses(response.data.items || []);
        } catch (error) {
            console.error("Erro ao buscar processos:", error);
        } finally {
            setLoading(false);
        }
    }

    useEffect(() => { fetchProcesses(); }, []);

    // --- CRIAR PROCESSO ---
    async function handleCreateProcess(e) {
        e.preventDefault();
        try {
            // Converte tags de string "tag1, tag2" para array ["tag1", "tag2"]
            const tagsArray = processForm.tags.split(',').map(t => t.trim()).filter(t => t);

            await api.post('/processes', { ...processForm, tags: tagsArray });

            setShowCreateModal(false);
            setProcessForm({ name: '', description: '', tipo: 'unattended', tags: '' });
            fetchProcesses();
            alert("Processo criado!");
        } catch (error) {
            alert("Erro ao criar: " + (error.response?.data?.detail || error.message));
        }
    }

    // --- GESTÃO DE VERSÕES ---
    async function openVersionsManager(process) {
        setSelectedProcess(process);
        setShowVersionsModal(true);
        setShowNewVersionForm(false);
        fetchVersions(process.id);
    }

    async function fetchVersions(processId) {
        setLoadingVersions(true);
        try {
            const response = await api.get(`/processes/${processId}/versions`);
            // Ordena descrescente por versão ou data
            const sorted = (response.data.items || []).sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
            setVersions(sorted);
        } catch (error) {
            alert("Erro ao carregar versões.");
        } finally {
            setLoadingVersions(false);
        }
    }

    async function handleCreateVersion(e) {
        e.preventDefault();
        try {
            await api.post(`/processes/${selectedProcess.id}/versions`, versionForm);
            setVersionForm({ version: '', package_path: '', release_notes: '' });
            setShowNewVersionForm(false);
            fetchVersions(selectedProcess.id);
            alert("Versão criada! Lembre-se de ativá-la se quiser usar.");
        } catch (error) {
            alert("Erro ao criar versão: " + (error.response?.data?.detail || error.message));
        }
    }

    async function handleActivateVersion(version) {
        if (!confirm(`Deseja ativar a versão ${version.version}? Isso desativará a atual.`)) return;
        try {
            await api.put(`/processes/${selectedProcess.id}/versions/${version.id}/activate`);
            fetchVersions(selectedProcess.id);
            fetchProcesses(); // Atualiza a lista principal também
        } catch (error) {
            alert("Erro ao ativar versão.");
        }
    }

    async function handleDeleteProcess(id) {
        if (!confirm("Tem certeza? Isso arquivará o processo.")) return;
        try {
            await api.delete(`/processes/${id}`);
            fetchProcesses();
        } catch (error) {
            alert("Erro ao deletar.");
        }
    }

    return (
        <div>
            {/* CABEÇALHO */}
            <div className="flex justify-between items-center mb-8">
                <div>
                    <h1 className="text-3xl font-bold text-white mb-2">Processos & Pacotes</h1>
                    <p className="text-slate-400">Gerencie o ciclo de vida das suas automações.</p>
                </div>
                <button onClick={() => setShowCreateModal(true)} className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg flex gap-2 items-center shadow-lg">
                    <Plus size={20} /> Novo Processo
                </button>
            </div>

            {/* LISTAGEM DE PROCESSOS */}
            {loading ? <div className="text-center text-slate-500 py-10">Carregando...</div> : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {processes.map(proc => (
                        <div key={proc.id} className="bg-slate-900 border border-slate-800 rounded-xl p-6 hover:border-blue-500/30 transition-colors shadow-lg">
                            <div className="flex justify-between items-start mb-4">
                                <div className="p-3 bg-blue-500/10 rounded-lg text-blue-400">
                                    <Package size={24} />
                                </div>
                                <div className="flex gap-2">
                                    <span className={`text-xs px-2 py-1 rounded border ${proc.is_active ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400' : 'bg-slate-800 border-slate-700 text-slate-500'}`}>
                                        {proc.is_active ? 'Ativo' : 'Inativo'}
                                    </span>
                                </div>
                            </div>

                            <h3 className="text-xl font-bold text-white mb-1">{proc.name}</h3>
                            <p className="text-slate-400 text-sm h-10 line-clamp-2 mb-4">{proc.description || "Sem descrição."}</p>

                            <div className="flex flex-wrap gap-2 mb-6">
                                {proc.tags && proc.tags.map(tag => (
                                    <span key={tag} className="text-xs bg-slate-800 text-slate-400 px-2 py-1 rounded flex items-center gap-1">
                                        <Tag size={10} /> {tag}
                                    </span>
                                ))}
                            </div>

                            <div className="flex items-center justify-between pt-4 border-t border-slate-800">
                                <div className="text-sm">
                                    <span className="text-slate-500 block text-xs">Versão Ativa</span>
                                    <span className="text-white font-mono">{proc.active_version || "Nenhuma"}</span>
                                </div>
                                <div className="flex gap-2">
                                    <button onClick={() => handleDeleteProcess(proc.id)} className="p-2 text-slate-500 hover:text-red-400 hover:bg-slate-800 rounded"><Trash2 size={18} /></button>
                                    <button
                                        onClick={() => openVersionsManager(proc)}
                                        className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-white text-sm rounded flex items-center gap-2"
                                    >
                                        <GitBranch size={16} /> Versões
                                    </button>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* --- MODAL CRIAÇÃO DE PROCESSO --- */}
            {showCreateModal && (
                <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4 backdrop-blur-sm">
                    <div className="bg-slate-900 border border-slate-800 rounded-xl w-full max-w-md p-6 shadow-2xl">
                        <h2 className="text-xl font-bold text-white mb-4">Novo Processo</h2>
                        <form onSubmit={handleCreateProcess} className="space-y-4">
                            <input className="w-full bg-slate-950 border border-slate-700 rounded p-3 text-white" placeholder="Nome Único (ex: Faturas)" value={processForm.name} onChange={e => setProcessForm({ ...processForm, name: e.target.value })} required />
                            <textarea className="w-full bg-slate-950 border border-slate-700 rounded p-3 text-white" placeholder="Descrição" value={processForm.description} onChange={e => setProcessForm({ ...processForm, description: e.target.value })} />
                            <select className="w-full bg-slate-950 border border-slate-700 rounded p-3 text-white" value={processForm.tipo} onChange={e => setProcessForm({ ...processForm, tipo: e.target.value })}>
                                <option value="unattended">Unattended (Robô Sozinho)</option>
                                <option value="attended">Attended (Com Humano)</option>
                            </select>
                            <input className="w-full bg-slate-950 border border-slate-700 rounded p-3 text-white" placeholder="Tags (separadas por vírgula)" value={processForm.tags} onChange={e => setProcessForm({ ...processForm, tags: e.target.value })} />
                            <div className="flex gap-3 pt-2">
                                <button type="button" onClick={() => setShowCreateModal(false)} className="flex-1 py-2 border border-slate-700 text-slate-300 rounded">Cancelar</button>
                                <button type="submit" className="flex-1 py-2 bg-blue-600 text-white rounded">Criar</button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* --- MODAL DE VERSÕES (O COFRE DOS CÓDIGOS) --- */}
            {showVersionsModal && selectedProcess && (
                <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4 backdrop-blur-sm">
                    <div className="bg-slate-900 border border-slate-800 rounded-xl w-full max-w-2xl p-0 shadow-2xl flex flex-col max-h-[80vh]">
                        {/* Header Modal */}
                        <div className="p-6 border-b border-slate-800 flex justify-between items-center">
                            <div>
                                <h2 className="text-xl font-bold text-white flex items-center gap-2"><Package className="text-blue-500" /> {selectedProcess.name}</h2>
                                <p className="text-slate-400 text-sm">Gerenciamento de Pacotes e Versões</p>
                            </div>
                            <button onClick={() => setShowVersionsModal(false)} className="text-slate-400 hover:text-white"><Trash2 className="rotate-45" size={24} /></button> {/* Ícone X improvisado com Trash rodado ou use X */}
                        </div>

                        {/* Conteúdo Modal */}
                        <div className="p-6 overflow-y-auto flex-1 custom-scrollbar">

                            {/* Botão para abrir form de nova versão */}
                            {!showNewVersionForm ? (
                                <button onClick={() => setShowNewVersionForm(true)} className="w-full py-3 border-2 border-dashed border-slate-700 text-slate-400 rounded-lg hover:border-blue-500 hover:text-blue-400 transition-all mb-6 flex justify-center items-center gap-2">
                                    <Plus size={20} /> Publicar Nova Versão
                                </button>
                            ) : (
                                <form onSubmit={handleCreateVersion} className="bg-slate-950 p-4 rounded-lg border border-slate-700 mb-6 space-y-3">
                                    <h3 className="text-white font-medium mb-2">Nova Versão</h3>
                                    <div className="grid grid-cols-2 gap-3">
                                        <input className="bg-slate-900 border border-slate-700 rounded p-2 text-white" placeholder="Versão (ex: 1.0.0)" value={versionForm.version} onChange={e => setVersionForm({ ...versionForm, version: e.target.value })} required />
                                        <input className="bg-slate-900 border border-slate-700 rounded p-2 text-white" placeholder="Caminho do Pacote (S3/Path)" value={versionForm.package_path} onChange={e => setVersionForm({ ...versionForm, package_path: e.target.value })} required />
                                    </div>
                                    <textarea className="w-full bg-slate-900 border border-slate-700 rounded p-2 text-white text-sm" placeholder="O que mudou nesta versão?" value={versionForm.release_notes} onChange={e => setVersionForm({ ...versionForm, release_notes: e.target.value })} />
                                    <div className="flex gap-2 justify-end">
                                        <button type="button" onClick={() => setShowNewVersionForm(false)} className="px-3 py-1 text-slate-400 text-sm">Cancelar</button>
                                        <button type="submit" className="px-3 py-1 bg-emerald-600 text-white text-sm rounded hover:bg-emerald-700">Publicar</button>
                                    </div>
                                </form>
                            )}

                            {/* Lista de Versões */}
                            <h3 className="text-slate-300 font-medium mb-3 flex items-center gap-2"><Clock size={16} /> Histórico</h3>
                            <div className="space-y-3">
                                {loadingVersions ? <div className="text-center text-slate-500">Carregando versões...</div> : versions.length === 0 ? <p className="text-slate-500 text-sm">Nenhuma versão publicada.</p> : versions.map(v => (
                                    <div key={v.id} className={`p-4 rounded-lg border flex justify-between items-center ${v.is_active ? 'bg-blue-900/20 border-blue-500/50' : 'bg-slate-950 border-slate-800'}`}>
                                        <div>
                                            <div className="flex items-center gap-3">
                                                <span className="text-white font-mono font-bold text-lg">v{v.version}</span>
                                                {v.is_active && <span className="text-xs bg-blue-500 text-white px-2 py-0.5 rounded-full flex items-center gap-1"><CheckCircle2 size={10} /> ATIVA</span>}
                                            </div>
                                            <p className="text-xs text-slate-500 mt-1">{new Date(v.created_at).toLocaleString()}</p>
                                            {v.release_notes && <p className="text-sm text-slate-400 mt-2 border-l-2 border-slate-700 pl-2">{v.release_notes}</p>}
                                        </div>

                                        {!v.is_active && (
                                            <button onClick={() => handleActivateVersion(v)} className="p-2 text-slate-400 hover:text-emerald-400 hover:bg-emerald-500/10 rounded-full transition-colors" title="Ativar esta versão">
                                                <PlayCircle size={24} />
                                            </button>
                                        )}
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}