import { Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';

/**
 * Shared shell for the static legal / trust pages (privacy, impressum, dpa, trust).
 * Public pages — no auth check, no data fetching.
 */
export function LegalLayout({
  title,
  subtitle,
  lastUpdated,
  children,
}: {
  title: string;
  subtitle?: string;
  lastUpdated?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-[calc(100vh-72px)] bg-background px-4 md:px-8 py-10 md:py-14">
      <div className="max-w-3xl mx-auto">
        <Link
          to="/"
          className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors mb-8"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Humbowo
        </Link>

        <h1 className="text-3xl md:text-4xl font-bold text-white mb-2">{title}</h1>
        {subtitle && <p className="text-muted-foreground text-lg mb-1">{subtitle}</p>}
        {lastUpdated && (
          <p className="text-xs text-muted-foreground mb-8">Last updated: {lastUpdated}</p>
        )}
        {!lastUpdated && subtitle && <div className="mb-6" />}

        <div className="prose prose-invert prose-sm md:prose-base max-w-none space-y-10 text-foreground/90">
          {children}
        </div>
      </div>
    </div>
  );
}

/** Highlights a {{PLACEHOLDER}} token so it's obviously to-be-filled before shipping. */
export function Placeholder({ children }: { children: React.ReactNode }) {
  return (
    <span className="inline-block rounded bg-amber-500/15 border border-amber-500/40 text-amber-400 px-1.5 py-0.5 font-mono text-[0.85em] font-medium">
      {children}
    </span>
  );
}

export function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section>
      <h2 className="text-xl font-semibold text-white mb-3">{title}</h2>
      <div className="space-y-3 text-sm md:text-base text-muted-foreground leading-relaxed">
        {children}
      </div>
    </section>
  );
}

export function NoticeBox({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-sm text-amber-300">
      {children}
    </div>
  );
}

export type SubProcessor = {
  name: string;
  location: string;
  purpose: string;
};

export const SUB_PROCESSORS: SubProcessor[] = [
  { name: 'Hetzner Online GmbH', location: 'Germany (EU)', purpose: 'Server hosting (Falkenstein data center)' },
  { name: 'Supabase Inc.', location: 'Frankfurt, Germany (AWS eu-central-1)', purpose: 'Application database' },
  { name: 'OpenAI LLC', location: 'United States', purpose: 'Document embeddings and AI-generated insights' },
  { name: 'xAI Corp', location: 'United States', purpose: 'Chat answer generation' },
  { name: 'GoDaddy', location: 'United States', purpose: 'Domain registration and DNS' },
];

export function SubProcessorTable() {
  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <table className="w-full text-sm text-left">
        <thead className="bg-secondary/50 text-foreground">
          <tr>
            <th className="px-4 py-2.5 font-medium">Sub-processor</th>
            <th className="px-4 py-2.5 font-medium">Location</th>
            <th className="px-4 py-2.5 font-medium">Purpose</th>
          </tr>
        </thead>
        <tbody>
          {SUB_PROCESSORS.map((row) => (
            <tr key={row.name} className="border-t border-border">
              <td className="px-4 py-2.5 text-foreground">{row.name}</td>
              <td className="px-4 py-2.5 text-muted-foreground">{row.location}</td>
              <td className="px-4 py-2.5 text-muted-foreground">{row.purpose}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
