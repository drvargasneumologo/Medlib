import { useState } from 'react';
import { mockTopics, mockPosts, mockHashtagSets, mockDoctor } from '../../data';
import { useGenerator } from './useGenerator';
import type { Platform, ContentType } from '../../types';
import type { AIModel } from '../../lib/ai/client';

const platformIcon: Record<string, string> = {
  instagram: '📸',
  linkedin: '💼',
  twitter: '🐦',
  tiktok: '🎵',
};

const contentTypeOptions: { value: ContentType; label: string }[] = [
  { value: 'post_imagen', label: 'Post imagen' },
  { value: 'carrusel', label: 'Carrusel' },
  { value: 'historia', label: 'Historia / Story' },
  { value: 'reels', label: 'Reels / Video corto' },
  { value: 'hilo_twitter', label: 'Hilo de Twitter/X' },
  { value: 'articulo_linkedin', label: 'Artículo LinkedIn' },
];

const modelOptions: { value: AIModel; label: string }[] = [
  { value: 'claude', label: '🤖 Claude (Anthropic)' },
  { value: 'gemini', label: '✨ Gemini (Google)' },
  { value: 'chatgpt', label: '💬 ChatGPT (OpenAI)' },
];

const scoreColor = (score: number) =>
  score >= 80 ? 'bg-green-100 text-green-700' : score >= 50 ? 'bg-yellow-100 text-yellow-700' : 'bg-red-100 text-red-700';

const scoreIcon = (score: number) => (score >= 80 ? '🟢' : score >= 50 ? '🟡' : '🔴');
const scoreLabel = (score: number) =>
  score >= 80 ? 'Cumplimiento alto' : score >= 50 ? 'Revisar advertencias' : 'Bloqueado para aprobación';

const severityIcon: Record<string, string> = { ok: '✅', warning: '⚠️', error: '❌' };

