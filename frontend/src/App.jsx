import React from 'react';
import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom';
import { AuthProvider, useAuth } from './auth';

// --- IMPORTAÇÕES CORRIGIDAS (Com chaves { } para Named Exports) ---
// O Login eu mandei como default recentemente, então deixamos sem chaves. 
// Se der erro no Login, coloque chaves nele também: import { Login } ...
import Login from './pages/Login';

import { Dashboard } from './pages/Dashboard';
import { Agents } from './pages/Agents';
import { Workload } from './pages/Workload';
import { Governance } from './pages/Governance';
import { Schedules } from './pages/Schedules';
import { Processes } from './pages/Processes';
import { Tasks } from './pages/Tasks';

// Layout também deve ser importado com chaves se for "export function Layout"
import { Layout } from './components/Layout';

// Componente que protege as rotas
const PrivateRoute = () => {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="h-screen w-full flex items-center justify-center bg-cognitx-dark text-cognitx-teal animate-pulse">
        Carregando sistema...
      </div>
    );
  }

  return user ? <Outlet /> : <Navigate to="/login" replace />;
};

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Rota Pública */}
          <Route path="/login" element={<Login />} />

          {/* Redirecionamento da Raiz */}
          <Route path="/" element={<Navigate to="/dashboard" replace />} />

          {/* Rotas Protegidas */}
          <Route element={<PrivateRoute />}>
            <Route element={<Layout />}>
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/agents" element={<Agents />} />
              <Route path="/workload" element={<Workload />} />
              <Route path="/tasks" element={<Tasks />} />
              <Route path="/governance" element={<Governance />} />
              <Route path="/schedules" element={<Schedules />} />
              <Route path="/processes" element={<Processes />} />
            </Route>
          </Route>

          {/* Rota 404 - Volta para inicio */}
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;