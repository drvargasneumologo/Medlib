import { NavLink, Outlet } from 'react-router-dom';

const navItems = [
  { to: '/', label: 'Dashboard', icon: '🏠' },
  { to: '/temas', label: 'Temas', icon: '📋' },
  { to: '/generador', label: 'Generador', icon: '✍️' },
  { to: '/calendario', label: 'Calendario', icon: '📅' },
  { to: '/diseno', label: 'Diseño', icon: '🎨' },
  { to: '/auditoria', label: 'Auditoría', icon: '📊' },
  { to: '/servicios', label: 'Servicios', icon: '🏥' },
  { to: '/consultorios', label: 'Consultorios', icon: '📍' },
  { to: '/perfil', label: 'Perfil', icon: '👤' },
];

export default function Layout() {
  return (
    <div className="min-h-screen flex bg-gray-50">
      {/* Sidebar */}
      <aside className="w-56 shrink-0 bg-white border-r border-gray-200 flex flex-col">
        <div className="px-4 py-5 border-b border-gray-100">
          <span className="text-sm font-bold text-brand-700">🫁 NeumoContent MX</span>
        </div>
        <nav className="flex-1 px-2 py-4 space-y-0.5">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors ${
                  isActive
                    ? 'bg-brand-50 text-brand-700 font-medium'
                    : 'text-gray-600 hover:bg-gray-100'
                }`
              }
            >
              <span>{item.icon}</span>
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="px-4 py-3 border-t border-gray-100 text-xs text-gray-400">
          v2.0 · NeumoContent MX
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  );
}
