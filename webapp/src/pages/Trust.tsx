import { Link } from 'react-router-dom';
import { ArrowLeft, ServerCog, ShieldCheck, Trash2, Users, Lock, Info } from 'lucide-react';
import { Card } from '@/components/ui/card';

const pillars = [
  {
    icon: ServerCog,
    title: 'Built in the EU',
    body:
      'Your application server and backups run on Hetzner in Falkenstein, Germany. Your database runs on Supabase in Frankfurt, Germany (AWS eu-central-1). Uploaded files live in object storage on our own EU-based server.',
  },
  {
    icon: Lock,
    title: 'TLS everywhere',
    body: 'All traffic to and from Humbowo — the app, the API, and file uploads — is encrypted in transit.',
  },
  {
    icon: ShieldCheck,
    title: 'Daily backups',
    body: 'Your data is backed up daily so a server failure does not mean a data loss event.',
  },
  {
    icon: Trash2,
    title: 'Permanent deletion, for real',
    body:
      'Deleting a knowledge base or your account immediately and permanently purges its documents, vector embeddings, chat history, and stored files. No soft-delete limbo, no lingering copies.',
  },
  {
    icon: Users,
    title: 'Roles & workspace access controls',
    body:
      'Knowledge bases are isolated per workspace. Members only see what they have been invited into, with role-based access to control who can upload, query, or manage a workspace.',
  },
  {
    icon: ShieldCheck,
    title: 'No training on your data',
    body:
      'Your documents and queries are never used to train our models or any third-party model. They are processed only to answer your questions.',
  },
];

export default function Trust() {
  return (
    <div className="min-h-[calc(100vh-72px)] bg-background px-4 md:px-8 py-10 md:py-14">
      <div className="max-w-4xl mx-auto">
        <Link
          to="/"
          className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors mb-8"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Humbowo
        </Link>

        <h1 className="text-3xl md:text-4xl font-bold text-white mb-3">Trust & Security</h1>
        <p className="text-muted-foreground text-lg mb-10 max-w-2xl">
          Humbowo is built by TheNerdsInt for teams who need to know exactly where their data
          lives and who touches it. Here is the plain-language version.
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-10">
          {pillars.map(({ icon: Icon, title, body }) => (
            <Card key={title} className="p-6 bg-card border-border">
              <div className="flex items-center gap-3 mb-2">
                <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
                  <Icon className="w-4 h-4 text-primary" />
                </div>
                <h2 className="font-semibold text-foreground">{title}</h2>
              </div>
              <p className="text-sm text-muted-foreground leading-relaxed">{body}</p>
            </Card>
          ))}
        </div>

        <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-5 py-4 mb-10">
          <div className="flex items-start gap-3">
            <Info className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
            <div className="text-sm text-amber-200 leading-relaxed">
              <p className="font-semibold text-amber-300 mb-1">Where AI processing happens</p>
              <p>
                Embeddings and chat answers are computed via OpenAI and xAI APIs in the US under
                no-training API terms. Your stored documents never leave the EU; text excerpts
                are transmitted for processing when you upload a document or ask a question.
              </p>
            </div>
          </div>
        </div>

        <p className="text-sm text-muted-foreground">
          Full sub-processor list, data categories, and legal bases are in our{' '}
          <Link to="/legal/privacy" className="text-primary hover:underline">
            Privacy Policy
          </Link>
          . For contractual terms, see our{' '}
          <Link to="/legal/dpa" className="text-primary hover:underline">
            Data Processing Agreement
          </Link>
          .
        </p>
      </div>
    </div>
  );
}
