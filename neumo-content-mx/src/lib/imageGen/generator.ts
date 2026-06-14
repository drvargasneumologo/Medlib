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
  const styleDesc =
    params.style === 'educativo'
      ? 'flat vector illustration style, diagram-like'
      : params.style === 'ilustrativo'
        ? 'soft watercolor illustration style'
        : 'realistic medical photography style';

  return (
    `Professional medical illustration about ${params.topic.title}, ` +
    `${styleDesc}, clean minimalist background, soft blue and teal color palette, ` +
    `no text, no words, no labels, no logos, suitable for healthcare social media, ` +
    `respectful and calm tone`
  );
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
