import { useEffect, useState } from 'react';
import {
    Layers, Plus, RefreshCw, Trash2, PlayCircle,
    CheckCircle, XCircle, Clock, Key, Database
} from 'lucide-react';
import api from '../services/api';

export function Workload() {
    const [items, setItems] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showModal, setShowModal] = useState(false);

    // Estado do formulário
    const [formData, setFormData] = useState({
        queue_name: 'fila_padrao',
        reference: '',
        priority: 'normal'
    });

    // Estado para o "Construtor de Payload" (Evita digitar JSON na mão)
    const [payloadFields, setPayloadFields] = useState([{ key: '', value: '' }]);

    // Busca dados da API
    async function fetchItems() {
        setLoading(true);
        try {
            const response = await api.get('/workload/items');
            setItems(response.data);
        } catch (error) {
            console.error("Erro ao buscar fila:", error);
        } finally {
            setLoading(false);
        }
    }

    useEffect(() => { fetchItems(); }, []);

    // Adiciona novo par Chave/Valor no construtor de payload
    const addPayloadField = () => {
        setPayloadFields([...payloadFields, { key: '', value: '' }]);
    };

    // Remove par Chave/Valor
    const removePayloadField = (index) => {
        const newFields = [...payloadFields];
        newFields.splice(index, 1);
        setPayloadFields(newFields);
    };

    // Atualiza par Chave/Valor
    const updatePayloadField = (index, field, newValue) => {
        const newFields = [...payloadFields];
        newFields[index][field] = newValue;
        setPayloadFields(newFields);
    };

    // Criar Item
    async function handleCreate(e) {
        e.preventDefault();
        try {
            // 1. Converte os campos visuais para um Objeto JSON real
            const finalPayload = {};
            payloadFields.forEach(field => {
                if (field.key.trim()) {
                    // Tenta converter números automaticamente (ex: "123" vira 123)
                    const isNumber = !isNaN(field.value) && field.value.trim() !== '';
                    finalPayload[field.key] = isNumber ? Number(field.value) : field.value;
                }
            });

            // 2. Se a referência estiver vazia, gera uma automática ou manda null
            const finalReference = formData.reference.trim() === ''
                ? `REF-${Date.now()}` // Gera algo como REF-1703020202
                : formData.reference;

            await api.post('/workload/items', {
                ...formData,
                reference: finalReference,
                payload: finalPayload,
                processo_id: null
            });

            setShowModal(false);
            // Reseta form
            setFormData({ queue_name: 'fila_padrao', reference: '', priority: 'normal' });
            setPayloadFields([{ key: '', value: '' }]);

            fetchItems();
            alert("Item criado com sucesso!");
        } catch (error) {
            alert("Erro ao criar: " + (error.response?.data?.detail || error.message));
        }
    }

    // Deletar Item
    async function handleDelete(id) {
        if (!confirm("Excluir item?")) return;
        try {
            await api.delete(`/workload/items/${id}`);
            fetchItems();
        } catch (error) {
            alert("Erro ao excluir.");
        }
    }

    const getStatusIcon = (status) => {
        const map = {
            pending: <Clock className="text-slate-400" size={18} />,
            processing: <PlayCircle className="text-blue-400 animate-pulse" size={18} />,
            completed: <CheckCircle className="text-green-400" size={18} />,
            failed: <XCircle className="text-red-400" size={18} />
        };
        return map[status] || <Layers size={18} />;
    };

    return (
        <div>
            <div className="flex justify-between items-center mb-8">
                <div>
                    <h1 className="text-3xl font-bold text-white mb-2">Fila de Trabalho</h1>
                    <p className="text-slate-400">Monitoramento de itens a processar.</p>
                </div>
                <button onClick={() => setShowModal(true)} className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg flex gap-2 items-center shadow-lg shadow-blue-900/20">
                    <Plus size={20} /> Novo Item
                </button>
            </div>

            {loading ? <div className="text-center py-10 text-slate-500"><RefreshCw className="animate-spin inline mr-2" />Carregando...</div> : (
                <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-xl min-h-[300px]">
                    <table className="w-full text-left">
                        <thead className="bg-slate-950 text-slate-400 uppercase text-xs font-semibold">
                            <tr>
                                <th className="px-6 py-4">Status</th>
                                <th className="px-6 py-4">Fila / Ref Negócio</th>
                                <th className="px-6 py-4">Prioridade</th>
                                <th className="px-6 py-4">Dados (Payload)</th>
                                <th className="px-6 py-4 text-right">Ações</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800 text-slate-300">
                            {items.length === 0 ? <tr><td colSpan="5" className="text-center py-12 text-slate-500">Nenhum item na fila.</td></tr> : items.map(item => (
                                <tr key={item.id} className="hover:bg-slate-800/50 transition-colors">
                                    <td className="px-6 py-4 flex gap-2 items-center">{getStatusIcon(item.status)} <span className="capitalize text-sm">{item.status}</span></td>
                                    <td className="px-6 py-4">
                                        <div className="font-medium text-white">{item.queue_name}</div>
                                        <div className="text-xs text-blue-400 font-mono bg-blue-400/10 px-1 rounded w-fit mt-1" title="Referência de Negócio">
                                            {item.reference || "Sem Ref"}
                                        </div>
                                    </td>
                                    <td className="px-6 py-4">
                                        <span className={`px-2 py-1 rounded text-xs font-bold ${item.priority === 'high' || item.priority === 'critical' ? 'bg-amber-500/20 text-amber-400' : 'bg-slate-800 text-slate-400'}`}>
                                            {item.priority}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4">
                                        <code className="text-xs text-slate-400 bg-slate-950 px-2 py-1 rounded border border-slate-800 block max-w-[200px] truncate" title={JSON.stringify(item.payload, null, 2)}>
                                            {JSON.stringify(item.payload)}
                                        </code>
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
                    <div className="bg-slate-900 border border-slate-800 rounded-xl w-full max-w-lg shadow-2xl animate-in fade-in zoom-in duration-200 flex flex-col max-h-[90vh]">

                        <div className="p-6 border-b border-slate-800">
                            <h2 className="text-xl font-bold text-white flex items-center gap-2">
                                <Layers className="text-blue-500" /> Adicionar à Fila
                            </h2>
                            <p className="text-slate-400 text-sm mt-1">Defina os dados que o robô irá processar.</p>
                        </div>

                        <form onSubmit={handleCreate} className="p-6 overflow-y-auto custom-scrollbar">

                            {/* CONFIGURAÇÃO DA FILA */}
                            <div className="space-y-4 mb-6">
                                <div>
                                    <label className="text-sm text-slate-300 font-medium mb-1 block">Nome da Fila</label>
                                    <input
                                        className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-white focus:border-blue-500 outline-none"
                                        placeholder="Ex: fila_notas_fiscais"
                                        value={formData.queue_name}
                                        onChange={e => setFormData({ ...formData, queue_name: e.target.value })}
                                        required
                                    />
                                </div>

                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <label className="text-sm text-slate-300 font-medium mb-1 block">Referência <span className="text-slate-500 font-normal">(Opcional)</span></label>
                                        <input
                                            className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-white focus:border-blue-500 outline-none"
                                            placeholder="Ex: NF-2024-001"
                                            value={formData.reference}
                                            onChange={e => setFormData({ ...formData, reference: e.target.value })}
                                        />
                                        <p className="text-xs text-slate-500 mt-1">Identificador único do negócio (ex: CPF, ID Pedido).</p>
                                    </div>
                                    <div>
                                        <label className="text-sm text-slate-300 font-medium mb-1 block">Prioridade</label>
                                        <select
                                            className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-white focus:border-blue-500 outline-none"
                                            value={formData.priority}
                                            onChange={e => setFormData({ ...formData, priority: e.target.value })}
                                        >
                                            <option value="low">Baixa</option>
                                            <option value="normal">Normal</option>
                                            <option value="high">Alta</option>
                                            <option value="critical">Crítica</option>
                                        </select>
                                    </div>
                                </div>
                            </div>

                            {/* CONSTRUTOR DE PAYLOAD (JSON) */}
                            <div className="border-t border-slate-800 pt-4">
                                <div className="flex justify-between items-center mb-3">
                                    <label className="text-sm text-slate-300 font-medium flex items-center gap-2">
                                        <Database size={16} className="text-blue-400" />
                                        Dados de Entrada (Payload)
                                    </label>
                                    <button type="button" onClick={addPayloadField} className="text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1">
                                        <Plus size={14} /> Adicionar Campo
                                    </button>
                                </div>

                                <div className="space-y-2 bg-slate-950/50 p-3 rounded-lg border border-slate-800">
                                    {payloadFields.map((field, index) => (
                                        <div key={index} className="flex gap-2">
                                            <input
                                                className="flex-1 bg-slate-900 border border-slate-700 rounded p-2 text-sm text-white placeholder:text-slate-600 focus:border-blue-500 outline-none"
                                                placeholder="Chave (ex: valor)"
                                                value={field.key}
                                                onChange={e => updatePayloadField(index, 'key', e.target.value)}
                                            />
                                            <input
                                                className="flex-[2] bg-slate-900 border border-slate-700 rounded p-2 text-sm text-white placeholder:text-slate-600 focus:border-blue-500 outline-none"
                                                placeholder="Valor (ex: 150.00)"
                                                value={field.value}
                                                onChange={e => updatePayloadField(index, 'value', e.target.value)}
                                            />
                                            {payloadFields.length > 1 && (
                                                <button type="button" onClick={() => removePayloadField(index)} className="text-slate-600 hover:text-red-400 p-1">
                                                    <XCircle size={18} />
                                                </button>
                                            )}
                                        </div>
                                    ))}
                                    <div className="text-xs text-slate-500 pt-1 italic">
                                        O sistema irá gerar um JSON automaticamente com estes campos.
                                    </div>
                                </div>
                            </div>

                        </form>

                        <div className="p-6 border-t border-slate-800 flex gap-3 bg-slate-900 rounded-b-xl">
                            <button type="button" onClick={() => setShowModal(false)} className="flex-1 py-2.5 border border-slate-700 text-slate-300 rounded-lg hover:bg-slate-800 transition-colors">
                                Cancelar
                            </button>
                            <button onClick={handleCreate} className="flex-1 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium transition-colors shadow-lg shadow-blue-900/20">
                                Criar Tarefa
                            </button>
                        </div>

                    </div>
                </div>
            )}
        </div>
    );
}