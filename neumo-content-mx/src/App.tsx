import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import DashboardView from './features/dashboard/DashboardView';
import TopicsView from './features/topics/TopicsView';
import GeneratorView from './features/posts/GeneratorView';
import PlaceholderView from './features/placeholder/PlaceholderView';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<DashboardView />} />
          <Route path="temas" element={<TopicsView />} />
          <Route path="generador" element={<GeneratorView />} />
          <Route
            path="calendario"
            element={<PlaceholderView title="Calendario" description="Planificación de publicaciones" icon="📅" />}
          />
          <Route
            path="diseno"
            element={<PlaceholderView title="Diseño" description="Plantillas visuales para posts" icon="🎨" />}
          />
          <Route
            path="auditoria"
            element={<PlaceholderView title="Auditoría" description="Análisis de rendimiento de contenido" icon="📊" />}
          />
          <Route
            path="servicios"
            element={<PlaceholderView title="Servicios" description="Catálogo de servicios del consultorio" icon="🏥" />}
          />
          <Route
            path="consultorios"
            element={<PlaceholderView title="Consultorios" description="Ubicaciones y horarios" icon="📍" />}
          />
          <Route
            path="perfil"
            element={<PlaceholderView title="Perfil" description="Datos del médico y su especialidad" icon="👤" />}
          />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
