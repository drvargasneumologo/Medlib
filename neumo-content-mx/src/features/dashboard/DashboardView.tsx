import { formatDistanceToNow } from 'date-fns';
import { es } from 'date-fns/locale';
import { mockTopics } from '../../data';
import { getDrafts } from '../../lib/storage/posts';

const hasAnthropicKey = !!import.meta.env.VITE_ANTHROPIC_KEY;
const hasGeminiKey = !!import.meta.env.VITE_GEMINI_KEY;
const hasOpenAIKey = !!import.meta.env.VITE_OPENAI_KEY;
const configuredCount = [hasAnthropicKey, hasGeminiKey, hasOpenAIKey].filter(Boolean).length;

const statusLabel: Record<string, string> = {
  borrador: '📝 Borrador',
  en_revision: '🔍 En revisión',
  aprobado: '✅ Aprobado',
  rechazado: '❌ Rechazado',
  programado: '📅 Programado',
  publicado: '🚀 Publicado',
};

export default function DashboardView() {
  const drafts = getDrafts();
  const alta = mockTopics.filter((t) => t.priority === 'alta').length;
  const media = mockTopics.filter((t) => t.priority === 'media').length;
  const published = drafts.filter((p) => p.status === 'publicado').length;

  const now = new Date();
  const nextScheduled = drafts
    .filter((p) => p.status === 'programado' && p.scheduledAt && new Date(p.scheduledAt) > now)
    .sort((a, b) => new Date(a.scheduledAt!).getTime() - new Date(b.scheduledAt!).getTime())[0];

  const recentPosts = drafts
    .filter((p) => p.status && p.status !== 'borrador')
    .slice(-5)
    .reverse();

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-1">Dashboard</h1>
      <p className="text-gray-500 mb-4">Resumen de tu estrategia de contenido médico</p>

      {/* Banner de API keys */}
      {configuredCount === 0 && (
        <div className="mb-6 flex items-start gap-3 bg-red-50 border border-red-200 rounded-xl px-4 py-3 text-sm text-red-700">
          <span className="shrink-0 mt-0.5">🔴</span>
          <span>
            Configura al menos una API key en <code className="bg-red-100 px-1 rounded">.env.local</code> para usar el Generador.{' '}
            <span className="font-medium">Ver README.</span>
          </span>
        </div>
      )}
      {configuredCount > 0 && configuredCount < 3 && (
        <div className="mb-6 flex items-start gap-3 bg-yellow-50 border border-yellow-200 rounded-xl px-4 py-3 text-sm text-yellow-700">
          <span className="shrink-0 mt-0.5">🟡</span>
          <span>Tienes {configuredCount}/3 modelos de IA configurados.</span>
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6 mt-2">
        <StatCard label="Temas totales" value={mockTopics.length} color="bg-brand-50 text-brand-700" />
        <StatCard label="Prioridad alta" value={alta} color="bg-red-50 text-red-700" />
        <StatCard label="Prioridad media" value={media} color="bg-yellow-50 text-yellow-700" />
        <StatCard label="Publicados" value={published} color="bg-green-50 text-green-700" />
      </div>

      <div className="grid gap-4 sm:grid-cols-2 mb-6">
        {/* Próxima publicación */}
        <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
          <h2 className="text-base font-semibold text-gray-800 mb-3">Próxima publicación</h2>
          {nextScheduled ? (
            <div>
              <p className="text-sm font-medium text-gray-900 line-clamp-2 mb-1">{nextScheduled.caption.slice(0, 80)}…</p>
              <p className="text-xs text-blue-600">
                🗓 {formatDistanceToNow(new Date(nextScheduled.scheduledAt!), { addSuffix: true, locale: es })}
              </p>
              <p className="text-xs text-gray-400 mt-0.5">
                {new Date(nextScheduled.scheduledAt!).toLocaleString('es-MX')}
              </p>
            </div>
          ) : (
            <p className="text-sm text-gray-400">Sin publicaciones programadas. Ve al Generador para crear contenido.</p>
          )}
        </div>

        {/* Temas sugeridos */}
        <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
          <h2 className="text-base font-semibold text-gray-800 mb-3">Temas de prioridad alta</h2>
          <ul className="space-y-2">
            {mockTopics
              .filter((t) => t.priority === 'alta')
              .slice(0, 4)
              .map((t) => (
                <li key={t.id} className="flex items-center gap-3 text-sm">
                  <span className="w-2 h-2 rounded-full bg-red-400 shrink-0" />
                  <span className="text-gray-700 truncate">{t.title}</span>
                  <span className="ml-auto text-xs text-gray-400 shrink-0">{t.category}</span>
                </li>
              ))}
          </ul>
        </div>
      </div>

      {/* Publicaciones recientes */}
      {recentPosts.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
          <h2 className="text-base font-semibold text-gray-800 mb-3">Publicaciones recientes</h2>
          <ul className="space-y-2">
            {recentPosts.map((post) => (
              <li key={post.id} className="flex items-center gap-3 text-sm">
                <span className="text-base">{['📸','💼','🐦','🎵'][['instagram','linkedin','twitter','tiktok'].indexOf(post.platform)] ?? '📄'}</span>
                <span className="text-gray-700 truncate flex-1">{post.caption.slice(0, 60)}…</span>
                <span className="badge bg-gray-100 text-gray-500 text-xs shrink-0">
                  {post.status ? statusLabel[post.status] : 'borrador'}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function StatCard({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className={`rounded-xl p-4 ${color}`}>
      <p className="text-2xl font-bold">{value}</p>
      <p className="text-xs mt-0.5 opacity-80">{label}</p>
    </div>
  );
}
