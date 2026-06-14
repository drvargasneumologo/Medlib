import { useState } from 'react';
import { getDrafts, schedulePost, saveDraft } from '../../lib/storage/posts';
import { buildShareText, getShareTweets, copyToClipboard, openPlatform } from '../../lib/share/share';
import type { Post } from '../../types';

const platformIcon: Record<string, string> = {
  instagram: '📸', linkedin: '💼', twitter: '🐦', tiktok: '🎵',
};

function CopiedBadge({ show }: { show: boolean }) {
  return show ? (
    <span className="ml-2 text-xs text-green-600 font-medium animate-pulse">¡Copiado!</span>
  ) : null;
}

export default function CalendarView() {
  const [drafts, setDrafts] = useState(() => getDrafts());
  const [scheduleTimes, setScheduleTimes] = useState<Record<string, string>>({});
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [copiedTweetIdx, setCopiedTweetIdx] = useState<string | null>(null);

  const now = new Date();

  const approved = drafts.filter((p) => p.status === 'aprobado');
  const scheduled = drafts.filter((p) => p.status === 'programado');
  const readyToPublish = scheduled.filter((p) => p.scheduledAt && new Date(p.scheduledAt) <= now);
  const scheduledFuture = scheduled.filter((p) => p.scheduledAt && new Date(p.scheduledAt) > now);

  function refresh() {
    setDrafts(getDrafts());
  }

  function handleSchedule(post: Post) {
    const at = scheduleTimes[post.id];
    if (!at) return;
    schedulePost(post.id, new Date(at).toISOString());
    refresh();
  }

  async function handleCopy(post: Post) {
    const text = buildShareText(
      { caption: post.caption, hashtags: post.hashtags, disclaimer: post.disclaimer ?? '' },
      post.platform,
    );
    await copyToClipboard(text);
    setCopiedId(post.id);
    setTimeout(() => setCopiedId(null), 2000);
  }

  async function handleCopyTweet(_post: Post, tweet: string, key: string) {
    await copyToClipboard(tweet);
    setCopiedTweetIdx(key);
    setTimeout(() => setCopiedTweetIdx(null), 2000);
  }

  function handleOpen(post: Post) {
    const firstTweet = post.platform === 'twitter'
      ? getShareTweets({ caption: post.caption, hashtags: post.hashtags, disclaimer: post.disclaimer ?? '' })[0]
      : undefined;
    openPlatform(post.platform, firstTweet);
  }

  function handleMarkPublished(post: Post) {
    saveDraft({ ...post, status: 'publicado', publishedAt: new Date().toISOString() });
    refresh();
  }

  function PostCard({ post: p, children }: { post: Post; children?: React.ReactNode }) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-lg">{platformIcon[p.platform]}</span>
          <span className="text-xs font-medium text-gray-500 uppercase">{p.platform}</span>
          {p.scheduledAt && (
            <span className="badge bg-blue-50 text-blue-600 ml-auto text-xs">
              🗓 {new Date(p.scheduledAt).toLocaleString('es-MX', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
            </span>
          )}
        </div>
        <p className="text-sm text-gray-700 line-clamp-3 mb-2">{p.caption}</p>
        <div className="flex flex-wrap gap-1 mb-3">
          {p.hashtags.slice(0, 5).map((ht) => (
            <span key={ht} className="badge bg-gray-100 text-gray-500 text-xs">{ht}</span>
          ))}
        </div>
        {children}
      </div>
    );
  }

  function ShareActions({ post }: { post: Post }) {
    const isTwitterThread = post.platform === 'twitter' && post.caption.includes('\n\n');
    const tweets = isTwitterThread
      ? getShareTweets({ caption: post.caption, hashtags: post.hashtags, disclaimer: post.disclaimer ?? '' })
      : [];

    return (
      <div className="space-y-2">
        {post.platform === 'instagram' && (
          <p className="text-xs text-amber-600 bg-amber-50 rounded-lg px-3 py-2">
            ℹ️ Instagram no permite pre-llenar el caption desde el navegador. Copia el contenido, abre Instagram y pégalo al crear tu publicación.
          </p>
        )}

        <div className="flex gap-2 flex-wrap">
          <button onClick={() => handleCopy(post)}
            className="flex-1 py-1.5 rounded-lg text-xs font-medium bg-gray-100 text-gray-700 hover:bg-gray-200 transition-colors">
            📋 Copiar contenido
            <CopiedBadge show={copiedId === post.id} />
          </button>
          <button onClick={() => handleOpen(post)}
            className="flex-1 py-1.5 rounded-lg text-xs font-medium bg-brand-600 text-white hover:bg-brand-700 transition-colors">
            Abrir {post.platform} ↗
          </button>
        </div>

        {isTwitterThread && tweets.length > 0 && (
          <div className="border border-gray-100 rounded-lg p-3 space-y-2">
            <p className="text-xs font-semibold text-gray-500">Hilo de Twitter — copia tweet por tweet:</p>
            {tweets.map((tw, i) => (
              <div key={i} className="flex items-start gap-2">
                <span className="text-xs text-gray-400 shrink-0 mt-1">{i + 1}/{tweets.length}</span>
                <p className="text-xs text-gray-700 flex-1 line-clamp-2">{tw}</p>
                <button onClick={() => handleCopyTweet(post, tw, `${post.id}-${i}`)}
                  className="shrink-0 text-xs px-2 py-1 rounded bg-gray-100 text-gray-600 hover:bg-gray-200">
                  📋
                  <CopiedBadge show={copiedTweetIdx === `${post.id}-${i}`} />
                </button>
              </div>
            ))}
          </div>
        )}

        <button onClick={() => handleMarkPublished(post)}
          className="w-full py-1.5 rounded-lg text-xs font-medium border border-green-300 text-green-700 hover:bg-green-50 transition-colors">
          ✅ Ya publiqué esto
        </button>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-1">Calendario</h1>
      <p className="text-gray-500 mb-8">Programa y publica tu contenido aprobado</p>

      {/* Listos para publicar */}
      {readyToPublish.length > 0 && (
        <section className="mb-8">
          <h2 className="text-base font-semibold text-gray-800 mb-3 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
            Listos para publicar ({readyToPublish.length})
          </h2>
          <div className="grid gap-4 sm:grid-cols-2">
            {readyToPublish.map((post) => (
              <PostCard key={post.id} post={post}>
                <ShareActions post={post} />
              </PostCard>
            ))}
          </div>
        </section>
      )}

      {/* Programados a futuro */}
      {scheduledFuture.length > 0 && (
        <section className="mb-8">
          <h2 className="text-base font-semibold text-gray-800 mb-3">Programados ({scheduledFuture.length})</h2>
          <div className="grid gap-4 sm:grid-cols-2">
            {scheduledFuture.map((post) => (
              <PostCard key={post.id} post={post}>
                <p className="text-xs text-blue-600">
                  Publicación programada para {post.scheduledAt && new Date(post.scheduledAt).toLocaleString('es-MX')}
                </p>
              </PostCard>
            ))}
          </div>
        </section>
      )}

      {/* Listos para programar */}
      {approved.length > 0 && (
        <section className="mb-8">
          <h2 className="text-base font-semibold text-gray-800 mb-3">Listos para programar ({approved.length})</h2>
          <div className="grid gap-4 sm:grid-cols-2">
            {approved.map((post) => (
              <PostCard key={post.id} post={post}>
                <div className="flex gap-2">
                  <input type="datetime-local"
                    value={scheduleTimes[post.id] ?? ''}
                    onChange={(e) => setScheduleTimes((prev) => ({ ...prev, [post.id]: e.target.value }))}
                    className="flex-1 border border-gray-300 rounded-lg px-2 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-brand-500" />
                  <button onClick={() => handleSchedule(post)}
                    disabled={!scheduleTimes[post.id]}
                    className="px-3 py-1.5 bg-brand-600 text-white rounded-lg text-xs font-medium hover:bg-brand-700 disabled:opacity-40 transition-colors">
                    Programar
                  </button>
                </div>
              </PostCard>
            ))}
          </div>
        </section>
      )}

      {approved.length === 0 && readyToPublish.length === 0 && scheduledFuture.length === 0 && (
        <div className="text-center py-20 text-gray-300">
          <p className="text-5xl mb-4">📅</p>
          <p className="text-sm">Aún no tienes publicaciones aprobadas.</p>
          <p className="text-sm">Genera y aprueba contenido desde el Generador.</p>
        </div>
      )}
    </div>
  );
}
