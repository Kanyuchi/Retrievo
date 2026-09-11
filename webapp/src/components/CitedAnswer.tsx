export interface CitedAnswerSource {
  citation_number: number;
  authors?: string;
  year?: number | string;
  title?: string;
  doc_id?: string;
  snippet?: string;
  page?: number | string | null;
  section?: string | null;
}

interface CitedAnswerProps {
  answer: string;
  sources?: CitedAnswerSource[];
  activeCitation?: number | null;
  onSelectCitation?: (citationNumber: number) => void;
}

const CITATION_PATTERN = /(\[\d+\])/g;

/**
 * Renders an assistant answer with inline, clickable citation chips.
 *
 * The backend embeds plain-text markers like "[1]" in the answer. This
 * component splits on those markers and, for any marker that matches a
 * known source, renders a small chip that the reader can click to reveal
 * the exact passage that grounded it (the "inspectable citation" proof).
 * Markers with no matching source (or an answer with no markers at all)
 * fall back to plain text -- this must never throw on unexpected input.
 */
export default function CitedAnswer({
  answer,
  sources,
  activeCitation = null,
  onSelectCitation,
}: CitedAnswerProps) {
  const sourceNumbers = new Set((sources ?? []).map((s) => s.citation_number));
  const parts = (answer || '').split(CITATION_PATTERN);

  return (
    <p className="whitespace-pre-wrap text-left">
      {parts.map((part, idx) => {
        const match = part.match(/^\[(\d+)\]$/);
        if (match) {
          const citationNumber = parseInt(match[1], 10);
          if (sourceNumbers.has(citationNumber)) {
            const isActive = activeCitation === citationNumber;
            return (
              <button
                key={idx}
                type="button"
                onClick={() => onSelectCitation?.(citationNumber)}
                aria-pressed={isActive}
                aria-label={`View source ${citationNumber}`}
                className={`mx-0.5 -translate-y-px inline-flex items-center rounded border px-1 font-mono text-[11px] font-semibold align-baseline transition-colors ${
                  isActive
                    ? 'border-primary bg-primary text-primary-foreground'
                    : 'border-primary/40 bg-primary/10 text-primary hover:bg-primary/20'
                }`}
              >
                [{citationNumber}]
              </button>
            );
          }
        }
        return <span key={idx}>{part}</span>;
      })}
    </p>
  );
}
