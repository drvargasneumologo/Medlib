import type { Platform } from '../../types';

export interface ShareContent {
  caption: string;
  hashtags: string[];
  disclaimer: string;
}

export function buildShareText(content: ShareContent, platform: Platform): string {
  const { caption, hashtags, disclaimer } = content;
  const tags = hashtags.join(' ');

  if (platform === 'twitter') {
    // For thread format, return only the first tweet
    const tweets = caption.split(/\n\n+/);
    return tweets[0] + (tags ? `\n\n${tags}` : '');
  }
  if (platform === 'linkedin') {
    return `${caption}\n\n${disclaimer}\n\n${tags}`;
  }
  // instagram, facebook, tiktok
  return `${caption}\n\n${tags}\n\n${disclaimer}`;
}

export function getShareTweets(content: ShareContent): string[] {
  const tweets = content.caption.split(/\n\n+/);
  return tweets.map((t, i) => `${i + 1}/${tweets.length} ${t}`);
}

export async function copyToClipboard(text: string): Promise<boolean> {
  if (navigator.clipboard) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch {
      return false;
    }
  }
  // Fallback for non-secure contexts
  try {
    const el = document.createElement('textarea');
    el.value = text;
    el.style.position = 'fixed';
    el.style.opacity = '0';
    document.body.appendChild(el);
    el.focus();
    el.select();
    const ok = document.execCommand('copy');
    document.body.removeChild(el);
    return ok;
  } catch {
    return false;
  }
}

export function getShareUrl(platform: Platform, firstTweet?: string): string {
  switch (platform) {
    case 'instagram':
      return 'https://www.instagram.com/';
    case 'twitter':
      return `https://twitter.com/intent/tweet?text=${encodeURIComponent(firstTweet ?? '')}`;
    case 'linkedin':
      return 'https://www.linkedin.com/feed/?shareActive=true';
    case 'tiktok':
      return 'https://www.tiktok.com/upload';
    default:
      return 'https://www.facebook.com/';
  }
}

export function openPlatform(platform: Platform, firstTweet?: string): void {
  window.open(getShareUrl(platform, firstTweet), '_blank');
}
