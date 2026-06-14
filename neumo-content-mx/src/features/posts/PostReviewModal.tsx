import { format } from 'date-fns';
import { es } from 'date-fns/locale';
import type { Post, Doctor } from '../../types';
import type { ComplianceResult } from '../../lib/compliance/checker';

interface PostReviewModalProps {
  post: Post;
  doctor: Doctor;
  compliance: ComplianceResult;
  onApprove: (signedPost: Post) => void;
  onReject: () => void;
  onClose: () => void;
}

const scoreColor = (score: number) =>
  score >= 80 ? 'bg-green-100 text-green-700' : score >= 50 ? 'bg-yellow-100 text-yellow-700' : 'bg-red-100 text-red-700';
const scoreIcon = (score: number) => (score >= 80 ? '🟢' : score >= 50 ? '🟡' : '🔴');
const scoreLabel = (score: number) =>
  score >= 80 ? 'Cumplimiento alto' : score >= 50 ? 'Revisar advertencias' : 'Bloqueado para aprobación';
const severityIcon: Record<string, string> = { ok: '✅', warning: '⚠️', error: '❌' };

const isPortrait = (post: Post) =>
  post.platform === 'tiktok' || post.contentType === 'historia' || post.contentType === 'reels';

export default function PostReviewModal({
  post,
  doctor,
  compliance,
  onApprove,
  onReject,
  onClose,
}: PostReviewModalProps) {
  const now = new Date();
  const approvedBy = `${doctor.name} — Cédula Profesional: ${doctor.cedula}`;
  const approvedAt = now.toISOString();
  const dateLabel = format(now, "d 'de' MMMM 'de' yyyy, HH:mm", { locale: es });

  function handleApprove() {
    onApprove({ ...post, status: 'aprobado', approvedBy, approvedAt });
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />

      {/* Modal */}
      <div className="relative bg-white rounded-2xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="sticky top-0 bg-white border-b border-gray-100 px-6 py-4 flex items-center justify-between">
          <h2 className="text-base font-semibold text-gray-900">Revisión de publicación</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl leading-none">×</button>
        </div>

        <div className="p-6 space-y-6">
          {/* Vista previa */}
          <div>
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">Vista previa · {post.platform}</p>
            <div className="border border-gray-200 rounded-xl overflow-hidden">
              {/* Header de perfil */}
              <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-100">
                <div className="w-9 h-9 rounded-full bg-brand-600 flex items-center justify-center text-white text-sm font-bold shrink-0">
                  {doctor.name.charAt(0)}
                </div>
                <div>
                  <p className="text-sm font-semibold text-gray-900">{doctor.name}</p>
                  <p className="text-xs text-gray-400">{doctor.specialty} · {doctor.location}</p>
                </div>
              </div>

              {/* Imagen */}
              {post.imageUrl && (
                <img
                  src={post.imageUrl}
                  alt="Imagen generada"
                  className={`w-full object-cover ${isPortrait(post) ? 'aspect-[9/16]' : 'aspect-square'}`}
                />
              )}

              {/* Caption */}
              <div className="px-4 py-3 space-y-2">
                <p className="text-sm text-gray-800 whitespace-pre-line leading-relaxed">{post.caption}</p>
                {post.hashtags && post.hashtags.length > 0 && (
                  <p className="text-sm text-blue-600">{post.hashtags.join(' ')}</p>
                )}
                {post.disclaimer && (
                  <p className="text-xs text-gray-400 border-t border-gray-100 pt-2">{post.disclaimer}</p>
                )}
              </div>
            </div>
          </div>

          {/* Compliance */}
          <div>
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">Revisión de cumplimiento</p>
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

          {/* Firma digital */}
          {compliance.canApprove && (
            <div className="bg-green-50 border border-green-200 rounded-xl px-4 py-3">
              <p className="text-xs text-green-700 mb-1">Al aprobar, este contenido quedará registrado como aprobado por:</p>
              <p className="text-sm font-semibold text-green-800">{approvedBy}</p>
              <p className="text-xs text-green-600 mt-0.5">Fecha: {dateLabel}</p>
            </div>
          )}

          {/* Acciones */}
          {!compliance.canApprove ? (
            <div className="space-y-3">
              <p className="text-sm text-red-600 text-center">
                No se puede aprobar hasta resolver los errores de cumplimiento.
              </p>
              <button
                onClick={onClose}
                className="w-full py-2.5 rounded-lg text-sm font-medium border border-gray-300 text-gray-700 hover:bg-gray-50"
              >
                Cerrar y editar
              </button>
            </div>
          ) : (
            <div className="flex gap-2">
              <button
                onClick={onClose}
                className="py-2.5 px-4 rounded-lg text-sm font-medium border border-gray-300 text-gray-700 hover:bg-gray-50"
              >
                Cerrar
              </button>
              <button
                onClick={onReject}
                className="py-2.5 px-4 rounded-lg text-sm font-medium border border-red-200 text-red-600 hover:bg-red-50"
              >
                Rechazar
              </button>
              <button
                onClick={handleApprove}
                className="flex-1 py-2.5 rounded-lg text-sm font-semibold bg-green-600 text-white hover:bg-green-700"
              >
                ✅ Aprobar y firmar
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
