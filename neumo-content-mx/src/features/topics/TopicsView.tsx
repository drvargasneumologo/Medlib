import { mockTopics, mockHashtagSets } from '../../data';

const priorityColor: Record<string, string> = {
  alta: 'bg-red-100 text-red-700',
  media: 'bg-yellow-100 text-yellow-700',
  baja: 'bg-gray-100 text-gray-600',
};

const categoryLabel: Record<string, string> = {
  patologia: 'Patología',
  prevencion: 'Prevención',
  sintoma: 'Síntoma',
  educacion_medica: 'Educación médica',
};

export default function TopicsView() {
  return (
    <div className="p-6 max-w-5xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-1">Temas</h1>
      <p className="text-gray-500 mb-6">Banco de temas para contenido médico en redes sociales</p>

      <div className="grid gap-4 sm:grid-cols-2">
        {mockTopics.map((topic) => {
          const hashtagSet = topic.hashtagSetId
            ? mockHashtagSets.find((hs) => hs.id === topic.hashtagSetId)
            : undefined;

          return (
            <div
              key={topic.id}
              className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm hover:shadow-md transition-shadow"
            >
              {/* Header */}
              <div className="flex items-start justify-between gap-2 mb-2">
                <h2 className="text-base font-semibold text-gray-900 leading-snug">
                  {topic.title}
                </h2>
                <span className={`badge shrink-0 ${priorityColor[topic.priority]}`}>
                  {topic.priority}
                </span>
              </div>

              <p className="text-sm text-gray-500 mb-3">{topic.description}</p>

              {/* Meta */}
              <div className="flex flex-wrap gap-2 mb-3">
                <span className="badge bg-brand-50 text-brand-700">
                  {categoryLabel[topic.category]}
                </span>
                <span className="badge bg-gray-100 text-gray-600">
                  {topic.targetAudience}
                </span>
                {topic.platform.map((p) => (
                  <span key={p} className="badge bg-gray-100 text-gray-600">
                    {p}
                  </span>
                ))}
              </div>

              {/* Keywords */}
              <div className="flex flex-wrap gap-1 mb-3">
                {topic.keywords.map((kw) => (
                  <span key={kw} className="badge bg-gray-50 text-gray-500 border border-gray-200">
                    {kw}
                  </span>
                ))}
              </div>

              {/* Hashtags sugeridos (v2) */}
              {hashtagSet && (
                <div className="mt-3 pt-3 border-t border-gray-100">
                  <p className="text-xs text-gray-400 font-medium mb-1.5 uppercase tracking-wide">
                    Hashtags · {hashtagSet.platform}
                  </p>
                  <div className="flex flex-wrap gap-1">
                    {hashtagSet.hashtags.map((ht) => (
                      <span
                        key={ht}
                        className="badge bg-brand-50 text-brand-700"
                      >
                        {ht}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
