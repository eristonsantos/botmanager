import axios from 'axios';

// AQUI ESTÁ A MÁGICA 👇
// O import.meta.env.VITE_API_URL é como o Vite lê o que passamos no Dockerfile
const api = axios.create({
    baseURL: import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api/v1',
});

// Interceptador para adicionar o Token automaticamente
api.interceptors.request.use((config) => {
    const token = localStorage.getItem('@BotManager:token');
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

export default api;