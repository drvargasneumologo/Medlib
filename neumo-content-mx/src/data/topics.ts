import type { Topic } from '../types';

export const mockTopics: Topic[] = [
  {
    id: 'topic-001',
    title: 'EPOC: qué es y cómo afecta tu vida diaria',
    description:
      'Explicación accesible de la Enfermedad Pulmonar Obstructiva Crónica para pacientes y familiares.',
    category: 'patologia',
    platform: ['instagram'],
    priority: 'alta',
    targetAudience: 'pacientes',
    keywords: ['EPOC', 'bronquitis crónica', 'enfisema', 'disnea'],
    hashtagSetId: 'hs-001',
  },
  {
    id: 'topic-002',
    title: 'Asma en adultos: mitos y realidades',
    description:
      'Desmitificación del asma en la edad adulta; diferencias con EPOC y tratamientos actuales.',
    category: 'patologia',
    platform: ['instagram', 'tiktok'],
    priority: 'alta',
    targetAudience: 'pacientes',
    keywords: ['asma', 'broncoespasmo', 'inhalador', 'alergia respiratoria'],
    hashtagSetId: 'hs-001',
  },
  {
    id: 'topic-003',
    title: '¿Cómo dejar de fumar? Estrategias que funcionan',
    description:
      'Guía práctica basada en evidencia para la cesación tabáquica en la consulta neumológica.',
    category: 'prevencion',
    platform: ['instagram'],
    priority: 'alta',
    targetAudience: 'pacientes',
    keywords: ['tabaquismo', 'cesación', 'vareniclina', 'terapia nicotina'],
    hashtagSetId: 'hs-002',
  },
  {
    id: 'topic-004',
    title: 'Calidad del aire en CDMX y salud respiratoria',
    description:
      'Impacto de la contaminación del aire de la Ciudad de México en pacientes con enfermedades pulmonares.',
    category: 'prevencion',
    platform: ['instagram', 'twitter'],
    priority: 'alta',
    targetAudience: 'general',
    keywords: ['contaminación', 'PM2.5', 'IMECA', 'mascarilla'],
    hashtagSetId: 'hs-002',
  },
  {
    id: 'topic-005',
    title: 'Disnea: cuándo la falta de aire es una emergencia',
    description:
      'Señales de alerta que indican que la dificultad para respirar requiere atención urgente.',
    category: 'sintoma',
    platform: ['instagram', 'tiktok'],
    priority: 'alta',
    targetAudience: 'pacientes',
    keywords: ['disnea', 'falta de aire', 'emergencia', 'saturación'],
    hashtagSetId: 'hs-003',
  },
  {
    id: 'topic-006',
    title: 'Tos crónica: causas más frecuentes',
    description:
      'Diagnóstico diferencial de la tos persistente mayor a 8 semanas en consulta general y especializada.',
    category: 'sintoma',
    platform: ['instagram', 'linkedin'],
    priority: 'media',
    targetAudience: 'medicos',
    keywords: ['tos crónica', 'ERGE', 'goteo retronasal', 'asma variante'],
    hashtagSetId: 'hs-003',
  },
  {
    id: 'topic-007',
    title: 'Espirometría: la prueba básica del pulmón',
    description:
      'Qué es, cómo interpretarla y cuándo solicitarla — guía para médicos no especialistas.',
    category: 'educacion_medica',
    platform: ['linkedin', 'twitter'],
    priority: 'media',
    targetAudience: 'medicos',
    keywords: ['espirometría', 'FEV1', 'CVF', 'obstrucción', 'restricción'],
    hashtagSetId: 'hs-004',
  },
  {
    id: 'topic-008',
    title: 'Actualización en tratamiento de asma severa',
    description:
      'Biológicos disponibles en México para asma severa no controlada: omalizumab, mepolizumab, dupilumab.',
    category: 'educacion_medica',
    platform: ['linkedin', 'twitter'],
    priority: 'media',
    targetAudience: 'medicos',
    keywords: ['asma severa', 'biológicos', 'omalizumab', 'dupilumab', 'COFEPRIS'],
    hashtagSetId: 'hs-004',
  },
  {
    id: 'topic-009',
    title: '5 ejercicios para mejorar tu capacidad pulmonar',
    description:
      'Rehabilitación pulmonar en casa: técnicas de respiración y actividad física adaptada.',
    category: 'prevencion',
    platform: ['tiktok', 'instagram'],
    priority: 'media',
    targetAudience: 'pacientes',
    keywords: ['rehabilitación pulmonar', 'ejercicio', 'capacidad respiratoria'],
    hashtagSetId: 'hs-005',
  },
  {
    id: 'topic-010',
    title: 'Neumonía por COVID-19 vs neumonía bacteriana',
    description:
      'Diferencias clínicas, radiológicas y de manejo entre neumonía viral y bacteriana post-pandemia.',
    category: 'educacion_medica',
    platform: ['linkedin', 'twitter'],
    priority: 'baja',
    targetAudience: 'medicos',
    keywords: ['neumonía', 'COVID-19', 'bacteriana', 'tomografía', 'antibiótico'],
    hashtagSetId: 'hs-004',
  },
];
