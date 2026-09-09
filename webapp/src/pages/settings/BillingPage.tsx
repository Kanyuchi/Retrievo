import { useCallback, useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useTranslation } from 'react-i18next';
import { Check, Loader2, Minus, Plus } from 'lucide-react';
import SettingsSidebar from '@/components/SettingsSidebar';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { toast } from '@/lib/toast';
import { api } from '@/lib/api';
import type { BillingStatusResponse } from '@/lib/api';
import { useAuth } from '@/contexts/AuthContext';

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
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
      duration: 0.5,
    },
  },
};

type PlanTier = BillingStatusResponse['plan_tier'];

// Backend tier -> display label. Team subscriptions map to the existing
// 'enterprise' QUOTA_LIMITS tier (a dedicated 'team' tier is a later
// refinement) — the UI always calls it "Team".
function planLabel(tier: PlanTier, t: (key: string) => string): string {
  if (tier === 'pro') return t('billing.plan_pro_name');
  if (tier === 'enterprise') return t('billing.plan_team_name');
  return t('billing.plan_free_name');
}

const MIN_SEATS = 3;
const MAX_SEATS = 100;

export default function BillingPage() {
  const { t } = useTranslation();
  const { accessToken, isAuthenticated } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const [status, setStatus] = useState<BillingStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [academic, setAcademic] = useState(false);
  const [seats, setSeats] = useState(MIN_SEATS);
  const [creatingPlan, setCreatingPlan] = useState<'pro' | 'team' | null>(null);
  const [portalLoading, setPortalLoading] = useState(false);

  const loadStatus = useCallback(async () => {
    if (!isAuthenticated) return;
    setLoading(true);
    try {
      const response = await api.getBillingStatus(accessToken || undefined);
      setStatus(response);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : t('billing.load_failed'));
    } finally {
      setLoading(false);
    }
  }, [accessToken, isAuthenticated, t]);

  useEffect(() => {
    loadStatus();
  }, [loadStatus]);

  // Handle the ?status=success|cancelled redirect back from Stripe Checkout.
  useEffect(() => {
    const checkoutStatus = searchParams.get('status');
    if (!checkoutStatus) return;

    if (checkoutStatus === 'success') {
      toast.success(t('billing.status_success'));
      loadStatus();
    } else if (checkoutStatus === 'cancelled') {
      toast.info(t('billing.status_cancelled'));
    }

    // Strip the query param so a refresh doesn't re-trigger the toast.
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        next.delete('status');
        return next;
      },
      { replace: true }
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleCheckout = async (plan: 'pro' | 'team') => {
    setCreatingPlan(plan);
    try {
      const response = await api.createCheckout(
        plan,
        plan === 'team' ? seats : undefined,
        academic,
        accessToken || undefined
      );
      window.location.href = response.url;
    } catch (err) {
      toast.error(err instanceof Error ? err.message : t('billing.checkout_failed'));
      setCreatingPlan(null);
    }
  };

  const handlePortal = async () => {
    setPortalLoading(true);
    try {
      const response = await api.createPortalSession(accessToken || undefined);
      window.location.href = response.url;
    } catch (err) {
      toast.error(err instanceof Error ? err.message : t('billing.portal_failed'));
      setPortalLoading(false);
    }
  };

  const currentTier = status?.plan_tier ?? 'free';

  return (
    <div className="flex min-h-[calc(100vh-72px)]">
      <SettingsSidebar />

      <motion.main
        variants={containerVariants}
        initial="hidden"
        animate="visible"
        className="flex-1 p-8"
      >
        <div className="max-w-[900px]">
          <motion.div variants={itemVariants} className="mb-8">
            <h1 className="text-2xl font-bold text-white mb-2">{t('billing.title')}</h1>
            <p className="text-muted-foreground">{t('billing.subtitle')}</p>
          </motion.div>

          {/* Current plan banner */}
          <motion.div variants={itemVariants} className="mb-6">
            <Card className="px-6 py-4 flex flex-wrap items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                {loading ? (
                  <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
                ) : (
                  <Badge variant="secondary" className="text-sm px-3 py-1">
                    {planLabel(currentTier, t)}
                  </Badge>
                )}
                <p className="text-sm text-muted-foreground">
                  {t('billing.current_plan_banner', { plan: planLabel(currentTier, t) })}
                </p>
              </div>
              {status?.has_customer && (
                <Button
                  variant="outline"
                  className="border-border bg-secondary/50 hover:bg-secondary"
                  onClick={handlePortal}
                  disabled={portalLoading}
                >
                  {portalLoading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin mr-2" />
                      {t('billing.opening_portal')}
                    </>
                  ) : (
                    t('billing.manage_subscription')
                  )}
                </Button>
              )}
            </Card>
          </motion.div>

          {/* Academic / NGO discount checkbox */}
          <motion.div variants={itemVariants} className="mb-6">
            <label className="flex items-start gap-3 p-4 rounded-lg border border-border bg-secondary/30 cursor-pointer">
              <Checkbox
                checked={academic}
                onCheckedChange={(checked) => setAcademic(checked === true)}
                className="mt-0.5"
              />
              <div>
                <p className="text-sm font-medium text-foreground">{t('billing.academic_label')}</p>
                <p className="text-xs text-muted-foreground">{t('billing.academic_hint')}</p>
              </div>
            </label>
          </motion.div>

          {/* Plan cards */}
          <motion.div variants={itemVariants} className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Free */}
            <Card className="p-6 flex flex-col gap-4 border-border">
              <div>
                <h3 className="text-lg font-semibold text-foreground">{t('billing.plan_free_name')}</h3>
                <p className="text-2xl font-bold text-foreground mt-1">
                  {t('billing.plan_free_price')}
                </p>
              </div>
              <ul className="space-y-2 text-sm text-muted-foreground flex-1">
                <FeatureItem text={t('billing.feature_kbs', { count: 3 })} />
                <FeatureItem text={t('billing.feature_docs', { count: 50 })} />
                <FeatureItem text={t('billing.feature_storage', { size: '100MB' })} />
              </ul>
              {currentTier === 'free' ? (
                <Button variant="outline" disabled className="w-full">
                  {t('billing.current_plan')}
                </Button>
              ) : (
                <div className="h-9" />
              )}
            </Card>

            {/* Pro */}
            <Card className="p-6 flex flex-col gap-4 border-border">
              <div>
                <h3 className="text-lg font-semibold text-foreground">{t('billing.plan_pro_name')}</h3>
                <p className="text-2xl font-bold text-foreground mt-1">
                  {t('billing.plan_pro_price')}
                  <span className="text-sm font-normal text-muted-foreground">
                    {t('billing.per_month')}
                  </span>
                </p>
              </div>
              <ul className="space-y-2 text-sm text-muted-foreground flex-1">
                <FeatureItem text={t('billing.feature_kbs', { count: 20 })} />
                <FeatureItem text={t('billing.feature_docs', { count: 500 })} />
                <FeatureItem text={t('billing.feature_storage', { size: '5GB' })} />
              </ul>
              {currentTier === 'pro' ? (
                <Button variant="outline" disabled className="w-full">
                  {t('billing.current_plan')}
                </Button>
              ) : (
                <Button
                  className="w-full"
                  onClick={() => handleCheckout('pro')}
                  disabled={creatingPlan !== null}
                >
                  {creatingPlan === 'pro' ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin mr-2" />
                      {t('billing.creating_checkout')}
                    </>
                  ) : (
                    t('billing.upgrade_to', { plan: t('billing.plan_pro_name') })
                  )}
                </Button>
              )}
            </Card>

            {/* Team */}
            <Card className="p-6 flex flex-col gap-4 border-border">
              <div>
                <h3 className="text-lg font-semibold text-foreground">{t('billing.plan_team_name')}</h3>
                <p className="text-2xl font-bold text-foreground mt-1">
                  {t('billing.plan_team_price')}
                  <span className="text-sm font-normal text-muted-foreground">
                    {t('billing.per_seat_month')}
                  </span>
                </p>
              </div>
              <ul className="space-y-2 text-sm text-muted-foreground flex-1">
                <FeatureItem text={t('billing.feature_kbs_unlimited')} />
                <FeatureItem text={t('billing.feature_docs_unlimited')} />
                <FeatureItem text={t('billing.feature_storage_unlimited')} />
                <FeatureItem text={t('billing.feature_shared_workspaces')} />
              </ul>

              {currentTier !== 'enterprise' && (
                <div className="flex items-center justify-between gap-3">
                  <span className="text-xs text-muted-foreground">{t('billing.seats_label')}</span>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="icon-sm"
                      onClick={() => setSeats((s) => Math.max(MIN_SEATS, s - 1))}
                      disabled={seats <= MIN_SEATS}
                      aria-label="Decrease seats"
                    >
                      <Minus className="w-3.5 h-3.5" />
                    </Button>
                    <span className="w-8 text-center text-sm text-foreground tabular-nums">
                      {seats}
                    </span>
                    <Button
                      variant="outline"
                      size="icon-sm"
                      onClick={() => setSeats((s) => Math.min(MAX_SEATS, s + 1))}
                      disabled={seats >= MAX_SEATS}
                      aria-label="Increase seats"
                    >
                      <Plus className="w-3.5 h-3.5" />
                    </Button>
                  </div>
                </div>
              )}

              {currentTier === 'enterprise' ? (
                <Button variant="outline" disabled className="w-full">
                  {t('billing.current_plan')}
                </Button>
              ) : (
                <Button
                  className="w-full"
                  onClick={() => handleCheckout('team')}
                  disabled={creatingPlan !== null}
                >
                  {creatingPlan === 'team' ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin mr-2" />
                      {t('billing.creating_checkout')}
                    </>
                  ) : (
                    t('billing.upgrade_to', { plan: t('billing.plan_team_name') })
                  )}
                </Button>
              )}
            </Card>
          </motion.div>
        </div>
      </motion.main>
    </div>
  );
}

function FeatureItem({ text }: { text: string }) {
  return (
    <li className="flex items-center gap-2">
      <Check className="w-4 h-4 text-primary flex-shrink-0" />
      <span>{text}</span>
    </li>
  );
}
