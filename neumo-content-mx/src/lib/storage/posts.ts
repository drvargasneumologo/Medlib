import type { Post } from '../../types';
import { mockPosts } from '../../data';

const DRAFTS_KEY = 'neumo_drafts';

function readStore(): Post[] {
  try {
    const raw = localStorage.getItem(DRAFTS_KEY);
    return raw ? (JSON.parse(raw) as Post[]) : [];
  } catch {
    return [];
  }
}

function writeStore(posts: Post[]): void {
  try {
    localStorage.setItem(DRAFTS_KEY, JSON.stringify(posts));
  } catch {
    // silencioso — cuota excedida o modo incógnito
  }
}

export function getDrafts(): Post[] {
  const saved = readStore();
  const savedIds = new Set(saved.map((p) => p.id));
  const mocks = mockPosts.filter((p) => !savedIds.has(p.id));
  return [...mocks, ...saved];
}

export function saveDraft(post: Post): void {
  const posts = readStore();
  const idx = posts.findIndex((p) => p.id === post.id);
  if (idx >= 0) {
    posts[idx] = post;
  } else {
    posts.push(post);
  }
  writeStore(posts);
}

export function deleteDraft(id: string): void {
  writeStore(readStore().filter((p) => p.id !== id));
}

export function getScheduled(): Post[] {
  return getDrafts().filter((p) => p.status === 'programado');
}

export function schedulePost(id: string, scheduledAt: string): void {
  const posts = readStore();
  const idx = posts.findIndex((p) => p.id === id);
  if (idx >= 0) {
    posts[idx] = { ...posts[idx], status: 'programado', scheduledAt };
    writeStore(posts);
  } else {
    // post is a mock — bring it into storage with schedule
    const mock = mockPosts.find((p) => p.id === id);
    if (mock) {
      posts.push({ ...mock, status: 'programado', scheduledAt });
      writeStore(posts);
    }
  }
}
