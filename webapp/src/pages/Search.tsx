import { useState } from 'react';
import { motion } from 'framer-motion';
import { Search as SearchIcon, Loader2, FileText, ChevronDown, Filter } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useSearch, useStats } from '@/hooks/useApi';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

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

export default function Search() {
  const [query, setQuery] = useState('');
  const [phaseFilter, setPhaseFilter] = useState<string>('');
  const [topicFilter, setTopicFilter] = useState<string>('');
  const { results, loading, error, search } = useSearch();
  const { data: stats } = useStats();

  const phases = stats ? Object.keys(stats.phases) : [];
  const topics = stats ? Object.keys(stats.topics) : [];

  const handleSearch = async () => {
    if (!query.trim()) return;
    await search({
      query: query.trim(),
      n_results: 10,
      phase_filter: phaseFilter || undefined,
      topic_filter: topicFilter || undefined,
    });
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className="min-h-[calc(100vh-72px)] bg-background px-4 md:px-8 lg:px-12 py-6"
    >
      <div className="max-w-[1400px] mx-auto">
        {/* Header */}
        <motion.div 
          variants={itemVariants}
          className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8"
        >
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center">
              <SearchIcon className="w-5 h-5 text-primary" />
            </div>
            <h1 className="text-2xl font-semibold text-white">Search Apps</h1>
          </div>
        </motion.div>

        {/* Search Input */}
        <motion.div variants={itemVariants} className="mb-8">
          <Card className="p-6 bg-card border-border">
            <div className="flex flex-col md:flex-row gap-4">
              <div className="flex-1 relative">
                <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
                <Input 
                  placeholder="Enter your search query..." 
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={handleKeyDown}
                  className="pl-12 h-12 bg-secondary/50 border-border focus:border-primary text-lg"
                />
              </div>
              
              {/* Phase Filter */}
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" className="border-border bg-secondary/50 hover:bg-secondary gap-2 h-12">
                    <Filter className="w-4 h-4" />
                    {phaseFilter || 'Phase'}
                    <ChevronDown className="w-4 h-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="bg-card border-border">
                  <DropdownMenuItem onClick={() => setPhaseFilter('')}>All Phases</DropdownMenuItem>
                  {phases.map(phase => (
                    <DropdownMenuItem key={phase} onClick={() => setPhaseFilter(phase)}>
                      {phase}
                    </DropdownMenuItem>
                  ))}
                </DropdownMenuContent>
              </DropdownMenu>

              {/* Topic Filter */}
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" className="border-border bg-secondary/50 hover:bg-secondary gap-2 h-12">
                    <Filter className="w-4 h-4" />
                    {topicFilter || 'Topic'}
                    <ChevronDown className="w-4 h-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="bg-card border-border">
                  <DropdownMenuItem onClick={() => setTopicFilter('')}>All Topics</DropdownMenuItem>
                  {topics.map(topic => (
                    <DropdownMenuItem key={topic} onClick={() => setTopicFilter(topic)}>
                      {topic}
                    </DropdownMenuItem>
                  ))}
                </DropdownMenuContent>
              </DropdownMenu>
              
              <Button 
                onClick={handleSearch}
                disabled={loading || !query.trim()}
                className="h-12 px-8 bg-white text-background hover:bg-white/90"
              >
                {loading ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  'Search'
                )}
              </Button>
            </div>
          </Card>
        </motion.div>

        {/* Error State */}
        {error && (
          <motion.div variants={itemVariants} className="mb-8">
            <Card className="p-6 bg-destructive/10 border-destructive/50">
              <p className="text-destructive">Search failed: {error}</p>
            </Card>
          </motion.div>
        )}

        {/* Results */}
        {results.length > 0 && (
          <motion.div variants={itemVariants}>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-white">
                Results ({results.length})
              </h2>
            </div>
            
            <div className="space-y-4">
              {results.map((result, index) => (
                <Card key={index} className="p-6 bg-card border-border hover:border-primary/50 transition-colors">
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <FileText className="w-5 h-5 text-primary" />
                      <h3 className="text-lg font-semibold text-white">{result.title}</h3>
                    </div>
                    <Badge variant="secondary" className="bg-primary/20 text-primary">
                      Score: {(result.relevance_score * 100).toFixed(1)}%
                    </Badge>
                  </div>
                  
                  <div className="flex flex-wrap gap-2 mb-3">
                    {result.authors && (
                      <Badge variant="secondary" className="bg-secondary/50">
                        {result.authors}
                      </Badge>
                    )}
                    {result.year && (
                      <Badge variant="secondary" className="bg-secondary/50">
                        {result.year}
                      </Badge>
                    )}
                    {result.phase && (
                      <Badge variant="secondary" className="bg-secondary/50">
                        {result.phase}
                      </Badge>
                    )}
                    {result.topic && (
                      <Badge variant="secondary" className="bg-secondary/50">
                        {result.topic}
                      </Badge>
                    )}
                  </div>
                  
                  <p className="text-muted-foreground text-sm line-clamp-3">
                    {result.chunk_text}
                  </p>
                </Card>
              ))}
            </div>
          </motion.div>
        )}

        {/* Empty State */}
        {!loading && results.length === 0 && !error && query && (
          <motion.div 
            variants={itemVariants}
            className="flex flex-col items-center justify-center py-32"
          >
            <div className="w-16 h-16 rounded-full bg-secondary/50 flex items-center justify-center mb-4">
              <SearchIcon className="w-8 h-8 text-muted-foreground" />
            </div>
            <p className="text-muted-foreground text-sm">No results found</p>
          </motion.div>
        )}

        {/* Initial State */}
        {!loading && results.length === 0 && !query && (
          <motion.div 
            variants={itemVariants}
            className="flex flex-col items-center justify-center py-32"
          >
            <div className="w-16 h-16 rounded-full bg-secondary/50 flex items-center justify-center mb-4">
              <SearchIcon className="w-8 h-8 text-muted-foreground" />
            </div>
            <p className="text-muted-foreground text-sm">Enter a query to search the literature</p>
          </motion.div>
        )}
      </div>
    </motion.div>
  );
}
