export type TopicCategory =
  | 'patologia'
  | 'prevencion'
  | 'sintoma'
  | 'educacion_medica';

export type Platform = 'instagram' | 'twitter' | 'linkedin' | 'tiktok';

export type Priority = 'alta' | 'media' | 'baja';

export type TargetAudience = 'pacientes' | 'medicos' | 'general';

export interface Topic {
  id: string;
  title: string;
  description: string;
  category: TopicCategory;
  platform: Platform[];
  priority: Priority;
  targetAudience: TargetAudience;
  keywords: string[];
  hashtagSetId?: string;
}

export interface Post {
  id: string;
  topicId: string;
  platform: Platform;
  caption: string;
  hashtags: string[];
  createdAt: string;
}

// Banco de hashtags validados (v2)
export interface HashtagSet {
  id: string;
  category: TopicCategory;
  platform: Platform;
  hashtags: string[];
  notes?: string;
}
