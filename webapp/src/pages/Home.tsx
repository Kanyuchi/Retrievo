import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { Database, MessageSquare, ChevronRight, Loader2, FileText, Layers, Calendar } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { useStats } from '@/hooks/useApi';
import { Badge } from '@/components/ui/badge';

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
  const { data: stats, loading, error } = useStats();

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
            Welcome to <span className="gradient-text">RAGFlow</span>
          </h1>
          <p className="mt-4 text-muted-foreground text-lg">
            Academic Literature Review RAG System
          </p>
        </motion.section>

        {/* Stats Section */}
        <motion.section variants={itemVariants} className="mb-12">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-8 h-8 animate-spin text-primary" />
            </div>
          ) : error ? (
            <div className="text-center py-12 text-destructive">
              Failed to load stats: {error}
            </div>
          ) : stats ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
              <Card className="p-6 bg-card border-border">
                <div className="flex items-center gap-3 mb-2">
                  <FileText className="w-5 h-5 text-primary" />
                  <span className="text-muted-foreground text-sm">Total Papers</span>
                </div>
                <p className="text-3xl font-bold text-white">{stats.total_papers}</p>
              </Card>
              
              <Card className="p-6 bg-card border-border">
                <div className="flex items-center gap-3 mb-2">
                  <Layers className="w-5 h-5 text-primary" />
                  <span className="text-muted-foreground text-sm">Total Chunks</span>
                </div>
                <p className="text-3xl font-bold text-white">{stats.total_chunks.toLocaleString()}</p>
              </Card>
              
              <Card className="p-6 bg-card border-border">
                <div className="flex items-center gap-3 mb-2">
                  <Database className="w-5 h-5 text-primary" />
                  <span className="text-muted-foreground text-sm">Phases</span>
                </div>
                <p className="text-3xl font-bold text-white">{Object.keys(stats.phases).length}</p>
              </Card>
              
              <Card className="p-6 bg-card border-border">
                <div className="flex items-center gap-3 mb-2">
                  <Calendar className="w-5 h-5 text-primary" />
                  <span className="text-muted-foreground text-sm">Year Range</span>
                </div>
                <p className="text-3xl font-bold text-white">
                  {stats.year_range.min}-{stats.year_range.max}
                </p>
              </Card>
            </div>
          ) : null}
        </motion.section>

        {/* Topics & Phases */}
        {stats && (
          <motion.section variants={itemVariants} className="mb-12">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card className="p-6 bg-card border-border">
                <h3 className="text-lg font-semibold text-white mb-4">Topics</h3>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(stats.topics).map(([topic, count]) => (
                    <Badge key={topic} variant="secondary" className="bg-secondary/50">
                      {topic} ({count})
                    </Badge>
                  ))}
                </div>
              </Card>
              
              <Card className="p-6 bg-card border-border">
                <h3 className="text-lg font-semibold text-white mb-4">Phases</h3>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(stats.phases).map(([phase, count]) => (
                    <Badge key={phase} variant="secondary" className="bg-secondary/50">
                      {phase} ({count})
                    </Badge>
                  ))}
                </div>
              </Card>
            </div>
          </motion.section>
        )}

        {/* Dataset Section */}
        <motion.section variants={itemVariants} className="mb-12">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center">
              <Database className="w-5 h-5 text-primary" />
            </div>
            <h2 className="text-2xl font-semibold text-white">Dataset</h2>
          </div>
          
          <Link to="/datasets">
            <motion.div
              whileHover={{ y: -4, borderColor: 'hsl(var(--primary))' }}
              transition={{ duration: 0.3 }}
            >
              <Card className="w-full max-w-[280px] h-[100px] bg-card border-border hover:border-primary/50 transition-colors cursor-pointer flex items-center justify-center group">
                <div className="flex items-center gap-2 text-muted-foreground group-hover:text-foreground transition-colors">
                  <span className="text-sm font-medium">See All Papers</span>
                  <ChevronRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                </div>
              </Card>
            </motion.div>
          </Link>
        </motion.section>

        {/* Chat Apps Section */}
        <motion.section variants={itemVariants}>
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center">
                <MessageSquare className="w-5 h-5 text-primary" />
              </div>
              <h2 className="text-2xl font-semibold text-white">Chat Apps</h2>
            </div>
            
            {/* App Type Tabs */}
            <div className="hidden sm:flex items-center gap-1 bg-secondary/50 rounded-lg p-1">
              <Link to="/chats">
                <button className="px-4 py-1.5 rounded-md text-sm font-medium bg-background text-foreground transition-colors">
                  Chat Apps
                </button>
              </Link>
              <Link to="/searches">
                <button className="px-4 py-1.5 rounded-md text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
                  Search Apps
                </button>
              </Link>
              <Link to="/agents">
                <button className="px-4 py-1.5 rounded-md text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
                  Agent
                </button>
              </Link>
            </div>
          </div>
          
          <Link to="/chats">
            <motion.div
              whileHover={{ y: -4, borderColor: 'hsl(var(--primary))' }}
              transition={{ duration: 0.3 }}
            >
              <Card className="w-full max-w-[280px] h-[100px] bg-card border-border hover:border-primary/50 transition-colors cursor-pointer flex items-center justify-center group">
                <div className="flex items-center gap-2 text-muted-foreground group-hover:text-foreground transition-colors">
                  <span className="text-sm font-medium">Start Chat</span>
                  <ChevronRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                </div>
              </Card>
            </motion.div>
          </Link>
        </motion.section>
      </div>
    </motion.div>
  );
}
