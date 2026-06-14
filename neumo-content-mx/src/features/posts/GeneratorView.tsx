import { useState } from 'react';
import { mockTopics, mockPosts, mockHashtagSets } from '../../data';

const platformIcon: Record<string, string> = {
  instagram: '📸',
  linkedin: '💼',
  twitter: '🐦',
  tiktok: '🎵',
};

export default function GeneratorView() {
  const [selectedTopicId, setSelectedTopicId] = useState('');

  const selectedTopic = mockTopics.find((t) => t.id === selectedTopicId);
  const suggestedHashtagSet = selectedTopic?.hashtagSetId
    ? mockHashtagSets.find((hs) => hs.id === selectedTopic.hashtagSetId)
    : undefined;

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-1">Generador de contenido</h1>
      <p className="text-gray-500 mb-6">Crea posts optimizados para cada red social</p>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Panel izquierdo — configuración */}
        <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
          <h2 className="text-base font-semibold text-gray-800 mb-4">Configuración</h2>

          <label className="block text-sm font-medium text-gray-700 mb-1">
            Tema
          </label>
          <select
            value={selectedTopicId}
            onChange={(e) => setSelectedTopicId(e.target.value)}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 mb-4"
          >
            <option value="">— Selecciona un tema —</option>
            {mockTopics.map((t) => (
              <option key={t.id} value={t.id}>
                {t.title}
              </option>
            ))}
          </select>

          {/* Hashtags sugeridos (v2) */}
          {suggestedHashtagSet && (
            <div className="bg-brand-50 rounded-lg p-3 border border-brand-100">
              <p className="text-xs font-semibold text-brand-700 uppercase tracking-wide mb-2">
                Hashtags sugeridos · {suggestedHashtagSet.platform}
              </p>
              <div className="flex flex-wrap gap-1">
                {suggestedHashtagSet.hashtags.map((ht) => (
                  <span key={ht} className="badge bg-white text-brand-700 border border-brand-200">
                    {ht}
                  </span>
                ))}
              </div>
              {suggestedHashtagSet.notes && (
                <p className="text-xs text-brand-600 mt-2 italic">{suggestedHashtagSet.notes}</p>
              )}
            </div>
          )}

          {selectedTopic && (
            <div className="mt-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Plataforma objetivo
              </label>
              <div className="flex flex-wrap gap-2">
                {selectedTopic.platform.map((p) => (
                  <button
                    key={p}
                    className="badge bg-gray-100 text-gray-700 border border-gray-200 cursor-pointer hover:bg-brand-50 hover:text-brand-700 transition-colors py-1 px-3"
                  >
                    {platformIcon[p]} {p}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Panel derecho — posts existentes */}
        <div className="space-y-4">
          <h2 className="text-base font-semibold text-gray-800">Posts recientes</h2>
          {mockPosts.map((post) => {
            const topic = mockTopics.find((t) => t.id === post.topicId);
            return (
              <div
                key={post.id}
                className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm"
              >
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-lg">{platformIcon[post.platform]}</span>
                  <span className="text-xs font-medium text-gray-500 uppercase">
                    {post.platform}
                  </span>
                  {topic && (
                    <span className="badge bg-brand-50 text-brand-700 ml-auto">
                      {topic.title.slice(0, 30)}…
                    </span>
                  )}
                </div>
                <p className="text-sm text-gray-700 whitespace-pre-line mb-3 leading-relaxed">
                  {post.caption}
                </p>
                <div className="flex flex-wrap gap-1">
                  {post.hashtags.map((ht) => (
                    <span key={ht} className="badge bg-gray-100 text-gray-600">
                      {ht}
                    </span>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
