/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                cognitx: {
                    // Fundo: Preto levemente azulado (Profundo e moderno)
                    dark: '#020617',
                    // Painéis/Cards: Um pouco mais claro que o fundo
                    panel: '#0f172a',
                    // Bordas: Para separar elementos sutilmente
                    border: '#1e293b',

                    // Cores da Marca
                    main: '#3b82f6',    // Azul Principal (Botões, Links)
                    hover: '#2563eb',   // Azul mais escuro (Hover)
                    teal: '#2dd4bf',    // Verde-Água (Detalhes, Ícones, Acentos)
                    success: '#10b981', // Verde (Status Online, Sucesso)
                    danger: '#ef4444',  // Vermelho (Erros, Offline)
                }
            },
            fontFamily: {
                sans: ['Inter', 'sans-serif'],
            },
            animation: {
                'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
            }
        },
    },
    plugins: [],
}