export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function mediaUrl(path: string | null | undefined): string {
  if (!path) return "";
  if (path.startsWith("http://") || path.startsWith("https://")) return path;
  return `${API_BASE}${path}`;
}
