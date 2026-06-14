import { mockTopics, mockPosts } from '../../data';

const hasAnthropicKey = !!import.meta.env.VITE_ANTHROPIC_KEY;
const hasGeminiKey = !!import.meta.env.VITE_GEMINI_KEY;
const hasOpenAIKey = !!import.meta.env.VITE_OPENAI_KEY;
const configuredCount = [hasAnthropicKey, hasGeminiKey, hasOpenAIKey].filter(Boolean).length;

export default function DashboardView() {
  const alta = mockTopics.filter((t) => t.priority === 'alta').length;
  const media = mockTopics.filter((t) => t.priority === 'media').length;

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

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8 mt-2">
        <StatCard label="Temas totales" value={mockTopics.length} color="bg-brand-50 text-brand-700" />
        <StatCard label="Prioridad alta" value={alta} color="bg-red-50 text-red-700" />
        <StatCard label="Prioridad media" value={media} color="bg-yellow-50 text-yellow-700" />
        <StatCard label="Posts creados" value={mockPosts.length} color="bg-green-50 text-green-700" />
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
        <h2 className="text-base font-semibold text-gray-800 mb-3">Próximos temas sugeridos</h2>
        <ul className="space-y-2">
          {mockTopics
            .filter((t) => t.priority === 'alta')
            .slice(0, 4)
            .map((t) => (
              <li key={t.id} className="flex items-center gap-3 text-sm">
                <span className="w-2 h-2 rounded-full bg-red-400 shrink-0" />
                <span className="text-gray-700">{t.title}</span>
                <span className="ml-auto text-xs text-gray-400">{t.category}</span>
              </li>
            ))}
        </ul>
      </div>
    </div>
  );
}

function StatCard({
  label,
  value,
  color,
}: {
  label: string;
  value: number;
  color: string;
}) {
  return (
    <div className={`rounded-xl p-4 ${color}`}>
      <p className="text-2xl font-bold">{value}</p>
      <p className="text-xs mt-0.5 opacity-80">{label}</p>
    </div>
  );
}
