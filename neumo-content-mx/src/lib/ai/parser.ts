export interface ParsedAIOutput {
  caption: string;
  hashtags: string[];
  disclaimer: string;
  raw: string;
}

export function parseAIOutput(rawText: string): ParsedAIOutput {
  const captionMatch = rawText.match(/\[CAPTION\]\s*([\s\S]*?)(?=\[HASHTAGS\]|\[DISCLAIMER\]|$)/i);
  const hashtagsMatch = rawText.match(/\[HASHTAGS\]\s*([\s\S]*?)(?=\[DISCLAIMER\]|$)/i);
  const disclaimerMatch = rawText.match(/\[DISCLAIMER\]\s*([\s\S]*?)$/i);

  if (!captionMatch) {
    return { caption: rawText.trim(), hashtags: [], disclaimer: '', raw: rawText };
  }

  const caption = captionMatch[1].trim();

  const hashtags = hashtagsMatch
    ? hashtagsMatch[1]
        .split(/[\s\n]+/)
        .filter((t) => t.startsWith('#'))
    : [];

  const disclaimer = disclaimerMatch ? disclaimerMatch[1].trim() : '';

  return { caption, hashtags, disclaimer, raw: rawText };
}
