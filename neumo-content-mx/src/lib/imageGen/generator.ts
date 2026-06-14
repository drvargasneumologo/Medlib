import type { Platform, ContentType } from '../../types';

export interface ImageGenParams {
  topic: { title: string; description: string; category: string };
  platform: Platform;
  contentType: ContentType;
  style?: 'profesional' | 'educativo' | 'ilustrativo';
}

export interface ImageGenResult {
  imageUrl: string;
  prompt: string;
}

export class ImageGenError extends Error {}

function buildImagePrompt(params: ImageGenParams): string {
  const base =
    `Premium professional medical illustration for a pulmonology social media post about ${params.topic.title}. ` +
    `Clean, sober, modern clinical aesthetic — single clear focal point with generous negative space, ` +
    `NOT a busy collage or multiple vignettes. ` +
    `Color palette: medical blue, white, soft gray, medical teal/green (matching a #2e80fa and #319dac brand palette). ` +
    `No exaggerated cartoon characters, no blood, no dramatic hospital scenes, no identifiable human faces. ` +
    `May depict calm imagery of: lung/airway anatomy, inhaler device, spirometer, pulse oximeter, ` +
    `or a serene doctor-patient consultation (no visible faces). ` +
    `No text, no words, no labels, no logos — text is added separately in post-production.`;

  const styleDesc =
    params.style === 'educativo'
      ? 'Style: clean flat vector diagram, minimal line work, infographic-style anatomy illustration, like a modern medical textbook.'
      : params.style === 'ilustrativo'
        ? 'Style: elegant minimalist line-art or soft watercolor illustration, calming and refined.'
        : 'Style: realistic medical photography or clean 3D render, soft studio lighting, premium healthcare brand feel.';

  return `${base} ${styleDesc}`;
}

function isPortrait(params: ImageGenParams): boolean {
  return params.platform === 'tiktok' || params.contentType === 'historia' || params.contentType === 'reels';
}

export async function generatePostImage(params: ImageGenParams): Promise<ImageGenResult> {
  const key = import.meta.env.VITE_OPENAI_KEY;
  if (!key) throw new ImageGenError('Configura tu clave de OpenAI en .env.local para generar imágenes');

  const prompt = buildImagePrompt(params);
  const size = isPortrait(params) ? '1024x1536' : '1024x1024';

  let res: Response;
  try {
    res = await fetch('https://api.openai.com/v1/images/generations', {
      method: 'POST',
      headers: { Authorization: `Bearer ${key}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ model: 'gpt-image-1', prompt, size, n: 1 }),
    });
  } catch {
    throw new ImageGenError('No se pudo generar la imagen. Verifica tu conexión e intenta de nuevo.');
  }

  if (!res.ok) {
    let body: { error?: { message?: string; code?: string } } = {};
    try { body = await res.json(); } catch { /* respuesta no es JSON válido */ }
    const apiMsg = body?.error?.message ?? '';
    const apiCode = body?.error?.code ?? '';
    if (res.status === 400 && apiMsg.includes('content_policy')) {
      throw new ImageGenError('El tema generó una imagen no permitida por políticas de OpenAI. Intenta con un estilo diferente.');
    }
    const parts: string[] = [`No se pudo generar la imagen (código ${res.status}).`];
    if (apiCode) parts.push(`Código OpenAI: ${apiCode}.`);
    if (apiMsg) parts.push(`Detalle: ${apiMsg}`);
    throw new ImageGenError(parts.join(' '));
  }

  let data: { data: { b64_json: string }[] };
  try {
    data = await res.json();
    const base64 = data.data[0].b64_json;
    const imageUrl = `data:image/png;base64,${base64}`;
    return { imageUrl, prompt };
  } catch {
    throw new ImageGenError('Respuesta inesperada de gpt-image-1. Intenta de nuevo.');
  }
}
