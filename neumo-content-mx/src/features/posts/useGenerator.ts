import { useState, useRef } from 'react';
import { generateContent, AIError, type AIModel } from '../../lib/ai/client';
import { buildMedicalPrompt } from '../../lib/ai/prompts';
import { parseAIOutput, type ParsedAIOutput } from '../../lib/ai/parser';
import { runCompliance, type ComplianceResult } from '../../lib/compliance/checker';
import type { Topic, Platform, ContentType, Doctor, HashtagSet } from '../../types';

interface GenerateParams {
  topic: Topic;
  platform: Platform;
  contentType: ContentType;
  model: AIModel;
  doctor: Doctor;
  hashtagSet?: HashtagSet;
}

interface UseGeneratorResult {
  loading: boolean;
  error: string | null;
  output: ParsedAIOutput | null;
  compliance: ComplianceResult | null;
  generate: (params: GenerateParams) => Promise<void>;
  updateCaption: (newCaption: string) => void;
  updateHashtags: (newHashtags: string[]) => void;
  reset: () => void;
}

export function useGenerator(): UseGeneratorResult {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [output, setOutput] = useState<ParsedAIOutput | null>(null);
  const [compliance, setCompliance] = useState<ComplianceResult | null>(null);
  const lastPlatformRef = useRef<Platform>('instagram');
  const lastParamsRef = useRef<GenerateParams | null>(null);

  async function generate(params: GenerateParams) {
    setLoading(true);
    setError(null);
    lastPlatformRef.current = params.platform;
    lastParamsRef.current = params;
    try {
      const { system, user } = buildMedicalPrompt(params);
      const result = await generateContent({ model: params.model, systemPrompt: system, userPrompt: user });
      const parsed = parseAIOutput(result.text);
      setOutput(parsed);
      setCompliance(
        runCompliance({
          caption: parsed.caption,
          hashtags: parsed.hashtags,
          disclaimer: parsed.disclaimer,
          platform: params.platform,
        }),
      );
    } catch (e) {
      if (e instanceof AIError) {
        setError(e.message);
      } else {
        setError('Error inesperado al generar el contenido. Intenta de nuevo.');
      }
    } finally {
      setLoading(false);
    }
  }

  function updateCaption(newCaption: string) {
    if (!output) return;
    const updated = { ...output, caption: newCaption };
    setOutput(updated);
    setCompliance(
      runCompliance({
        caption: newCaption,
        hashtags: updated.hashtags,
        disclaimer: updated.disclaimer,
        platform: lastPlatformRef.current,
      }),
    );
  }

  function updateHashtags(newHashtags: string[]) {
    if (!output) return;
    const updated = { ...output, hashtags: newHashtags };
    setOutput(updated);
    setCompliance(
      runCompliance({
        caption: updated.caption,
        hashtags: newHashtags,
        disclaimer: updated.disclaimer,
        platform: lastPlatformRef.current,
      }),
    );
  }

  function reset() {
    setOutput(null);
    setCompliance(null);
    setError(null);
    lastParamsRef.current = null;
  }

  return { loading, error, output, compliance, generate, updateCaption, updateHashtags, reset };
}
