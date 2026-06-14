import type { ComplianceFlag, Platform } from '../../types';

export interface ComplianceResult {
  score: number;
  flags: ComplianceFlag[];
  canApprove: boolean;
}

export function runCompliance(params: {
  caption: string;
  hashtags: string[];
  disclaimer: string;
  platform: Platform;
}): ComplianceResult {
  const { caption, hashtags, disclaimer, platform } = params;
  let score = 100;
  const flags: ComplianceFlag[] = [];

  // --- ERRORES (-30 cada uno) ---

  if (
    /cura\s+(garantizada|definitiva|total)/i.test(caption) ||
    /elimina(r)?\s+para\s+siempre/i.test(caption) ||
    /tratamiento\s+definitivo/i.test(caption) ||
    /100%\s+efectivo/i.test(caption)
  ) {
    score -= 30;
    flags.push({ severity: 'error', message: 'El texto contiene una promesa de cura no permitida (NOM-004/COFEPRIS)' });
  }

  if (/\$\s?\d+|\bMXN\b|\bpesos\b/i.test(caption)) {
    score -= 30;
    flags.push({ severity: 'error', message: 'El texto menciona precios o montos — no permitido en contenido educativo' });
  }

  if (/\b(tienes|padeces|sufres de|usted tiene)\b/i.test(caption)) {
    score -= 30;
    flags.push({ severity: 'error', message: 'El texto diagnostica directamente al lector — riesgo ético/legal' });
  }

  if (disclaimer.trim().length === 0) {
    score -= 30;
    flags.push({ severity: 'error', message: 'Falta el disclaimer médico obligatorio' });
  } else if (!/[Cc]édula/.test(disclaimer)) {
    score -= 30;
    flags.push({ severity: 'error', message: 'El disclaimer no incluye la cédula profesional' });
  }

  // --- ADVERTENCIAS (-10 cada una) ---

  const wordCount = caption.trim().split(/\s+/).length;
  if ((platform === 'instagram' || platform === 'twitter') && wordCount > 300) {
    score -= 10;
    flags.push({ severity: 'warning', message: `El texto excede la longitud recomendada para ${platform}` });
  }

  if (platform === 'twitter') {
    const lines = caption.split('\n');
    if (lines.some((l) => l.length > 280)) {
      score -= 10;
      flags.push({ severity: 'warning', message: `El texto excede la longitud recomendada para ${platform}` });
    }
  }

  if (hashtags.length < 3 || hashtags.length > 10) {
    score -= 10;
    flags.push({ severity: 'warning', message: 'Número de hashtags fuera del rango recomendado (3-10)' });
  }

  if (
    /\b(salbutamol|budesonida|formoterol|tiotropio|prednisona)\b/i.test(caption) &&
    !/prescripci[oó]n|indicaci[oó]n m[eé]dica/i.test(caption)
  ) {
    score -= 10;
    flags.push({ severity: 'warning', message: 'Se menciona un medicamento sin indicar que requiere prescripción médica' });
  }

  // --- OK flags ---

  if (disclaimer.trim().length > 0) {
    flags.push({ severity: 'ok', message: 'Disclaimer presente y completo' });
  }
  if (/[Cc]édula/.test(disclaimer)) {
    flags.push({ severity: 'ok', message: 'Cédula profesional incluida' });
  }
  if (!((platform === 'instagram' || platform === 'twitter') && wordCount > 300)) {
    flags.push({ severity: 'ok', message: 'Longitud apropiada para la plataforma' });
  }
  if (hashtags.length >= 3 && hashtags.length <= 10) {
    flags.push({ severity: 'ok', message: 'Hashtags en rango recomendado' });
  }

  score = Math.max(0, score);
  const canApprove = score >= 70 && !flags.some((f) => f.severity === 'error');

  return { score, flags, canApprove };
}
