import React, { createContext, useContext, useState, useEffect } from 'react';
// CORREÇÃO AQUI: Caminho para services
import api from './services/api';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const token = localStorage.getItem('@BotManager:token'); // Usei a chave que vi no seu Login antigo
        if (token) {
            api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
            setUser({ name: 'Admin', token });
        }
        setLoading(false);
    }, []);

    const login = async (username, password) => {
        // Ajuste para o formato que seu backend espera (JSON ou FormData)
        // Baseado no seu backend auth.py, ele espera JSON no corpo se for /auth/login
        // ou FormData se for OAuth2 padrão /token. 
        // Vamos tentar manter o padrão JSON que vi no seu Login.jsx antigo:
        try {
            const response = await api.post('/auth/login', {
                email: username,
                password: password
            });

            const { access_token } = response.data;

            localStorage.setItem('@BotManager:token', access_token);
            api.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;

            setUser({ username, token: access_token });
            return true;
        } catch (error) {
            console.error("Erro no login:", error);
            throw error;
        }
    };

    const logout = () => {
        localStorage.removeItem('@BotManager:token');
        delete api.defaults.headers.common['Authorization'];
        setUser(null);
    };

    return (
        <AuthContext.Provider value={{ user, login, logout, loading }}>
            {!loading && children}
        </AuthContext.Provider>
    );
};

export const useAuth = () => {
    return useContext(AuthContext);
};