export default function GeneratorView() {
  const [selectedTopicId, setSelectedTopicId] = useState('');
  const [selectedPlatform, setSelectedPlatform] = useState<Platform>('instagram');
  const [selectedType, setSelectedType] = useState<ContentType>('post_imagen');
  const [selectedModel, setSelectedModel] = useState<AIModel>('claude');
  const [newHashtag, setNewHashtag] = useState('');
  const [draftSaved, setDraftSaved] = useState(false);

  const { loading, error, output, compliance, generate, updateCaption, updateHashtags, reset } =
    useGenerator();

  const selectedTopic = mockTopics.find((t) => t.id === selectedTopicId);
  const suggestedHashtagSet = selectedTopic?.hashtagSetId
    ? mockHashtagSets.find((hs) => hs.id === selectedTopic.hashtagSetId)
    : undefined;

  function handleGenerate() {
    if (!selectedTopic) return;
    reset();
    setDraftSaved(false);
    generate({
      topic: selectedTopic,
      platform: selectedPlatform,
      contentType: selectedType,
      model: selectedModel,
      doctor: mockDoctor,
      hashtagSet: suggestedHashtagSet,
    });
  }

  function handleAddHashtag() {
    const tag = newHashtag.trim();
    if (!tag || !output) return;
    const normalized = tag.startsWith('#') ? tag : `#${tag}`;
    updateHashtags([...output.hashtags, normalized]);
    setNewHashtag('');
  }

  function handleRemoveHashtag(ht: string) {
    if (!output) return;
    updateHashtags(output.hashtags.filter((h) => h !== ht));
  }

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-1">Generador de contenido</h1>
      <p className="text-gray-500 mb-6">Crea posts con IA optimizados para cada red social</p>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Panel izquierdo — configuración */}
        <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm space-y-4">
          <h2 className="text-base font-semibold text-gray-800">Configuración</h2>

          {/* Tema */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Tema</label>
            <select
              value={selectedTopicId}
              onChange={(e) => { setSelectedTopicId(e.target.value); reset(); setDraftSaved(false); }}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            >
              <option value="">— Selecciona un tema —</option>
              {mockTopics.map((t) => (
                <option key={t.id} value={t.id}>{t.title}</option>
              ))}
            </select>
          </div>

          {/* Hashtags sugeridos */}
          {suggestedHashtagSet && (
            <div className="bg-brand-50 rounded-lg p-3 border border-brand-100">
              <p className="text-xs font-semibold text-brand-700 uppercase tracking-wide mb-2">
                Hashtags sugeridos · {suggestedHashtagSet.platform}
              </p>
              <div className="flex flex-wrap gap-1">
                {suggestedHashtagSet.hashtags.map((ht) => (
                  <span key={ht} className="badge bg-white text-brand-700 border border-brand-200">{ht}</span>
                ))}
              </div>
              {suggestedHashtagSet.notes && (
                <p className="text-xs text-brand-600 mt-2 italic">{suggestedHashtagSet.notes}</p>
              )}
            </div>
          )}

          {/* Plataforma */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Plataforma</label>
            <select
              value={selectedPlatform}
              onChange={(e) => setSelectedPlatform(e.target.value as Platform)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            >
              {(['instagram', 'twitter', 'linkedin', 'tiktok'] as Platform[]).map((p) => (
                <option key={p} value={p}>{platformIcon[p]} {p}</option>
              ))}
            </select>
          </div>

          {/* Tipo de contenido */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Tipo de contenido</label>
            <select
              value={selectedType}
              onChange={(e) => setSelectedType(e.target.value as ContentType)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            >
              {contentTypeOptions.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </div>

          {/* Modelo IA */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Modelo de IA</label>
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value as AIModel)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            >
              {modelOptions.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </div>

          <button
            onClick={handleGenerate}
            disabled={!selectedTopicId || loading}
            className="w-full py-2.5 rounded-lg text-sm font-semibold bg-brand-600 text-white hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? `Generando con ${selectedModel}...` : '✨ Generar con IA'}
          </button>
        </div>

        {/* Panel derecho — resultado o posts existentes */}
        <div className="space-y-4">
          {/* Spinner */}
          {loading && (
            <div className="bg-white rounded-xl border border-gray-200 p-8 shadow-sm flex flex-col items-center justify-center gap-3">
              <div className="w-8 h-8 border-4 border-brand-500 border-t-transparent rounded-full animate-spin" />
              <p className="text-sm text-gray-500">Generando con {selectedModel}...</p>
            </div>
          )}

          {/* Error */}
          {!loading && error && (
            <div className="bg-red-50 border border-red-200 rounded-xl p-4">
              <p className="text-sm font-semibold text-red-700 mb-1">Error al generar</p>
              <p className="text-sm text-red-600">{error}</p>
              <button
                onClick={handleGenerate}
                className="mt-3 text-sm font-medium text-red-700 underline hover:no-underline"
              >
                Reintentar
              </button>
            </div>
          )}

          {/* Output generado */}
          {!loading && !error && output && (
            <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm space-y-4">
              <h2 className="text-base font-semibold text-gray-800">Contenido generado</h2>

              {/* Caption editable */}
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Caption</label>
                <textarea
                  value={output.caption}
                  onChange={(e) => updateCaption(e.target.value)}
                  rows={8}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 resize-y"
                />
              </div>

              {/* Hashtags editables */}
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Hashtags</label>
                <div className="flex flex-wrap gap-1 mb-2">
                  {output.hashtags.map((ht) => (
                    <span key={ht} className="badge bg-brand-50 text-brand-700 border border-brand-200 gap-1">
                      {ht}
                      <button onClick={() => handleRemoveHashtag(ht)} className="ml-1 text-brand-400 hover:text-brand-700">×</button>
                    </span>
                  ))}
                </div>
                <div className="flex gap-2">
                  <input
                    value={newHashtag}
                    onChange={(e) => setNewHashtag(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleAddHashtag()}
                    placeholder="#NuevoHashtag"
                    className="flex-1 border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                  />
                  <button
                    onClick={handleAddHashtag}
                    className="px-3 py-1.5 bg-gray-100 text-gray-700 rounded-lg text-sm hover:bg-gray-200"
                  >
                    + Agregar
                  </button>
                </div>
              </div>

              {/* Disclaimer no editable */}
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Disclaimer</label>
                <div className="bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 text-xs text-gray-600 leading-relaxed">
                  {output.disclaimer || <span className="text-red-400">Sin disclaimer — regenera el contenido</span>}
                </div>
              </div>

              {/* Compliance */}
              {compliance && (
                <div>
                  <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Revisión de cumplimiento</label>
                  <div className={`badge text-sm px-3 py-1.5 mb-3 ${scoreColor(compliance.score)}`}>
                    {scoreIcon(compliance.score)} {scoreLabel(compliance.score)} ({compliance.score}/100)
                  </div>
                  <ul className="space-y-1">
                    {compliance.flags.map((f, i) => (
                      <li key={i} className="flex items-start gap-2 text-xs text-gray-600">
                        <span className="shrink-0 mt-0.5">{severityIcon[f.severity]}</span>
                        {f.message}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Acciones */}
              <div className="flex gap-2 pt-2 border-t border-gray-100">
                <button
                  onClick={handleGenerate}
                  className="flex-1 py-2 rounded-lg text-sm font-medium border border-gray-300 text-gray-700 hover:bg-gray-50 transition-colors"
                >
                  🔄 Regenerar
                </button>
                <button
                  disabled={!compliance?.canApprove}
                  onClick={() => setDraftSaved(true)}
                  className="flex-1 py-2 rounded-lg text-sm font-semibold bg-green-600 text-white hover:bg-green-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                >
                  ✅ Enviar a revisión
                </button>
              </div>
              {draftSaved && (
                <p className="text-xs text-green-600 text-center">
                  Guardado como borrador (localStorage en próximo paso)
                </p>
              )}
            </div>
          )}

          {/* Posts existentes — solo cuando no hay output generado */}
          {!loading && !error && !output && (
            <>
              <h2 className="text-base font-semibold text-gray-800">Posts recientes</h2>
              {mockPosts.map((post) => {
                const topic = mockTopics.find((t) => t.id === post.topicId);
                return (
                  <div key={post.id} className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-lg">{platformIcon[post.platform]}</span>
                      <span className="text-xs font-medium text-gray-500 uppercase">{post.platform}</span>
                      {topic && (
                        <span className="badge bg-brand-50 text-brand-700 ml-auto">
                          {topic.title.slice(0, 30)}…
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-gray-700 whitespace-pre-line mb-3 leading-relaxed">{post.caption}</p>
                    <div className="flex flex-wrap gap-1">
                      {post.hashtags.map((ht) => (
                        <span key={ht} className="badge bg-gray-100 text-gray-600">{ht}</span>
                      ))}
                    </div>
                  </div>
                );
              })}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
