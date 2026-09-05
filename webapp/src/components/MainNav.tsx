import { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  Home,
  Database,
  MessageSquare,
  Search,
  FolderOpen,
  Briefcase,
  Lightbulb,
  Share2,
  ChevronDown,
  Menu,
  LogIn,
  LogOut
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/sheet';
import { useAuth } from '../contexts/AuthContext';
import KnowledgeBaseSelector from './KnowledgeBaseSelector';
import { useTranslation } from 'react-i18next';
import { setLanguage } from '@/i18n';

export default function MainNav() {
  const location = useLocation();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);
  const { user, isAuthenticated, logout } = useAuth();
  const { t, i18n } = useTranslation();

  const navItems = [
    { path: '/', label: t('nav.home'), icon: Home },
    { path: '/datasets', label: t('nav.dataset'), icon: Database },
    { path: '/chats', label: t('nav.chat'), icon: MessageSquare },
    { path: '/searches', label: t('nav.search'), icon: Search },
    // disabled: stub — see 2026-09-05 audit (Agent page/route disabled, no backend)
    // { path: '/agents', label: t('nav.agent'), icon: Bot },
    { path: '/jobs', label: t('nav.jobs'), icon: Briefcase },
  ];

  const handleLogout = async () => {
    await logout();
    navigate('/');
  };

  return (
    <motion.header
      initial={{ y: -20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.5, ease: "easeOut" }}
      className="fixed top-0 left-0 right-0 z-50 h-[72px] glass border-b border-border"
    >
      <div className="h-full px-4 md:px-6 flex items-center justify-between max-w-[1600px] mx-auto gap-3">
        {/* Logo + Knowledge Base Selector */}
        <div className="flex items-center gap-4 shrink-0">
          <Link to="/" className="flex items-center gap-3 group">
            <motion.div
              className="w-10 h-10 rounded-lg bg-gradient-to-br from-primary to-accent flex items-center justify-center"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              <svg viewBox="0 0 24 24" className="w-6 h-6 text-white" fill="currentColor">
                <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
              </svg>
            </motion.div>
          </Link>

          {/* Knowledge Base Selector */}
          <div className="hidden md:block">
            <KnowledgeBaseSelector />
          </div>
        </div>

        {/* Desktop Navigation */}
        <nav className="hidden xl:flex items-center gap-1 bg-secondary/50 rounded-full p-1 flex-1 justify-center max-w-[700px] overflow-x-auto">
          {navItems.map((item) => {
            const isActive = location.pathname === item.path;
            const Icon = item.icon;
            return (
              <Link key={item.path} to={item.path}>
                <motion.button
                  className={`relative px-4 py-2 rounded-full flex items-center gap-2 text-sm font-medium transition-colors ${
                    isActive 
                      ? 'text-background' 
                      : 'text-muted-foreground hover:text-foreground'
                  }`}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  {isActive && (
                    <motion.div
                      layoutId="activeTab"
                      className="absolute inset-0 bg-white rounded-full"
                      transition={{ type: 'spring', bounce: 0.2, duration: 0.6 }}
                    />
                  )}
                  <span className="relative z-10 flex items-center gap-2">
                    <Icon className="w-4 h-4" />
                    <span className="hidden xl:inline">{item.label}</span>
                  </span>
                </motion.button>
              </Link>
            );
          })}
        </nav>

        {/* Right Side Actions */}
        <div className="flex items-center gap-2 shrink-0">
          {/* disabled: stub — see 2026-09-05 audit (Discord/GitHub icon buttons had no href/handler, did nothing) */}

          {/* Language Selector */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" className="text-sm text-muted-foreground hover:text-foreground gap-1">
                {i18n.language === 'de' ? t('common.german') : t('common.english')} <ChevronDown className="w-4 h-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="bg-card border-border">
              <DropdownMenuItem onClick={() => setLanguage('en')}>
                {t('common.english')}
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setLanguage('de')}>
                {t('common.german')}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>

          {/* disabled: stub — see 2026-09-05 audit (Help button had no popover/navigation; theme toggle changed no attribute, dark mode is the only theme) */}

          {/* User Avatar / Login */}
          {isAuthenticated ? (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" className="relative h-9 w-9 rounded-full">
                  {user?.avatar_url ? (
                    <img
                      src={user.avatar_url}
                      alt={user.name || user.email}
                      className="h-9 w-9 rounded-full object-cover border border-border"
                    />
                  ) : (
                    <div className="h-9 w-9 rounded-full bg-primary/10 flex items-center justify-center border border-border">
                      <span className="text-sm font-medium text-primary">
                        {(user?.name || user?.email || 'U')[0].toUpperCase()}
                      </span>
                    </div>
                  )}
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56 bg-card border-border">
                <div className="px-2 py-1.5">
                  <p className="text-sm font-medium text-foreground">
                    {user?.name || 'User'}
                  </p>
                  <p className="text-xs text-muted-foreground truncate">
                    {user?.email}
                  </p>
                </div>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => navigate('/jobs')}>
                  <Briefcase className="mr-2 h-4 w-4" />
                  {t('common.knowledge_bases')}
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => navigate('/files')}>
                  <FolderOpen className="mr-2 h-4 w-4" />
                  {t('nav.files')}
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => navigate('/insights')}>
                  <Lightbulb className="mr-2 h-4 w-4" />
                  {t('nav.insights')}
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => navigate('/graph')}>
                  <Share2 className="mr-2 h-4 w-4" />
                  {t('nav.graph')}
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => navigate('/settings/data-sources')}>
                  {t('common.data_sources')}
                </DropdownMenuItem>
                {/* disabled: stub — see 2026-09-05 audit (Model providers / MCP / Team settings pages are mock UI with no backend) */}
                <DropdownMenuItem onClick={() => navigate('/settings/profile')}>
                  {t('common.profile')}
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={handleLogout} className="text-destructive">
                  <LogOut className="mr-2 h-4 w-4" />
                  {t('common.sign_out')}
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          ) : (
            <Button
              variant="default"
              size="sm"
              onClick={() => navigate('/login')}
              className="gap-2"
            >
              <LogIn className="h-4 w-4" />
              <span className="hidden sm:inline">{t('common.sign_in')}</span>
            </Button>
          )}

          {/* Mobile Menu */}
          <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
            <SheetTrigger asChild className="xl:hidden">
              <Button variant="ghost" size="icon">
                <Menu className="w-6 h-6" />
              </Button>
            </SheetTrigger>
            <SheetContent side="right" className="w-[300px] bg-background border-border">
              <nav className="flex flex-col gap-2 mt-8">
                {navItems.map((item) => {
                  const isActive = location.pathname === item.path;
                  const Icon = item.icon;
                  return (
                    <Link
                      key={item.path}
                      to={item.path}
                      onClick={() => setMobileOpen(false)}
                      className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                        isActive
                          ? 'bg-primary text-primary-foreground'
                          : 'text-muted-foreground hover:text-foreground hover:bg-secondary'
                      }`}
                    >
                      <Icon className="w-5 h-5" />
                      {item.label}
                    </Link>
                  );
                })}
              </nav>
            </SheetContent>
          </Sheet>
        </div>
      </div>
    </motion.header>
  );
}
