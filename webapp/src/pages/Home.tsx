import { useCallback, useEffect, useState, type ComponentType } from 'react';
import { motion, type Variants } from 'framer-motion';
import { Link, useNavigate } from 'react-router-dom';
import {
  ArrowRight,
  Briefcase,
  Check,
  FileText,
  Folder,
  GraduationCap,
  Globe,
  HeartHandshake,
  KeyRound,
  Layers,
  Loader2,
  Lock,
  Network,
  Plus,
  Quote,
  ScanText,
  Server,
  ShieldCheck,
  Trash2,
  UploadCloud,
  Users2,
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { useKnowledgeBase } from '@/contexts/KnowledgeBaseContext';
import { api } from '@/lib/api';
import type { Job } from '@/lib/api';
import { useTranslation } from 'react-i18next';
import LiveProofPanel from '@/components/landing/LiveProofPanel';
import './home-landing.css';

const fadeUp: Variants = {
  hidden: { opacity: 0, y: 18 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.55, ease: 'easeOut' } },
};

const staggerContainer: Variants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.08 } },
};

function SectionHeading({ eyebrow, title }: { eyebrow: string; title: string }) {
  return (
    <div className="max-w-xl">
      <p className="hb-mono text-[11px] uppercase tracking-[0.16em] text-[var(--hb-accent)]">
        {eyebrow}
      </p>
      <h2 className="hb-display mt-2 text-2xl font-medium leading-tight text-[var(--hb-ink)] sm:text-3xl">
        {title}
      </h2>
    </div>
  );
}

function StatTile({
  icon: Icon,
  label,
  value,
}: {
  icon: ComponentType<{ className?: string }>;
  label: string;
  value: string | number;
}) {
  return (
    <div className="rounded-2xl border border-[var(--hb-border)] bg-[var(--hb-surface)] p-5">
      <div className="flex items-center gap-2 text-[var(--hb-ink-soft)]">
        <Icon className="h-4 w-4 text-[var(--hb-accent)]" />
        <span className="text-sm">{label}</span>
      </div>
      <p className="hb-display mt-2 text-2xl font-medium text-[var(--hb-ink)]">{value}</p>
    </div>
  );
}

