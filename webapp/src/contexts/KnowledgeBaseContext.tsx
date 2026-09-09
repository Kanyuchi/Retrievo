import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { useAuth } from './AuthContext';
import { api } from '../lib/api';
import type { Job } from '../lib/api';

const SELECTED_KB_STORAGE_KEY = 'selected_kb';

export interface KnowledgeBase {
  id: number;
  name: string;
  description?: string;
  document_count: number;
  chunk_count: number;
  // Legacy flag from the retired "Public Demo Collection" pseudo-KB (a
  // client-only stand-in for the global collection). Every KB is now backed
  // by a real job, so this is always false — kept only so pages that still
  // branch on it (Knowledge Insights/Graph) keep compiling unchanged.
  isDefault: boolean;
  // True for public/demo workspaces (jobs with is_public=true). Anonymous
  // visitors only ever see public jobs in availableKBs.
  isPublic: boolean;
  role: string;
}

interface KnowledgeBaseContextType {
  // Currently selected knowledge base
  selectedKB: KnowledgeBase | null;
  // All available knowledge bases (own jobs + public/demo jobs)
  availableKBs: KnowledgeBase[];
  // Loading state
  isLoading: boolean;
  // Select a knowledge base by job id
  selectKB: (id: number) => void;
  // Refresh the list
  refreshKBs: () => Promise<void>;
  // Legacy flag — always false now; kept for backward-compat call sites.
  isDefaultSelected: boolean;
}

const KnowledgeBaseContext = createContext<KnowledgeBaseContextType | undefined>(undefined);

function toKnowledgeBase(job: Job): KnowledgeBase {
  return {
    id: job.id,
    name: job.name,
    description: job.description || undefined,
    document_count: job.document_count,
    chunk_count: job.chunk_count,
    isDefault: false,
    isPublic: job.is_public ?? false,
    role: job.role ?? 'owner',
  };
}

// Pick a sensible fallback selection: prefer a public/demo workspace so
// anonymous and first-time visitors land somewhere with content, otherwise
// fall back to whatever KB is first in the list.
function pickFallbackKB(kbs: KnowledgeBase[]): KnowledgeBase | null {
  return kbs.find((kb) => kb.isPublic) || kbs[0] || null;
}

export function KnowledgeBaseProvider({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, accessToken } = useAuth();
  const [selectedKB, setSelectedKB] = useState<KnowledgeBase | null>(null);
  const [availableKBs, setAvailableKBs] = useState<KnowledgeBase[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Load available knowledge bases. GET /api/jobs now works for anonymous
  // callers too (returning only public jobs with role "viewer"), so this
  // always runs — not gated on isAuthenticated.
  const refreshKBs = useCallback(async () => {
    setIsLoading(true);
    try {
      const response = await api.listJobs(accessToken || undefined);
      const kbs = response.jobs.map(toKnowledgeBase);
      setAvailableKBs(kbs);

      setSelectedKB((current) => {
        // Keep the current selection (refreshed in place for updated
        // counts/role) if it still exists.
        if (current) {
          const stillExists = kbs.find((kb) => kb.id === current.id);
          if (stillExists) return stillExists;
        }

        // Otherwise try to restore a persisted selection; migrate away from
        // a stale/legacy pointer (including the old "default" pseudo-KB,
        // which was never persisted as a numeric id) to a public workspace,
        // then to the first available KB of any kind.
        const savedId = localStorage.getItem(SELECTED_KB_STORAGE_KEY);
        const numericSavedId = savedId ? Number(savedId) : NaN;
        const saved = Number.isFinite(numericSavedId)
          ? kbs.find((kb) => kb.id === numericSavedId)
          : undefined;

        const next = saved || pickFallbackKB(kbs);
        if (!next) {
          localStorage.removeItem(SELECTED_KB_STORAGE_KEY);
        } else if (next.id !== numericSavedId) {
          localStorage.setItem(SELECTED_KB_STORAGE_KEY, String(next.id));
        }
        return next;
      });
    } catch (err) {
      console.error('Failed to load knowledge bases:', err);
    } finally {
      setIsLoading(false);
    }
  }, [accessToken]);

  // Reload whenever auth state changes (login/logout swaps which private
  // jobs — if any — are visible alongside the public ones).
  useEffect(() => {
    refreshKBs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated, accessToken]);

  const selectKB = useCallback((id: number) => {
    const kb = availableKBs.find((k) => k.id === id);
    if (kb) {
      setSelectedKB(kb);
      localStorage.setItem(SELECTED_KB_STORAGE_KEY, String(id));
    }
  }, [availableKBs]);

  const value: KnowledgeBaseContextType = {
    selectedKB,
    availableKBs,
    isLoading,
    selectKB,
    refreshKBs,
    isDefaultSelected: false,
  };

  return (
    <KnowledgeBaseContext.Provider value={value}>
      {children}
    </KnowledgeBaseContext.Provider>
  );
}

export function useKnowledgeBase() {
  const context = useContext(KnowledgeBaseContext);
  if (context === undefined) {
    throw new Error('useKnowledgeBase must be used within a KnowledgeBaseProvider');
  }
  return context;
}
