// Shared helper for detecting plan-quota errors surfaced from the backend
// (see literature_rag/quotas.py — messages like "Knowledge base limit
// reached (3). Upgrade plan for more." / "Document limit reached ...").
// Used to decide when to show an "Upgrade plan" link/button next to an
// error, in both the KB-creation flow (Jobs.tsx) and the upload flow
// (JobDetail.tsx).
export function isQuotaError(message: string | null | undefined): boolean {
  if (!message) return false;
  const lower = message.toLowerCase();
  return lower.includes('limit') || lower.includes('upgrade');
}
