import { useState } from 'react';
import { mockTopics, mockHashtagSets, mockDoctor } from '../../data';
import { useGenerator } from './useGenerator';
import { getDrafts, saveDraft } from '../../lib/storage/posts';
import PostReviewModal from './PostReviewModal';
import type { Platform, ContentType, Post } from '../../types';
import type { AIModel } from '../../lib/ai/client';

const platformIcon: Record<string, string> = {
  instagram: '📸', linkedin: '💼', twitter: '🐦', tiktok: '🎵',
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

const styleOptions = [
  { value: 'profesional' as const, label: '📷 Profesional' },
  { value: 'educativo' as const, label: '📊 Educativo' },
  { value: 'ilustrativo' as const, label: '🎨 Ilustrativo' },
];

const scoreColor = (score: number) =>
  score >= 80 ? 'bg-green-100 text-green-700' : score >= 50 ? 'bg-yellow-100 text-yellow-700' : 'bg-red-100 text-red-700';
const scoreIcon = (score: number) => (score >= 80 ? '🟢' : score >= 50 ? '🟡' : '🔴');
const scoreLabel = (score: number) =>
  score >= 80 ? 'Cumplimiento alto' : score >= 50 ? 'Revisar advertencias' : 'Bloqueado para aprobación';
const severityIcon: Record<string, string> = { ok: '✅', warning: '⚠️', error: '❌' };

const isPortraitPlatform = (platform: Platform, contentType: ContentType) =>
  platform === 'tiktok' || contentType === 'historia' || contentType === 'reels';

export default function GeneratorView() {
  const [selectedTopicId, setSelectedTopicId] = useState('');
  const [selectedPlatform, setSelectedPlatform] = useState<Platform>('instagram');
  const [selectedType, setSelectedType] = useState<ContentType>('post_imagen');
  const [selectedModel, setSelectedModel] = useState<AIModel>('claude');
  const [selectedStyle, setSelectedStyle] = useState<'profesional' | 'educativo' | 'ilustrativo'>('educativo');
  const [newHashtag, setNewHashtag] = useState('');
  const [reviewPost, setReviewPost] = useState<Post | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [drafts, setDrafts] = useState(() => getDrafts());

  const { loading, error, output, compliance, generate, updateCaption, updateHashtags, reset,
    imageLoading, imageError, imageResult, generateImage } = useGenerator();

  const selectedTopic = mockTopics.find((t) => t.id === selectedTopicId);
  const suggestedHashtagSet = selectedTopic?.hashtagSetId
    ? mockHashtagSets.find((hs) => hs.id === selectedTopic.hashtagSetId)
    : undefined;

  function handleGenerate() {
    if (!selectedTopic) return;
    reset();
    setSuccessMsg(null);
    generate({
      topic: selectedTopic, platform: selectedPlatform, contentType: selectedType,
      model: selectedModel, doctor: mockDoctor, hashtagSet: suggestedHashtagSet,
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

  function handleGenerateImage() {
    if (!selectedTopic) return;
    generateImage({ topic: selectedTopic, platform: selectedPlatform, contentType: selectedType, style: selectedStyle });
  }

  function handleSendToReview() {
    if (!output || !compliance || !selectedTopic) return;
    const post: Post = {
      id: crypto.randomUUID(),
      topicId: selectedTopic.id,
      platform: selectedPlatform,
      caption: output.caption,
      hashtags: output.hashtags,
      disclaimer: output.disclaimer,
      contentType: selectedType,
      aiModel: selectedModel,
      createdAt: new Date().toISOString(),
      status: 'en_revision',
      complianceFlags: compliance.flags,
      imageUrl: imageResult?.imageUrl,
      imagePrompt: imageResult?.prompt,
    };
    saveDraft(post);
    setReviewPost(post);
  }

  function handleApprove(signedPost: Post) {
    saveDraft(signedPost);
    setReviewPost(null);
    setSuccessMsg('Publicación aprobada y guardada. Ve a Calendario para programarla.');
    setDrafts(getDrafts());
  }

  function handleReject() {
    if (!reviewPost) return;
    saveDraft({ ...reviewPost, status: 'rechazado' });
    setReviewPost(null);
    setSuccessMsg('Publicación rechazada. Puedes regenerar desde el panel izquierdo.');
    setDrafts(getDrafts());
  }

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-1">Generador de contenido</h1>
      <p className="text-gray-500 mb-6">Crea posts con IA optimizados para cada red social</p>

      {successMsg && (
        <div className="mb-4 bg-green-50 border border-green-200 rounded-xl px-4 py-3 text-sm text-green-700 flex items-center justify-between">
          <span>✅ {successMsg}</span>
          <button onClick={() => setSuccessMsg(null)} className="text-green-400 hover:text-green-600 ml-4">×</button>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Panel izquierdo */}
        <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm space-y-4">
          <h2 className="text-base font-semibold text-gray-800">Configuración</h2>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Tema</label>
            <select value={selectedTopicId}
              onChange={(e) => { setSelectedTopicId(e.target.value); reset(); setSuccessMsg(null); }}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500">
              <option value="">— Selecciona un tema —</option>
              {mockTopics.map((t) => <option key={t.id} value={t.id}>{t.title}</option>)}
            </select>
          </div>

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
              {suggestedHashtagSet.notes && <p className="text-xs text-brand-600 mt-2 italic">{suggestedHashtagSet.notes}</p>}
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Plataforma</label>
            <select value={selectedPlatform} onChange={(e) => setSelectedPlatform(e.target.value as Platform)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500">
              {(['instagram', 'twitter', 'linkedin', 'tiktok'] as Platform[]).map((p) => (
                <option key={p} value={p}>{platformIcon[p]} {p}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Tipo de contenido</label>
            <select value={selectedType} onChange={(e) => setSelectedType(e.target.value as ContentType)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500">
              {contentTypeOptions.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Modelo de IA</label>
            <select value={selectedModel} onChange={(e) => setSelectedModel(e.target.value as AIModel)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500">
              {modelOptions.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </div>

          <button onClick={handleGenerate} disabled={!selectedTopicId || loading}
            className="w-full py-2.5 rounded-lg text-sm font-semibold bg-brand-600 text-white hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors">
            {loading ? `Generando con ${selectedModel}...` : '✨ Generar con IA'}
          </button>
        </div>

        {/* Panel derecho */}
        <div className="space-y-4">
          {loading && (
            <div className="bg-white rounded-xl border border-gray-200 p-8 shadow-sm flex flex-col items-center justify-center gap-3">
              <div className="w-8 h-8 border-4 border-brand-500 border-t-transparent rounded-full animate-spin" />
              <p className="text-sm text-gray-500">Generando con {selectedModel}...</p>
            </div>
          )}

          {!loading && error && (
            <div className="bg-red-50 border border-red-200 rounded-xl p-4">
              <p className="text-sm font-semibold text-red-700 mb-1">Error al generar</p>
              <p className="text-sm text-red-600">{error}</p>
              <button onClick={handleGenerate} className="mt-3 text-sm font-medium text-red-700 underline hover:no-underline">
                Reintentar
              </button>
            </div>
          )}

          {!loading && !error && output && compliance && (
            <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm space-y-4">
              <h2 className="text-base font-semibold text-gray-800">Contenido generado</h2>

              {/* Caption */}
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Caption</label>
                <textarea value={output.caption} onChange={(e) => updateCaption(e.target.value)}
                  rows={8}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 resize-y" />
              </div>

              {/* Hashtags */}
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Hashtags</label>
                <div className="flex flex-wrap gap-1 mb-2">
                  {output.hashtags.map((ht) => (
                    <span key={ht} className="badge bg-brand-50 text-brand-700 border border-brand-200">
                      {ht}
                      <button onClick={() => handleRemoveHashtag(ht)} className="ml-1 text-brand-400 hover:text-brand-700">×</button>
                    </span>
                  ))}
                </div>
                <div className="flex gap-2">
                  <input value={newHashtag} onChange={(e) => setNewHashtag(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleAddHashtag()}
                    placeholder="#NuevoHashtag"
                    className="flex-1 border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" />
                  <button onClick={handleAddHashtag} className="px-3 py-1.5 bg-gray-100 text-gray-700 rounded-lg text-sm hover:bg-gray-200">
                    + Agregar
                  </button>
                </div>
              </div>

              {/* Disclaimer */}
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Disclaimer</label>
                <div className="bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 text-xs text-gray-600 leading-relaxed">
                  {output.disclaimer || <span className="text-red-400">Sin disclaimer — regenera el contenido</span>}
                </div>
              </div>

              {/* Imagen del post */}
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Imagen del post</label>
                <div className="flex gap-2 mb-3">
                  {styleOptions.map((s) => (
                    <button key={s.value}
                      onClick={() => setSelectedStyle(s.value)}
                      className={`flex-1 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                        selectedStyle === s.value
                          ? 'bg-brand-600 text-white border-brand-600'
                          : 'border-gray-300 text-gray-700 hover:bg-gray-50'
                      }`}>
                      {s.label}
                    </button>
                  ))}
                </div>
                <button onClick={handleGenerateImage} disabled={imageLoading}
                  className="w-full py-2 rounded-lg text-sm font-medium border border-brand-300 text-brand-700 hover:bg-brand-50 disabled:opacity-50 transition-colors">
                  {imageLoading ? 'Generando imagen con DALL-E...' : '🖼️ Generar imagen'}
                </button>
                {imageLoading && (
                  <div className="flex items-center justify-center gap-2 mt-3 text-sm text-gray-500">
                    <div className="w-4 h-4 border-2 border-brand-400 border-t-transparent rounded-full animate-spin" />
                    Generando imagen con DALL-E...
                  </div>
                )}
                {imageError && (
                  <div className="mt-2 bg-red-50 border border-red-200 rounded-lg p-3 text-xs text-red-600">
                    {imageError}
                    <button onClick={handleGenerateImage} className="ml-2 underline">Reintentar</button>
                  </div>
                )}
                {imageResult && !imageLoading && (
                  <div className="mt-3">
                    <img src={imageResult.imageUrl} alt="Imagen generada"
                      className={`w-full max-w-xs mx-auto rounded-lg object-cover ${
                        isPortraitPlatform(selectedPlatform, selectedType) ? 'aspect-[9/16]' : 'aspect-square'
                      }`} />
                    <button onClick={handleGenerateImage}
                      className="mt-2 w-full text-xs text-gray-500 underline hover:text-gray-700">
                      🔄 Regenerar imagen
                    </button>
                  </div>
                )}
              </div>

              {/* Compliance */}
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

              {/* Acciones */}
              <div className="flex gap-2 pt-2 border-t border-gray-100">
                <button onClick={handleGenerate}
                  className="flex-1 py-2 rounded-lg text-sm font-medium border border-gray-300 text-gray-700 hover:bg-gray-50 transition-colors">
                  🔄 Regenerar
                </button>
                <button disabled={!compliance.canApprove} onClick={handleSendToReview}
                  className="flex-1 py-2 rounded-lg text-sm font-semibold bg-green-600 text-white hover:bg-green-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors">
                  ✅ Enviar a revisión
                </button>
              </div>
            </div>
          )}

          {/* Posts existentes — solo sin output */}
          {!loading && !error && !output && (
            <>
              <h2 className="text-base font-semibold text-gray-800">Posts recientes</h2>
              {drafts.slice(0, 5).map((post) => {
                const topic = mockTopics.find((t) => t.id === post.topicId);
                return (
                  <div key={post.id} className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-lg">{platformIcon[post.platform]}</span>
                      <span className="text-xs font-medium text-gray-500 uppercase">{post.platform}</span>
                      {post.status && (
                        <span className="badge bg-gray-100 text-gray-500">{post.status}</span>
                      )}
                      {topic && (
                        <span className="badge bg-brand-50 text-brand-700 ml-auto">
                          {topic.title.slice(0, 28)}…
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-gray-700 whitespace-pre-line mb-3 leading-relaxed line-clamp-4">
                      {post.caption}
                    </p>
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

      {/* Modal de revisión */}
      {reviewPost && compliance && (
        <PostReviewModal
          post={reviewPost}
          doctor={mockDoctor}
          compliance={compliance}
          onApprove={handleApprove}
          onReject={handleReject}
          onClose={() => setReviewPost(null)}
        />
      )}
    </div>
  );
}
