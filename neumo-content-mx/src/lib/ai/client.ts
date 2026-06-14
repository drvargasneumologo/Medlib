export type AIModel = 'claude' | 'gemini' | 'chatgpt';

export interface GenerateParams {
  model: AIModel;
  systemPrompt: string;
  userPrompt: string;
}

export interface GenerateResult {
  text: string;
  model: AIModel;
}

export class AIError extends Error {
  model: AIModel;
  constructor(model: AIModel, message: string) {
    super(message);
    this.model = model;
    this.name = 'AIError';
  }
}

export async function generateContent(params: GenerateParams): Promise<GenerateResult> {
  const { model, systemPrompt, userPrompt } = params;

  if (model === 'claude') {
    const key = import.meta.env.VITE_ANTHROPIC_KEY;
    if (!key) throw new AIError('claude', 'Falta configurar la clave de Claude en .env.local');

    let data: unknown;
    try {
      const res = await fetch('https://api.anthropic.com/v1/messages', {
        method: 'POST',
        headers: {
          'x-api-key': key,
          'anthropic-version': '2023-06-01',
          'content-type': 'application/json',
          'anthropic-dangerous-direct-browser-access': 'true',
        },
        body: JSON.stringify({
          model: 'claude-sonnet-4-6',
          max_tokens: 1200,
          system: systemPrompt,
          messages: [{ role: 'user', content: userPrompt }],
        }),
      });
      if (!res.ok) throw new AIError('claude', `No se pudo conectar con Claude (código ${res.status}). Verifica tu API key.`);
      data = await res.json();
    } catch (e) {
      if (e instanceof AIError) throw e;
      throw new AIError('claude', 'Respuesta inesperada de Claude. Intenta de nuevo.');
    }
    try {
      const text = (data as { content: { text: string }[] }).content[0].text;
      return { text, model };
    } catch {
      throw new AIError('claude', 'Respuesta inesperada de Claude. Intenta de nuevo.');
    }
  }

  if (model === 'gemini') {
    const key = import.meta.env.VITE_GEMINI_KEY;
    if (!key) throw new AIError('gemini', 'Falta configurar la clave de Gemini en .env.local');

    let data: unknown;
    try {
      const res = await fetch(
        `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${key}`,
        {
          method: 'POST',
          headers: { 'content-type': 'application/json' },
          body: JSON.stringify({
            contents: [{ parts: [{ text: systemPrompt + '\n\n' + userPrompt }] }],
          }),
        },
      );
      if (!res.ok) throw new AIError('gemini', `No se pudo conectar con Gemini (código ${res.status}). Verifica tu API key.`);
      data = await res.json();
    } catch (e) {
      if (e instanceof AIError) throw e;
      throw new AIError('gemini', 'Respuesta inesperada de Gemini. Intenta de nuevo.');
    }
    try {
      const text = (data as { candidates: { content: { parts: { text: string }[] } }[] })
        .candidates[0].content.parts[0].text;
      return { text, model };
    } catch {
      throw new AIError('gemini', 'Respuesta inesperada de Gemini. Intenta de nuevo.');
    }
  }

  if (model === 'chatgpt') {
    const key = import.meta.env.VITE_OPENAI_KEY;
    if (!key) throw new AIError('chatgpt', 'Falta configurar la clave de ChatGPT en .env.local');

    let data: unknown;
    try {
      const res = await fetch('https://api.openai.com/v1/chat/completions', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${key}`,
          'content-type': 'application/json',
        },
        body: JSON.stringify({
          model: 'gpt-4o-mini',
          messages: [
            { role: 'system', content: systemPrompt },
            { role: 'user', content: userPrompt },
          ],
          max_tokens: 1200,
        }),
      });
      if (!res.ok) throw new AIError('chatgpt', `No se pudo conectar con ChatGPT (código ${res.status}). Verifica tu API key.`);
      data = await res.json();
    } catch (e) {
      if (e instanceof AIError) throw e;
      throw new AIError('chatgpt', 'Respuesta inesperada de ChatGPT. Intenta de nuevo.');
    }
    try {
      const text = (data as { choices: { message: { content: string } }[] }).choices[0].message.content;
      return { text, model };
    } catch {
      throw new AIError('chatgpt', 'Respuesta inesperada de ChatGPT. Intenta de nuevo.');
    }
  }

  throw new AIError(model, 'Modelo no reconocido');
}
