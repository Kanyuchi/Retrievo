import { useEffect, useMemo, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Play, Loader2 } from 'lucide-react';

export interface ProofCitation {
  id: number;
  title: string;
  snippet: string;
}

export type ProofSegment =
  | { type: 'text'; value: string }
  | { type: 'cite'; id: number };

interface LiveProofPanelProps {
  eyebrow: string;
  question: string;
  segments: ProofSegment[];
  citations: ProofCitation[];
  tryLiveLabel: string;
  onTryLive: () => void;
  tryLiveLoading?: boolean;
}

type Token =
  | { kind: 'char'; value: string }
  | { kind: 'cite'; id: number };

const REVEAL_MS = 16; // per character
const CITE_PAUSE_MS = 260; // extra pause when a citation chip pops in
const HOLD_MS = 4200; // how long the finished answer stays fully visible
const RESTART_FADE_MS = 350;

/**
 * Animated, self-contained sample Q&A for the hero. This is NOT a live
 * backend call — it's a scripted, typewriter-revealed answer with inline
 * citation chips that expand to a source snippet on hover/click. Keeping it
 * fake keeps the hero instant and reliable; the real product is one click
 * away via `onTryLive`.
 */
export default function LiveProofPanel({
  eyebrow,
  question,
  segments,
  citations,
  tryLiveLabel,
  onTryLive,
  tryLiveLoading,
}: LiveProofPanelProps) {
  const tokens = useMemo<Token[]>(() => {
    const out: Token[] = [];
    for (const seg of segments) {
      if (seg.type === 'text') {
        for (const ch of seg.value) out.push({ kind: 'char', value: ch });
      } else {
        out.push({ kind: 'cite', id: seg.id });
      }
    }
    return out;
  }, [segments]);

  // Read once, synchronously, so the very first render already shows the
  // final state under reduced motion — no flash of an animating panel.
  const [reducedMotion] = useState(
    () =>
      typeof window !== 'undefined' &&
      !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
  );
  const [revealed, setRevealed] = useState(() => (reducedMotion ? tokens.length : 0));
  const [phase, setPhase] = useState<'typing' | 'done' | 'fading'>(
    () => (reducedMotion ? 'done' : 'typing')
  );
  const [activeCite, setActiveCite] = useState<number | null>(null);
  const [pinnedCite, setPinnedCite] = useState<number | null>(null);

  useEffect(() => {
    if (reducedMotion) {
      // No typewriter, no loop — the finished answer is already showing.
      return;
    }

    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;

    const runCycle = (from: number) => {
      if (cancelled) return;
      if (from >= tokens.length) {
        setPhase('done');
        timer = setTimeout(() => {
          if (cancelled) return;
          setPhase('fading');
          timer = setTimeout(() => {
            if (cancelled) return;
            setRevealed(0);
            setPinnedCite(null);
            setActiveCite(null);
            setPhase('typing');
            timer = setTimeout(() => runCycle(0), RESTART_FADE_MS);
          }, RESTART_FADE_MS);
        }, HOLD_MS);
        return;
      }
      const isCite = tokens[from]?.kind === 'cite';
      setRevealed(from + 1);
      timer = setTimeout(() => runCycle(from + 1), isCite ? CITE_PAUSE_MS : REVEAL_MS);
    };

    runCycle(0);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [tokens, reducedMotion]);

  const citationById = useMemo(() => {
    const map = new Map<number, ProofCitation>();
    citations.forEach((c) => map.set(c.id, c));
    return map;
  }, [citations]);

  const openCite = pinnedCite ?? activeCite;
  const openCitation = openCite != null ? citationById.get(openCite) : undefined;

  return (
    <div className="hb-mono w-full max-w-md">
      <div className="mb-2 flex items-center gap-2 text-[11px] uppercase tracking-[0.18em] text-[var(--hb-accent)]">
        <span className="relative flex h-1.5 w-1.5">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[var(--hb-accent)] opacity-60 motion-reduce:hidden" />
          <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-[var(--hb-accent)]" />
        </span>
        {eyebrow}
      </div>

      <div
        className="rounded-2xl border border-[var(--hb-border)] bg-[var(--hb-surface)] shadow-[0_18px_50px_-25px_rgba(11,79,74,0.45)]"
        style={{ opacity: phase === 'fading' ? 0 : 1, transition: `opacity ${RESTART_FADE_MS}ms ease` }}
      >
        <div className="flex items-center justify-between border-b border-[var(--hb-border)] px-5 py-3">
          <span className="text-[11px] uppercase tracking-[0.14em] text-[var(--hb-ink-soft)]">
            Exhibit A — live query
          </span>
          <span className="text-[11px] text-[var(--hb-ink-soft)]">humbowo.eu</span>
        </div>

        <div className="px-5 pt-5 pb-4">
          <p className="hb-display text-[15px] italic leading-snug text-[var(--hb-deep)]">
            &ldquo;{question}&rdquo;
          </p>
        </div>

        <div className="mx-5 border-t border-dashed border-[var(--hb-border)]" />

        <div className="px-5 py-5 min-h-[132px]">
          <p className="hb-mono text-[13.5px] leading-relaxed text-[var(--hb-ink)]">
            {tokens.slice(0, revealed).map((tok, i) => {
              if (tok.kind === 'char') {
                return <span key={i}>{tok.value}</span>;
              }
              const citation = citationById.get(tok.id);
              if (!citation) return null;
              return (
                <button
                  key={i}
                  type="button"
                  className="hb-focus mx-0.5 inline-flex -translate-y-0.5 items-center rounded border border-[var(--hb-accent)]/50 bg-[var(--hb-accent-soft)] px-1 text-[11px] font-semibold text-[var(--hb-deep)] transition-colors hover:bg-[var(--hb-accent)] hover:text-[var(--hb-surface)]"
                  aria-expanded={openCite === citation.id}
                  onMouseEnter={() => setActiveCite(citation.id)}
                  onMouseLeave={() => setActiveCite(null)}
                  onFocus={() => setActiveCite(citation.id)}
                  onBlur={() => setActiveCite(null)}
                  onClick={() =>
                    setPinnedCite((prev) => (prev === citation.id ? null : citation.id))
                  }
                >
                  [{citation.id}]
                </button>
              );
            })}
            {phase !== 'done' && phase !== 'fading' && (
              <span className="hb-caret ml-0.5 inline-block h-[13px] w-[2px] -translate-y-0.5 bg-[var(--hb-deep)] align-middle" />
            )}
          </p>

          <AnimatePresence>
            {openCitation && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.22, ease: 'easeOut' }}
                className="overflow-hidden"
              >
                <div className="mt-4 rounded-lg border border-[var(--hb-border)] bg-[var(--hb-bg-soft)] p-3">
                  <p className="hb-mono text-[10.5px] uppercase tracking-[0.1em] text-[var(--hb-accent)]">
                    Source [{openCitation.id}]
                  </p>
                  <p className="hb-display mt-1 text-[13px] font-medium text-[var(--hb-ink)]">
                    {openCitation.title}
                  </p>
                  <p className="mt-1 text-[12px] leading-relaxed text-[var(--hb-ink-soft)]">
                    {openCitation.snippet}
                  </p>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      <button
        type="button"
        onClick={onTryLive}
        disabled={tryLiveLoading}
        className="hb-focus mt-4 inline-flex items-center gap-2 text-[13px] font-semibold text-[var(--hb-deep)] transition-colors hover:text-[var(--hb-accent)] disabled:opacity-60"
      >
        {tryLiveLoading ? (
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
        ) : (
          <Play className="h-3.5 w-3.5 fill-current" />
        )}
        {tryLiveLabel}
      </button>
    </div>
  );
}
