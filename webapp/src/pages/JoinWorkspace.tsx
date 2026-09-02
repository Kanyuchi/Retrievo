import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { api } from '../lib/api';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import { AlertCircle, ArrowLeft } from 'lucide-react';

export default function JoinWorkspace() {
  const { token } = useParams<{ token: string }>();
  const navigate = useNavigate();
  const { isAuthenticated, isLoading: authLoading, accessToken } = useAuth();
  const { t } = useTranslation();

  const [error, setError] = useState<string | null>(null);
  const hasJoined = useRef(false);

  // Not authenticated: redirect to login, preserving the invite link as returnTo.
  useEffect(() => {
    if (!authLoading && !isAuthenticated && token) {
      navigate(`/login?redirect=${encodeURIComponent(`/join/${token}`)}`);
    }
  }, [authLoading, isAuthenticated, navigate, token]);

  useEffect(() => {
    if (authLoading || !isAuthenticated || !token || hasJoined.current) return;
    hasJoined.current = true;

    const join = async () => {
      try {
        const result = await api.joinWorkspace(token, accessToken || undefined);
        toast.success(
          t('join_workspace.success', { name: result.name, role: result.role })
        );
        navigate(`/jobs/${result.job_id}`, { replace: true });
      } catch (err) {
        setError(err instanceof Error ? err.message : t('join_workspace.error_title'));
      }
    };

    join();
  }, [authLoading, isAuthenticated, token, accessToken, navigate, t]);

  if (authLoading || (isAuthenticated && !error)) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4 bg-background">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
        <p className="text-muted-foreground">{t('join_workspace.joining')}</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background p-8">
      <div className="max-w-xl mx-auto">
        <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-6">
          <div className="flex items-center gap-3 mb-2">
            <AlertCircle className="h-6 w-6 text-destructive" />
            <h2 className="text-lg font-semibold text-destructive">
              {t('join_workspace.error_title')}
            </h2>
          </div>
          <p className="text-destructive/80">{error}</p>
          <Link
            to="/"
            className="inline-flex items-center gap-2 mt-4 text-primary hover:text-primary/80"
          >
            <ArrowLeft className="h-4 w-4" />
            {t('join_workspace.back_home')}
          </Link>
        </div>
      </div>
    </div>
  );
}