export default function Home() {
  const { isAuthenticated, isLoading: authLoading, accessToken, user } = useAuth();
  const { selectKB } = useKnowledgeBase();
  const navigate = useNavigate();
  const { t } = useTranslation();

  const [jobs, setJobs] = useState<Job[]>([]);
  const [jobsLoading, setJobsLoading] = useState(true);

  // GET /api/jobs works for anonymous visitors too (returning only public/demo
  // jobs), so this always runs regardless of auth state.
  const loadJobs = useCallback(async () => {
    setJobsLoading(true);
    try {
      const response = await api.listJobs(accessToken || undefined);
      setJobs(response.jobs);
    } catch (err) {
      console.error('Failed to load jobs:', err);
    } finally {
      setJobsLoading(false);
    }
  }, [accessToken]);

  useEffect(() => {
    loadJobs();
  }, [loadJobs]);

  const ownJobs = jobs.filter((job) => !job.is_public);
  const userTotalDocs = ownJobs.reduce((sum, job) => sum + job.document_count, 0);
  const userTotalChunks = ownJobs.reduce((sum, job) => sum + job.chunk_count, 0);

  // "Try the live demo": select the first public/demo workspace and jump
  // straight into chat. If no public workspace exists, send visitors to
  // sign in instead. Anonymous-safe — /api/jobs already returns only public
  // jobs for anonymous callers.
  const handleTryDemo = useCallback(() => {
    const demoJob = jobs.find((job) => job.is_public);
    if (demoJob) {
      selectKB(demoJob.id);
      navigate('/chats');
    } else {
      navigate('/login');
    }
  }, [jobs, selectKB, navigate]);

  const handlePrimaryCta = useCallback(() => {
    if (isAuthenticated) {
      navigate('/jobs');
      return;
    }
    handleTryDemo();
  }, [isAuthenticated, navigate, handleTryDemo]);

  const scrollToSteps = useCallback(() => {
    const reduced =
      typeof window !== 'undefined' &&
      window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    document
      .getElementById('how-it-works')
      ?.scrollIntoView({ behavior: reduced ? 'auto' : 'smooth', block: 'start' });
  }, []);

  const primaryLabel = isAuthenticated
    ? t('home.hero.cta_primary_auth')
    : t('home.hero.cta_primary_anon');
  const primaryLoading = authLoading || (!isAuthenticated && jobsLoading);

  const features = [
    { icon: Quote, title: t('home.features.cited_chat_title'), body: t('home.features.cited_chat_body') },
    { icon: Network, title: t('home.features.graph_title'), body: t('home.features.graph_body') },
    { icon: Users2, title: t('home.features.workspaces_title'), body: t('home.features.workspaces_body') },
    { icon: Server, title: t('home.features.eu_title'), body: t('home.features.eu_body') },
    { icon: UploadCloud, title: t('home.features.bulk_title'), body: t('home.features.bulk_body') },
    { icon: ScanText, title: t('home.features.ocr_title'), body: t('home.features.ocr_body') },
  ];

  const steps = [
    { title: t('home.steps.step1_title'), body: t('home.steps.step1_body') },
    { title: t('home.steps.step2_title'), body: t('home.steps.step2_body') },
    { title: t('home.steps.step3_title'), body: t('home.steps.step3_body') },
  ];

  const useCases = [
    { icon: GraduationCap, title: t('home.use_cases.researchers_title'), body: t('home.use_cases.researchers_body') },
    { icon: Briefcase, title: t('home.use_cases.consulting_title'), body: t('home.use_cases.consulting_body') },
    { icon: HeartHandshake, title: t('home.use_cases.ngos_title'), body: t('home.use_cases.ngos_body') },
  ];

  const securityPillars = [
    { icon: Globe, title: t('home.security.residency_title'), body: t('home.security.residency_body') },
    { icon: Lock, title: t('home.security.encryption_title'), body: t('home.security.encryption_body') },
    { icon: Trash2, title: t('home.security.deletion_title'), body: t('home.security.deletion_body') },
    { icon: KeyRound, title: t('home.security.access_title'), body: t('home.security.access_body') },
  ];

  const pricingTiers = [
    {
      name: t('home.pricing.free_name'),
      price: t('home.pricing.free_price'),
      period: '',
      note: '',
      tagline: t('home.pricing.free_tagline'),
      features: [t('home.pricing.free_f1'), t('home.pricing.free_f2'), t('home.pricing.free_f3')],
      highlighted: false,
    },
    {
      name: t('home.pricing.pro_name'),
      price: t('home.pricing.pro_price'),
      period: t('home.pricing.pro_period'),
      note: '',
      tagline: t('home.pricing.pro_tagline'),
      features: [t('home.pricing.pro_f1'), t('home.pricing.pro_f2'), t('home.pricing.pro_f3')],
      highlighted: true,
    },
    {
      name: t('home.pricing.team_name'),
      price: t('home.pricing.team_price'),
      period: t('home.pricing.team_period'),
      note: t('home.pricing.team_note'),
      tagline: t('home.pricing.team_tagline'),
      features: [t('home.pricing.team_f1'), t('home.pricing.team_f2'), t('home.pricing.team_f3')],
      highlighted: false,
    },
  ];

  const handleSeeFullPricing = () => {
    navigate(isAuthenticated ? '/settings/billing' : '/login');
  };

  return (
    <div className="hb hb-grain">
      {/* 1. Hero + Live Proof panel */}
      <section className="mx-auto grid max-w-[1200px] gap-12 px-4 pb-16 pt-14 sm:px-8 sm:pt-20 lg:grid-cols-[1.05fr_0.95fr] lg:items-center lg:gap-10">
        <motion.div initial="hidden" animate="visible" variants={staggerContainer}>
          <motion.h1
            variants={fadeUp}
            className="hb-display text-4xl font-medium leading-[1.08] tracking-tight text-[var(--hb-ink)] sm:text-5xl lg:text-[3.4rem]"
          >
            <span className="block">{t('home.hero.h1_line1')}</span>
            <span className="relative mt-1 inline-block text-[var(--hb-deep)]">
              {t('home.hero.h1_line2')}
              <svg
                aria-hidden="true"
                viewBox="0 0 300 12"
                preserveAspectRatio="none"
                className="absolute -bottom-2 left-0 h-3 w-full text-[var(--hb-accent)]"
              >
                <path
                  className="hb-underline-path"
                  d="M2 8 Q 40 2, 80 7 T 160 6 T 240 8 T 298 5"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="4"
                  strokeLinecap="round"
                />
              </svg>
            </span>
          </motion.h1>

          <motion.p
            variants={fadeUp}
            className="mt-6 max-w-md text-lg leading-relaxed text-[var(--hb-ink-soft)]"
          >
            {t('home.hero.subhead')}
          </motion.p>

          <motion.div variants={fadeUp} className="mt-8 flex flex-wrap items-center gap-5">
            <button
              type="button"
              onClick={handlePrimaryCta}
              disabled={primaryLoading}
              className="hb-focus inline-flex items-center gap-2 rounded-full bg-[var(--hb-deep)] px-6 py-3 text-sm font-semibold text-[var(--hb-bg)] shadow-[0_10px_30px_-12px_rgba(11,79,74,0.55)] transition-transform hover:-translate-y-0.5 disabled:opacity-60 disabled:hover:translate-y-0"
            >
              {primaryLoading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <ArrowRight className="h-4 w-4" />
              )}
              {primaryLabel}
            </button>
            <button
              type="button"
              onClick={scrollToSteps}
              className="hb-focus text-sm font-semibold text-[var(--hb-ink)] underline decoration-[var(--hb-border)] decoration-2 underline-offset-4 transition-colors hover:decoration-[var(--hb-accent)]"
            >
              {t('home.hero.cta_secondary')}
            </button>
          </motion.div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.15, ease: 'easeOut' }}
          className="flex justify-center lg:justify-end"
        >
          <LiveProofPanel
            eyebrow={t('home.proof.eyebrow')}
            question={t('home.proof.question')}
            segments={[
              { type: 'text', value: t('home.proof.seg1') },
              { type: 'cite', id: 1 },
              { type: 'text', value: t('home.proof.seg2') },
              { type: 'cite', id: 2 },
              { type: 'text', value: t('home.proof.seg3') },
            ]}
            citations={[
              { id: 1, title: t('home.proof.cite1_title'), snippet: t('home.proof.cite1_snippet') },
              { id: 2, title: t('home.proof.cite2_title'), snippet: t('home.proof.cite2_snippet') },
            ]}
            tryLiveLabel={t('home.proof.try_live')}
            onTryLive={handleTryDemo}
            tryLiveLoading={!isAuthenticated && jobsLoading}
          />
        </motion.div>
      </section>

      {/* Signed-in only: quick path back to your own workspaces */}
      {isAuthenticated && (
        <section className="mx-auto max-w-[1200px] px-4 pb-16 sm:px-8">
          <div className="flex flex-wrap items-center justify-between gap-4 border-t border-[var(--hb-border)] pt-10">
            <div>
              <p className="hb-mono text-[11px] uppercase tracking-[0.16em] text-[var(--hb-accent)]">
                {t('home.your_kbs')}
              </p>
              <h2 className="hb-display mt-1 text-2xl font-medium text-[var(--hb-ink)]">
                {t('home.hello', { name: user?.name || user?.email?.split('@')[0] || 'Researcher' })}
              </h2>
            </div>
            <Link
              to="/jobs"
              className="hb-focus inline-flex items-center gap-2 rounded-full border border-[var(--hb-border)] px-4 py-2 text-sm font-medium text-[var(--hb-ink)] transition-colors hover:border-[var(--hb-accent)] hover:text-[var(--hb-accent)]"
            >
              <Plus className="h-4 w-4" />
              {t('home.new')}
            </Link>
          </div>

          {jobsLoading ? (
            <div className="flex items-center justify-center py-14">
              <Loader2 className="h-6 w-6 animate-spin text-[var(--hb-accent)]" />
            </div>
          ) : ownJobs.length === 0 ? (
            <div className="mt-8 rounded-2xl border border-dashed border-[var(--hb-border)] p-10 text-center">
              <Folder className="mx-auto h-8 w-8 text-[var(--hb-ink-soft)]" />
              <h3 className="hb-display mt-3 text-lg font-medium text-[var(--hb-ink)]">
                {t('home.no_kb_yet')}
              </h3>
              <p className="mx-auto mt-1 max-w-sm text-sm text-[var(--hb-ink-soft)]">
                {t('home.create_first_kb')}
              </p>
              <Link
                to="/jobs"
                className="hb-focus mt-5 inline-flex items-center gap-2 rounded-full bg-[var(--hb-deep)] px-5 py-2.5 text-sm font-semibold text-[var(--hb-bg)]"
              >
                <Plus className="h-4 w-4" />
                {t('home.create_kb')}
              </Link>
            </div>
          ) : (
            <>
              <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-3">
                <StatTile icon={Folder} label={t('home.stats_kbs')} value={ownJobs.length} />
                <StatTile icon={FileText} label={t('home.stats_docs')} value={userTotalDocs} />
                <StatTile
                  icon={Layers}
                  label={t('home.stats_chunks')}
                  value={userTotalChunks.toLocaleString()}
                />
              </div>
              <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {ownJobs.slice(0, 3).map((job) => (
                  <Link
                    key={job.id}
                    to={`/jobs/${job.id}`}
                    className="group rounded-2xl border border-[var(--hb-border)] bg-[var(--hb-surface)] p-5 transition-colors hover:border-[var(--hb-accent)]"
                  >
                    <div className="flex items-start gap-3">
                      <div className="rounded-lg bg-[var(--hb-accent-soft)] p-2">
                        <Folder className="h-4 w-4 text-[var(--hb-deep)]" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <h3 className="truncate font-semibold text-[var(--hb-ink)]">{job.name}</h3>
                        {job.description && (
                          <p className="mt-1 line-clamp-1 text-sm text-[var(--hb-ink-soft)]">
                            {job.description}
                          </p>
                        )}
                      </div>
                    </div>
                    <div className="mt-4 flex items-center gap-4 text-sm text-[var(--hb-ink-soft)]">
                      <span>
                        {job.document_count} {t('kb.docs')}
                      </span>
                      <span>
                        {job.chunk_count.toLocaleString()} {t('kb.chunks')}
                      </span>
                    </div>
                  </Link>
                ))}
                {ownJobs.length > 3 && (
                  <Link
                    to="/jobs"
                    className="flex min-h-[120px] items-center justify-center rounded-2xl border border-[var(--hb-border)] p-5 text-center transition-colors hover:border-[var(--hb-accent)]"
                  >
                    <div>
                      <p className="text-sm text-[var(--hb-ink-soft)]">
                        {t('home.more', { count: ownJobs.length - 3 })}
                      </p>
                      <p className="mt-1 text-sm font-semibold text-[var(--hb-accent)]">
                        {t('home.view_all')}
                      </p>
                    </div>
                  </Link>
                )}
              </div>
            </>
          )}
        </section>
      )}

      {/* 2. Trust bar */}
      <section className="border-y border-[var(--hb-border)] bg-[var(--hb-bg-soft)] py-6">
        <div className="mx-auto flex max-w-[1200px] flex-col items-center gap-3 px-4 text-center sm:flex-row sm:justify-between sm:px-8 sm:text-left">
          <p className="text-sm font-medium text-[var(--hb-ink-soft)]">{t('home.trust_bar.line')}</p>
          <div className="hb-mono flex flex-wrap items-center justify-center gap-x-5 gap-y-2 text-[11px] uppercase tracking-[0.1em] text-[var(--hb-deep)]">
            <span className="inline-flex items-center gap-1.5">
              <Globe className="h-3.5 w-3.5" />
              {t('home.trust_bar.badge1')}
            </span>
            <span className="inline-flex items-center gap-1.5">
              <ShieldCheck className="h-3.5 w-3.5" />
              {t('home.trust_bar.badge2')}
            </span>
            <span className="inline-flex items-center gap-1.5">
              <Quote className="h-3.5 w-3.5" />
              {t('home.trust_bar.badge3')}
            </span>
          </div>
        </div>
      </section>

      {/* 3. How it works */}
      <motion.section
        id="how-it-works"
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true, margin: '-80px' }}
        variants={staggerContainer}
        className="mx-auto max-w-[1200px] scroll-mt-24 px-4 py-20 sm:px-8"
      >
        <motion.div variants={fadeUp}>
          <SectionHeading eyebrow={t('home.steps.eyebrow')} title={t('home.steps.title')} />
        </motion.div>
        <div className="mt-12 grid gap-10 sm:grid-cols-3">
          {steps.map((step, i) => (
            <motion.div key={step.title} variants={fadeUp}>
              <span className="hb-display text-5xl text-[var(--hb-border)]">0{i + 1}</span>
              <h3 className="hb-display mt-3 text-xl font-medium text-[var(--hb-ink)]">
                {step.title}
              </h3>
              <p className="mt-2 text-[15px] leading-relaxed text-[var(--hb-ink-soft)]">
                {step.body}
              </p>
            </motion.div>
          ))}
        </div>
      </motion.section>

      {/* 4. Feature highlights */}
      <section className="bg-[var(--hb-bg-soft)] py-20">
        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: '-80px' }}
          variants={staggerContainer}
          className="mx-auto max-w-[1200px] px-4 sm:px-8"
        >
          <motion.div variants={fadeUp}>
            <SectionHeading eyebrow={t('home.features.eyebrow')} title={t('home.features.title')} />
          </motion.div>
          <div className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {features.map((f) => (
              <motion.div
                key={f.title}
                variants={fadeUp}
                className="rounded-2xl border border-[var(--hb-border)] bg-[var(--hb-surface)] p-6 transition-colors hover:border-[var(--hb-accent)]"
              >
                <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-lg bg-[var(--hb-accent-soft)] text-[var(--hb-deep)]">
                  <f.icon className="h-5 w-5" />
                </div>
                <h3 className="hb-display text-lg font-medium text-[var(--hb-ink)]">{f.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-[var(--hb-ink-soft)]">{f.body}</p>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </section>

      {/* 5. Use cases */}
      <motion.section
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true, margin: '-80px' }}
        variants={staggerContainer}
        className="mx-auto max-w-[1200px] px-4 py-20 sm:px-8"
      >
        <motion.div variants={fadeUp}>
          <SectionHeading eyebrow={t('home.use_cases.eyebrow')} title={t('home.use_cases.title')} />
        </motion.div>
        <div className="mt-12 grid gap-5 sm:grid-cols-3">
          {useCases.map((uc) => (
            <motion.div
              key={uc.title}
              variants={fadeUp}
              className="rounded-2xl border border-[var(--hb-border)] bg-[var(--hb-surface)] p-6"
            >
              <uc.icon className="h-6 w-6 text-[var(--hb-deep)]" />
              <h3 className="hb-display mt-4 text-lg font-medium text-[var(--hb-ink)]">{uc.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-[var(--hb-ink-soft)]">{uc.body}</p>
            </motion.div>
          ))}
        </div>
      </motion.section>

      {/* 6. Security & EU hosting */}
      <section className="bg-[var(--hb-deep)] py-20 text-[var(--hb-bg)]">
        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: '-80px' }}
          variants={staggerContainer}
          className="mx-auto max-w-[1200px] px-4 sm:px-8"
        >
          <motion.div variants={fadeUp}>
            <p className="hb-mono text-[11px] uppercase tracking-[0.16em] text-[var(--hb-accent)]">
              {t('home.security.eyebrow')}
            </p>
            <h2 className="hb-display mt-2 max-w-xl text-2xl font-medium leading-tight sm:text-3xl">
              {t('home.security.title')}
            </h2>
          </motion.div>
          <div className="mt-12 grid gap-5 sm:grid-cols-2">
            {securityPillars.map((p) => (
              <motion.div
                key={p.title}
                variants={fadeUp}
                className="rounded-2xl border border-white/15 bg-white/5 p-6"
              >
                <div className="mb-3 flex h-9 w-9 items-center justify-center rounded-lg bg-white/10">
                  <p.icon className="h-[18px] w-[18px]" />
                </div>
                <h3 className="font-semibold">{p.title}</h3>
                <p className="mt-1.5 text-sm leading-relaxed text-white/75">{p.body}</p>
              </motion.div>
            ))}
          </div>
          <motion.div variants={fadeUp} className="mt-8 flex flex-wrap gap-x-6 gap-y-2 text-sm">
            <Link to="/trust" className="hb-focus font-semibold underline underline-offset-4 hover:text-[var(--hb-accent)]">
              {t('home.security.link_trust')}
            </Link>
            <Link
              to="/legal/privacy"
              className="hb-focus font-semibold underline underline-offset-4 hover:text-[var(--hb-accent)]"
            >
              {t('home.security.link_privacy')}
            </Link>
          </motion.div>
        </motion.div>
      </section>

      {/* 7. Pricing teaser */}
      <motion.section
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true, margin: '-80px' }}
        variants={staggerContainer}
        className="mx-auto max-w-[1200px] px-4 py-20 sm:px-8"
      >
        <motion.div variants={fadeUp}>
          <SectionHeading eyebrow={t('home.pricing.eyebrow')} title={t('home.pricing.title')} />
        </motion.div>
        <div className="mt-12 grid gap-5 sm:grid-cols-3">
          {pricingTiers.map((tier) => (
            <motion.div
              key={tier.name}
              variants={fadeUp}
              className={`relative rounded-2xl border p-6 ${
                tier.highlighted
                  ? 'border-[var(--hb-deep)] bg-[var(--hb-surface)] shadow-[0_20px_50px_-25px_rgba(11,79,74,0.55)]'
                  : 'border-[var(--hb-border)] bg-[var(--hb-surface)]'
              }`}
            >
              {tier.highlighted && (
                <span className="hb-mono absolute -top-3 left-6 rounded-full bg-[var(--hb-deep)] px-3 py-1 text-[10px] uppercase tracking-[0.1em] text-[var(--hb-bg)]">
                  {t('home.pricing.pro_name')}
                </span>
              )}
              <h3 className="hb-display text-lg font-medium text-[var(--hb-ink)]">{tier.name}</h3>
              <p className="mt-2 flex items-baseline gap-1">
                <span className="hb-display text-3xl font-medium text-[var(--hb-ink)]">
                  {tier.price}
                </span>
                {tier.period && (
                  <span className="text-sm text-[var(--hb-ink-soft)]">{tier.period}</span>
                )}
              </p>
              {tier.note && (
                <p className="hb-mono mt-0.5 text-[11px] text-[var(--hb-ink-soft)]">{tier.note}</p>
              )}
              <p className="mt-3 text-sm text-[var(--hb-ink-soft)]">{tier.tagline}</p>
              <ul className="mt-5 space-y-2">
                {tier.features.map((feat) => (
                  <li key={feat} className="flex items-start gap-2 text-sm text-[var(--hb-ink)]">
                    <Check className="mt-0.5 h-4 w-4 shrink-0 text-[var(--hb-accent)]" />
                    {feat}
                  </li>
                ))}
              </ul>
            </motion.div>
          ))}
        </div>
        <motion.div variants={fadeUp} className="mt-10 flex justify-center">
          <button
            type="button"
            onClick={handleSeeFullPricing}
            className="hb-focus inline-flex items-center gap-2 rounded-full border border-[var(--hb-border)] px-6 py-3 text-sm font-semibold text-[var(--hb-ink)] transition-colors hover:border-[var(--hb-accent)] hover:text-[var(--hb-accent)]"
          >
            {t('home.pricing.see_full')}
            <ArrowRight className="h-4 w-4" />
          </button>
        </motion.div>
      </motion.section>

      {/* 8. Final CTA */}
      <section className="mx-auto max-w-[1200px] px-4 pb-24 sm:px-8">
        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: '-80px' }}
          variants={fadeUp}
          className="hb-grain rounded-3xl border border-[var(--hb-border)] bg-[var(--hb-bg-soft)] px-8 py-16 text-center"
        >
          <h2 className="hb-display text-3xl font-medium leading-tight text-[var(--hb-ink)] sm:text-4xl">
            {t('home.final_cta.title')}
            <br />
            <span className="text-[var(--hb-deep)]">{t('home.final_cta.title_emphasis')}</span>
          </h2>
          <button
            type="button"
            onClick={handlePrimaryCta}
            disabled={primaryLoading}
            className="hb-focus mt-8 inline-flex items-center gap-2 rounded-full bg-[var(--hb-deep)] px-7 py-3.5 text-sm font-semibold text-[var(--hb-bg)] shadow-[0_10px_30px_-12px_rgba(11,79,74,0.55)] transition-transform hover:-translate-y-0.5 disabled:opacity-60 disabled:hover:translate-y-0"
          >
            {primaryLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <ArrowRight className="h-4 w-4" />
            )}
            {isAuthenticated ? t('home.final_cta.button_auth') : t('home.final_cta.button_anon')}
          </button>
        </motion.div>
      </section>

      {/* 9. Footer note */}
      <p className="hb-mono mx-auto max-w-[1200px] px-4 pb-10 text-center text-[11px] text-[var(--hb-ink-soft)] sm:px-8">
        {t('home.footer_note')}
      </p>
    </div>
  );
}
