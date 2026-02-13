import { motion } from 'framer-motion';
import { useEffect, useMemo, useState } from 'react';
import SettingsSidebar from '@/components/SettingsSidebar';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';
import { api } from '@/lib/api';
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

const dataSources = [
  {
    id: 'google_drive',
    name: 'Google Drive',
    description: 'Connect Google Drive via OAuth and sync folders or shared drives.',
    color: '#0066DA',
    fields: [
      { key: 'client_id', label: 'Client ID' },
      { key: 'client_secret', label: 'Client Secret' },
      { key: 'redirect_uri', label: 'Redirect URI' },
    ],
  },
  {
    id: 'onedrive',
    name: 'OneDrive / SharePoint',
    description: 'Connect Microsoft OneDrive or SharePoint with tenant OAuth.',
    color: '#2563EB',
    fields: [
      { key: 'tenant_id', label: 'Tenant ID' },
      { key: 'client_id', label: 'Client ID' },
      { key: 'client_secret', label: 'Client Secret' },
      { key: 'redirect_uri', label: 'Redirect URI' },
    ],
  },
  {
    id: 'notion',
    name: 'Notion',
    description: 'Sync pages and databases from Notion for retrieval.',
    color: '#000000',
    fields: [
      { key: 'integration_token', label: 'Integration Token' },
    ],
  },
  {
    id: 'github',
    name: 'GitHub',
    description: 'Index repositories, issues, and documentation from GitHub.',
    color: '#0F172A',
    fields: [
      { key: 'client_id', label: 'Client ID' },
      { key: 'client_secret', label: 'Client Secret' },
      { key: 'org', label: 'Organization (optional)' },
      { key: 'repo', label: 'Repository (optional)' },
      { key: 'redirect_uri', label: 'Redirect URI' },
    ],
  },
  {
    id: 'confluence',
    name: 'Confluence',
    description: 'Integrate your Confluence workspace to search documentation.',
    color: '#0052CC',
    fields: [
      { key: 'base_url', label: 'Base URL' },
      { key: 'email', label: 'Account Email' },
      { key: 'api_token', label: 'API Token' },
    ],
  },
];

export default function DataSources() {
  const { accessToken, isAuthenticated } = useAuth();
  const [configs, setConfigs] = useState<Record<string, Record<string, string>>>({});
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!isAuthenticated || !accessToken) return;
    setLoading(true);
    api.listDataSources(accessToken)
      .then((res) => {
        const next: Record<string, Record<string, string>> = {};
        res.connections.forEach((conn) => {
          next[conn.provider] = conn.config || {};
        });
        setConfigs(next);
      })
      .catch(() => {
        toast.error('Failed to load data source settings');
      })
      .finally(() => setLoading(false));
  }, [accessToken, isAuthenticated]);

  const statusFor = (providerId: string) => {
    const cfg = configs[providerId];
    if (!cfg) return 'Not configured';
    const hasValue = Object.values(cfg).some((v) => v && v.trim() !== '');
    return hasValue ? 'Configured' : 'Not configured';
  };

  const updateField = (providerId: string, key: string, value: string) => {
    setConfigs((prev) => ({
      ...prev,
      [providerId]: {
        ...(prev[providerId] || {}),
        [key]: value,
      },
    }));
  };

  const saveProvider = async (providerId: string) => {
    if (!accessToken) return;
    const config = configs[providerId] || {};
    try {
      await api.upsertDataSource(providerId, config, accessToken);
      toast.success(`${providerId} configured`);
    } catch {
      toast.error(`Failed to save ${providerId} configuration`);
    }
  };

  const clearProvider = async (providerId: string) => {
    if (!accessToken) return;
    try {
      await api.deleteDataSource(providerId, accessToken);
      setConfigs((prev) => ({ ...prev, [providerId]: {} }));
      toast.success(`${providerId} cleared`);
    } catch {
      toast.error(`Failed to clear ${providerId}`);
    }
  };

  const sourceCards = useMemo(() => dataSources, []);

  return (
    <div className="flex min-h-[calc(100vh-72px)]">
      <SettingsSidebar />

      <motion.main
        variants={containerVariants}
        initial="hidden"
        animate="visible"
        className="flex-1 p-8"
      >
        <motion.div variants={itemVariants} className="mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">Data sources</h1>
          <p className="text-muted-foreground">Configure and connect your data sources</p>
        </motion.div>

        <motion.div variants={itemVariants}>
          <h2 className="text-xl font-semibold text-white mb-4">Available sources</h2>
          <p className="text-muted-foreground mb-6">
            {loading ? 'Loading connections…' : 'Save credentials to enable future sync.'}
          </p>
        </motion.div>

        <motion.div
          variants={containerVariants}
          className="grid grid-cols-1 md:grid-cols-2 gap-4"
        >
          {sourceCards.map((source) => (
            <motion.div
              key={source.id}
              variants={itemVariants}
              whileHover={{ y: -4, borderColor: source.color }}
              transition={{ duration: 0.3 }}
            >
              <Card className="p-5 bg-card border-border hover:shadow-lg transition-all">
                <div className="flex items-start justify-between gap-4 mb-4">
                  <div>
                    <h3 className="text-lg font-semibold text-white mb-1">
                      {source.name}
                    </h3>
                    <p className="text-sm text-muted-foreground leading-relaxed">
                      {source.description}
                    </p>
                  </div>
                  <div className="text-xs px-2 py-1 rounded-full bg-secondary/40 text-muted-foreground">
                    {statusFor(source.id)}
                  </div>
                </div>

                <div className="space-y-3">
                  {source.fields.map((field) => (
                    <div key={field.key}>
                      <label className="block text-xs text-muted-foreground mb-1">{field.label}</label>
                      <Input
                        type={field.key.includes('secret') || field.key.includes('token') ? 'password' : 'text'}
                        value={configs[source.id]?.[field.key] || ''}
                        onChange={(e) => updateField(source.id, field.key, e.target.value)}
                        placeholder={field.label}
                      />
                    </div>
                  ))}
                </div>

                <div className="flex items-center gap-2 mt-4">
                  <Button size="sm" onClick={() => saveProvider(source.id)}>
                    Save
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => clearProvider(source.id)}>
                    Clear
                  </Button>
                </div>
              </Card>
            </motion.div>
          ))}
        </motion.div>
      </motion.main>
    </div>
  );
}
