import type { Post } from '../types';

export const mockPosts: Post[] = [
  {
    id: 'post-001',
    topicId: 'topic-001',
    platform: 'instagram',
    caption:
      '¿Sabías que la EPOC afecta a más de 2 millones de mexicanos? 🫁\n\nEs una enfermedad progresiva pero MANEJABLE. El diagnóstico temprano cambia todo.\n\n✅ Si fumas o fumaste por años\n✅ Si tienes tos frecuente con flemas\n✅ Si te falta el aire al caminar\n\n👉 Agenda tu espirometría. Detectar a tiempo salva vidas.\n\n📍 Consulta en CDMX — Link en bio',
    hashtags: [
      '#EPOC',
      '#SaludRespiratoria',
      '#Neumologia',
      '#Mexico',
      '#PulmonesSanos',
      '#RespiraBien',
    ],
    createdAt: '2026-06-01T10:00:00Z',
  },
  {
    id: 'post-002',
    topicId: 'topic-003',
    platform: 'instagram',
    caption:
      'Dejar de fumar es lo MEJOR que puedes hacer por tus pulmones. 🚭\n\nNo es solo fuerza de voluntad — es un proceso médico que tiene tratamiento.\n\n3 opciones que funcionan:\n1️⃣ Terapia de reemplazo de nicotina\n2️⃣ Vareniclina (con receta)\n3️⃣ Apoyo psicológico combinado\n\nCon la guía correcta, el 30% lo logra al primer intento.\n\n¿Ya lo intentaste? Cuéntame en comentarios 👇',
    hashtags: [
      '#DejarDeFumar',
      '#Tabaquismo',
      '#SaludPulmonar',
      '#Prevencion',
      '#Neumologia',
      '#CDMX',
    ],
    createdAt: '2026-06-03T10:00:00Z',
  },
  {
    id: 'post-003',
    topicId: 'topic-007',
    platform: 'linkedin',
    caption:
      'La espirometría sigue siendo la prueba más subutilizada en México. 📊\n\nEn mi consulta, más del 60% de pacientes referidos con "asma" o "EPOC" nunca habían tenido una espirometría confirmada.\n\nClaves para interpretarla correctamente:\n→ FEV1/CVF < 0.70 post-broncodilatador = obstrucción (GOLD)\n→ CVF reducida con FEV1/CVF normal = patrón restrictivo\n→ Siempre post-broncodilatador para diagnóstico definitivo\n\nEl diagnóstico preciso cambia el tratamiento. Comparte con tus colegas.',
    hashtags: [
      '#Espirometria',
      '#Neumologia',
      '#MedicinaInterna',
      '#EducacionMedica',
      '#EPOC',
      '#Mexico',
    ],
    createdAt: '2026-06-05T10:00:00Z',
  },
];
