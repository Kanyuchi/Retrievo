import { Link, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import { 
  Database, 
  Box, 
  Cpu, 
  Users, 
  User, 
  Sun, 
  Moon,
  LogOut,
  ChevronRight,
  Home
} from 'lucide-react';
import { Button } from '@/components/ui/button';

const menuItems = [
  { path: '/settings/data-sources', label: 'Data sources', icon: Database },
  { path: '/settings/model-providers', label: 'Model providers', icon: Box },
  { path: '/settings/mcp', label: 'MCP', icon: Cpu },
  { path: '/settings/team', label: 'Team', icon: Users },
  { path: '/settings/profile', label: 'Profile', icon: User },
];

export default function SettingsSidebar() {
  const location = useLocation();

  return (
    <aside className="w-[280px] min-h-[calc(100vh-72px)] bg-card border-r border-border flex flex-col">
      {/* Breadcrumb */}
      <div className="px-4 py-4 border-b border-border">
        <div className="flex items-center gap-2 text-sm">
          <Link to="/" className="text-muted-foreground hover:text-foreground transition-colors">
            <Home className="w-4 h-4" />
          </Link>
          <ChevronRight className="w-4 h-4 text-muted-foreground" />
          <span className="text-foreground">Profile</span>
        </div>
      </div>

      {/* User Profile */}
      <div className="px-4 py-6 border-b border-border">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-full bg-secondary flex items-center justify-center border border-border">
            <User className="w-6 h-6 text-muted-foreground" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-foreground truncate">shaunkudzi@gmail.com</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-2 py-4">
        <ul className="space-y-1">
          {menuItems.map((item) => {
            const isActive = location.pathname === item.path;
            const Icon = item.icon;
            return (
              <li key={item.path}>
                <Link to={item.path}>
                  <motion.div
                    className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors relative ${
                      isActive
                        ? 'text-foreground bg-secondary'
                        : 'text-muted-foreground hover:text-foreground hover:bg-secondary/50'
                    }`}
                    whileHover={{ x: 2 }}
                    transition={{ duration: 0.2 }}
                  >
                    {isActive && (
                      <motion.div
                        layoutId="sidebarActive"
                        className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-6 bg-primary rounded-full"
                        transition={{ type: 'spring', bounce: 0.2, duration: 0.6 }}
                      />
                    )}
                    <Icon className="w-5 h-5" />
                    {item.label}
                  </motion.div>
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* Bottom Actions */}
      <div className="p-4 border-t border-border space-y-3">
        {/* Theme Toggle */}
        <div className="flex items-center justify-center gap-2 p-2 bg-secondary/50 rounded-lg">
          <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-foreground">
            <Sun className="w-4 h-4" />
          </Button>
          <Button variant="ghost" size="icon" className="h-8 w-8 text-foreground bg-secondary">
            <Moon className="w-4 h-4" />
          </Button>
        </div>

        {/* Log Out */}
        <Button 
          variant="outline" 
          className="w-full border-border bg-secondary/50 hover:bg-secondary text-muted-foreground hover:text-foreground"
        >
          <LogOut className="w-4 h-4 mr-2" />
          Log out
        </Button>
      </div>
    </aside>
  );
}
