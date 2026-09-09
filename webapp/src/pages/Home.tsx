import { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import { Link, useNavigate } from 'react-router-dom';
import { Database, MessageSquare, ChevronRight, Loader2, FileText, Layers, Folder, Plus, Briefcase } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useAuth } from '@/contexts/AuthContext';
import { useKnowledgeBase } from '@/contexts/KnowledgeBaseContext';
import { api } from '@/lib/api';
import type { Job } from '@/lib/api';
import { useTranslation } from 'react-i18next';

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.15,
      delayChildren: 0.1,
    },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.6,
    },
  },
};

export default function Home() {
  const { isAuthenticated, isLoading: authLoading, accessToken, user } = useAuth();
  const { selectKB } = useKnowledgeBase();
  const navigate = useNavigate();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [jobsLoading, setJobsLoading] = useState(true);
  const { t } = useTranslation();

  // Load the jobs payload. GET /api/jobs works for anonymous visitors too
  // (returning only public/demo jobs), so this always runs — there's no
  // more separate legacy /api/stats call or double-fetch.
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
  const publicJobs = jobs.filter((job) => job.is_public);

  const userTotalDocs = ownJobs.reduce((sum, job) => sum + job.document_count, 0);
  const userTotalChunks = ownJobs.reduce((sum, job) => sum + job.chunk_count, 0);
  const demoTotalDocs = publicJobs.reduce((sum, job) => sum + job.document_count, 0);

  const isUserLoading = authLoading || jobsLoading;

  const openDemoWorkspace = (job: Job) => {
    selectKB(job.id);
    navigate('/datasets');
  };

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className="min-h-[calc(100vh-72px)] bg-background px-4 md:px-8 lg:px-12 py-8 md:py-12"
    >
      <div className="max-w-[1400px] mx-auto">
        {/* Hero Section */}
        <motion.section variants={itemVariants} className="mb-16">
          <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold text-white">
            {t('home.welcome')} <span className="gradient-text">Humbowo</span>
          </h1>
          <p className="mt-4 text-muted-foreground text-lg">
            {isAuthenticated
              ? t('home.hello', { name: user?.name || user?.email?.split('@')[0] || 'Researcher' })
              : t('home.guest_subtitle')}
          </p>
        </motion.section>

        {isUserLoading ? (
          <motion.section variants={itemVariants}>
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-8 h-8 animate-spin text-primary" />
            </div>
          </motion.section>
        ) : (
          <>
            {/* User's Own Knowledge Bases (signed-in only) */}
            {isAuthenticated && (
              <motion.section variants={itemVariants} className="mb-12">
                <div className="flex items-center justify-between mb-6">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center">
                      <Briefcase className="w-5 h-5 text-primary" />
                    </div>
                    <h2 className="text-2xl font-semibold text-white">{t('home.your_kbs')}</h2>
                  </div>
                  <Link
                    to="/jobs"
                    className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
                  >
                    <Plus className="h-4 w-4" />
                    {t('home.new')}
                  </Link>
                </div>

                {ownJobs.length === 0 ? (
                  <Card className="p-8 bg-card border-border text-center">
                    <Folder className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
                    <h3 className="text-lg font-medium text-foreground mb-2">
                      {t('home.no_kb_yet')}
                    </h3>
                    <p className="text-muted-foreground mb-4">
                      {t('home.create_first_kb')}
                    </p>
                    <Link
                      to="/jobs"
                      className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
                    >
                      <Plus className="h-4 w-4" />
                      {t('home.create_kb')}
                    </Link>
                  </Card>
                ) : (
                  <>
                    {/* User Stats */}
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
                      <Card className="p-6 bg-card border-border">
                        <div className="flex items-center gap-3 mb-2">
                          <Folder className="w-5 h-5 text-primary" />
                          <span className="text-muted-foreground text-sm">{t('home.stats_kbs')}</span>
                        </div>
                        <p className="text-3xl font-bold text-white">{ownJobs.length}</p>
                      </Card>
                      <Card className="p-6 bg-card border-border">
                        <div className="flex items-center gap-3 mb-2">
                          <FileText className="w-5 h-5 text-primary" />
                          <span className="text-muted-foreground text-sm">{t('home.stats_docs')}</span>
                        </div>
                        <p className="text-3xl font-bold text-white">{userTotalDocs}</p>
                      </Card>
                      <Card className="p-6 bg-card border-border">
                        <div className="flex items-center gap-3 mb-2">
                          <Layers className="w-5 h-5 text-primary" />
                          <span className="text-muted-foreground text-sm">{t('home.stats_chunks')}</span>
                        </div>
                        <p className="text-3xl font-bold text-white">{userTotalChunks.toLocaleString()}</p>
                      </Card>
                    </div>

                    {/* Recent Jobs */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                      {ownJobs.slice(0, 3).map((job) => (
                        <Link key={job.id} to={`/jobs/${job.id}`}>
                          <Card className="p-5 bg-card border-border hover:border-primary/50 transition-colors cursor-pointer group">
                            <div className="flex items-start gap-3 mb-3">
                              <div className="p-2 bg-primary/10 rounded-lg">
                                <Folder className="h-5 w-5 text-primary" />
                              </div>
                              <div className="flex-1 min-w-0">
                                <h3 className="font-semibold text-foreground truncate">
                                  {job.name}
                                </h3>
                                {job.description && (
                                  <p className="text-sm text-muted-foreground line-clamp-1 mt-1">
                                    {job.description}
                                  </p>
                                )}
                              </div>
                              <ChevronRight className="h-4 w-4 text-muted-foreground group-hover:text-primary transition-colors" />
                            </div>
                            <div className="flex items-center gap-4 text-sm text-muted-foreground">
                              <span>{job.document_count} {t('kb.docs')}</span>
                              <span>{job.chunk_count} {t('kb.chunks')}</span>
                            </div>
                          </Card>
                        </Link>
                      ))}
                      {ownJobs.length > 3 && (
                        <Link to="/jobs">
                          <Card className="p-5 bg-card border-border hover:border-primary/50 transition-colors cursor-pointer flex items-center justify-center h-full min-h-[120px]">
                            <div className="text-center">
                              <p className="text-muted-foreground">
                                {t('home.more', { count: ownJobs.length - 3 })}
                              </p>
                              <p className="text-sm text-primary mt-1">{t('home.view_all')}</p>
                            </div>
                          </Card>
                        </Link>
                      )}
                    </div>
                  </>
                )}
              </motion.section>
            )}

            {/* Public Demo Workspaces — visible to everyone, including anonymous visitors */}
            {publicJobs.length > 0 && (
              <motion.section variants={itemVariants} className="mb-12">
                {isAuthenticated && <div className="border-t border-border pt-8 mb-2" />}
                <div className="flex items-center gap-3 mb-6">
                  <div className="w-8 h-8 rounded-lg bg-secondary/50 flex items-center justify-center">
                    <Database className="w-5 h-5 text-muted-foreground" />
                  </div>
                  <div>
                    <h2 className="text-xl font-semibold text-foreground">{t('home.demo_title')}</h2>
                    <p className="text-sm text-muted-foreground">
                      {t('home.demo_subtitle', { count: demoTotalDocs })}
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  {publicJobs.map((job) => (
                    <Card
                      key={job.id}
                      onClick={() => openDemoWorkspace(job)}
                      className="p-5 bg-card border-border hover:border-primary/50 transition-colors cursor-pointer group"
                    >
                      <div className="flex items-start gap-3 mb-3">
                        <div className="p-2 bg-primary/10 rounded-lg">
                          <Database className="h-5 w-5 text-primary" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <h3 className="font-semibold text-foreground truncate">
                              {job.name}
                            </h3>
                            <Badge variant="secondary" className="bg-secondary/50 shrink-0">
                              {t('kb.demo_badge')}
                            </Badge>
                          </div>
                          {job.description && (
                            <p className="text-sm text-muted-foreground line-clamp-1 mt-1">
                              {job.description}
                            </p>
                          )}
                        </div>
                        <ChevronRight className="h-4 w-4 text-muted-foreground group-hover:text-primary transition-colors" />
                      </div>
                      <div className="flex items-center gap-4 text-sm text-muted-foreground mb-3">
                        <span>{job.document_count} {t('kb.docs')}</span>
                        <span>{job.chunk_count.toLocaleString()} {t('kb.chunks')}</span>
                      </div>
                      <div className="flex items-center gap-2 text-xs text-primary">
                        <MessageSquare className="w-3.5 h-3.5" />
                        {t('home.demo_browse')}
                      </div>
                    </Card>
                  ))}
                </div>
              </motion.section>
            )}

            {/* Guest-only: use cases + CTA to sign in */}
            {!isAuthenticated && (
              <>
                <motion.section variants={itemVariants} className="mb-12">
                  <Card className="p-6 bg-card border-border">
                    <h3 className="text-lg font-semibold text-white mb-2">{t('home.use_cases_title')}</h3>
                    <p className="text-sm text-muted-foreground mb-4">{t('home.use_cases_subtitle')}</p>
                    <div className="flex flex-wrap gap-2">
                      {[
                        t('home.use_case_research'),
                        t('home.use_case_business'),
                        t('home.use_case_legal'),
                        t('home.use_case_support'),
                        t('home.use_case_product'),
                        t('home.use_case_data'),
                      ].map((label) => (
                        <Badge key={label} variant="secondary" className="bg-secondary/50">
                          {label}
                        </Badge>
                      ))}
                    </div>
                  </Card>
                </motion.section>

                <motion.section variants={itemVariants} className="mb-12">
                  <Card className="p-8 bg-gradient-to-r from-primary/10 to-accent/10 border-primary/20">
                    <div className="flex flex-col md:flex-row items-center justify-between gap-6">
                      <div>
                        <h3 className="text-xl font-semibold text-foreground mb-2">
                          Create Your Own Knowledge Base
                        </h3>
                        <p className="text-muted-foreground">
                          Sign in to upload your own documents and build custom RAG applications.
                        </p>
                      </div>
                      <Link
                        to="/login"
                        className="flex items-center gap-2 px-6 py-3 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors whitespace-nowrap"
                      >
                        Get Started
                        <ChevronRight className="h-4 w-4" />
                      </Link>
                    </div>
                  </Card>
                </motion.section>
              </>
            )}
          </>
        )}
      </div>
    </motion.div>
  );
}
