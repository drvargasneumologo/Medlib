import type { Topic, Platform, ContentType, Doctor, HashtagSet } from '../../types';

const FORMAT_EXAMPLE = `
Formato de salida OBLIGATORIO — respeta EXACTAMENTE estos marcadores:

[CAPTION]
(texto del post aquí, sin los marcadores)

[HASHTAGS]
#hashtag1 #hashtag2 #hashtag3 #hashtag4 #hashtag5

[DISCLAIMER]
Este contenido tiene fines informativos y de educación para la salud. No sustituye la consulta médica. Dr. Nombre — Cédula Profesional: 0000000 | Cédula Especialidad: 0000000
`;

function formatSpec(platform: Platform, contentType: ContentType): string {
  if (contentType === 'reels' || platform === 'tiktok') {
    return 'Escribe un GUIÓN con esta estructura:\n- GANCHO (3s): frase de impacto para detener el scroll\n- CONTENIDO (40-45s): información médica clave en viñetas cortas\n- CIERRE-CTA (5-7s): llamada a la acción y dónde acudir';
  }
  if (contentType === 'hilo_twitter' || platform === 'twitter') {
    return 'Escribe un HILO de 5-7 tweets, numerados (1/7, 2/7, etc.), cada uno de MÁXIMO 280 caracteres, separados por doble salto de línea.';
  }
  if (contentType === 'articulo_linkedin' || platform === 'linkedin') {
    return 'Escribe un artículo profesional de 250-400 palabras, tono técnico-académico, con subencabezados si corresponde.';
  }
  if (contentType === 'historia') {
    return 'Caption de 60-100 palabras, muy directo y con una sola idea, pensado para Story (se lee en 5 segundos).';
  }
  if (contentType === 'carrusel') {
    return 'Caption de 150-200 palabras que complemente un carrusel de imágenes. Introduce el tema y anima a deslizar.';
  }
  // post_imagen o default instagram/facebook
  return 'Caption de 120-200 palabras, conversacional, con emojis moderados y una llamada a la acción clara al final.';
}

export function buildMedicalPrompt(params: {
  topic: Topic;
  platform: Platform;
  contentType: ContentType;
  doctor: Doctor;
  hashtagSet?: HashtagSet;
}): { system: string; user: string } {
  const { topic, platform, contentType, doctor, hashtagSet } = params;

  const system = `Eres un experto en comunicación médica para un neumólogo mexicano certificado, especializado en contenido educativo para redes sociales.

PROHIBICIONES ABSOLUTAS (violación bloquea la publicación):
- NO prometer curas: nunca uses "cura garantizada", "tratamiento definitivo", "elimina para siempre", "100% efectivo".
- NO mencionar precios, costos, ni cifras en pesos/MXN/$.
- NO diagnosticar al lector directamente: evita "tú tienes", "padeces de", "seguramente sufres de", "usted tiene".

OBLIGACIONES:
- Contenido educativo basado en evidencia científica.
- Tono empático si la audiencia es "pacientes"; técnico/con referencias si la audiencia es "medicos".
- El contenido DEBE terminar con el bloque [DISCLAIMER] exacto que se especifica abajo, con los datos del médico ya completados.

${FORMAT_EXAMPLE}

El disclaimer de ESTE médico ya completado es:
"Este contenido tiene fines informativos y de educación para la salud. No sustituye la consulta médica. ${doctor.name} — Cédula Profesional: ${doctor.cedula} | Cédula Especialidad: ${doctor.cedulaEspecialidad}"

Usa ese texto exacto en el bloque [DISCLAIMER]. No lo alteres.`;

  const hashtagInstruction = hashtagSet
    ? `Usa estos hashtags como base y complétalos si faltan hasta tener entre 5 y 8 en total, sin inventar hashtags irrelevantes:\n${hashtagSet.hashtags.join(' ')}`
    : 'Genera entre 5 y 8 hashtags relevantes en español para audiencia mexicana de salud respiratoria, sin hashtags genéricos o spam.';

  const audienceNote =
    topic.targetAudience === 'medicos'
      ? 'Audiencia: MÉDICOS (puedes usar terminología técnica, mencionar criterios diagnósticos y guías clínicas).'
      : topic.targetAudience === 'pacientes'
        ? 'Audiencia: PACIENTES (lenguaje claro, empático, sin jerga técnica innecesaria).'
        : 'Audiencia: PÚBLICO GENERAL (lenguaje accesible, informativo, preventivo).';

  const user = `Crea contenido para ${platform.toUpperCase()} — tipo: ${contentType}.

TEMA: ${topic.title}
DESCRIPCIÓN: ${topic.description}
${audienceNote}
PALABRAS CLAVE DE CONTEXTO (no copiar literalmente): ${topic.keywords.join(', ')}

ESPECIFICACIONES DE FORMATO:
${formatSpec(platform, contentType)}

HASHTAGS:
${hashtagInstruction}

Recuerda: respeta el formato [CAPTION] / [HASHTAGS] / [DISCLAIMER] EXACTAMENTE.`;

  return { system, user };
}
