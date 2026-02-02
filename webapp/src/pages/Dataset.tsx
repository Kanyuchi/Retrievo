import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Database, Filter, Search, ChevronLeft, ChevronRight, FileText, Loader2, Folder } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Badge } from '@/components/ui/badge';
import { usePapers, useStats } from '@/hooks/useApi';
import { useKnowledgeBase } from '@/contexts/KnowledgeBaseContext';
import { useAuth } from '@/contexts/AuthContext';
import { api } from '@/lib/api';
import type { JobDocument } from '@/lib/api';

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

// Unified paper type for display
interface DisplayPaper {
  doc_id: string;
  title: string;
  authors?: string;
  year?: number;
  phase?: string;
  topic?: string;
}

export default function Dataset() {
  const { selectedKB, isDefaultSelected } = useKnowledgeBase();
  const { accessToken } = useAuth();

  const [searchQuery, setSearchQuery] = useState('');
  const [phaseFilter, setPhaseFilter] = useState<string>('');
  const [topicFilter, setTopicFilter] = useState<string>('');
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(50);

  // For default collection, use existing hooks
  const { data: papersData, loading: defaultLoading, error: defaultError } = usePapers(
    isDefaultSelected ? { limit: 500 } : undefined
  );
  const { data: defaultStats } = useStats();

  // For job collections, load manually
  const [jobPapers, setJobPapers] = useState<DisplayPaper[]>([]);
  const [jobStats, setJobStats] = useState<{ phases: Record<string, number>; topics: Record<string, number> } | null>(null);
  const [jobLoading, setJobLoading] = useState(false);
  const [jobError, setJobError] = useState<string | null>(null);

  // Load job data when KB changes
  useEffect(() => {
    if (!isDefaultSelected && selectedKB && accessToken) {
      loadJobData();
    }
  }, [selectedKB?.id, isDefaultSelected, accessToken]);

  const loadJobData = async () => {
    if (!selectedKB || isDefaultSelected) return;

    setJobLoading(true);
    setJobError(null);

    try {
      // Load documents and stats in parallel
      const [docsResponse, statsResponse] = await Promise.all([
        api.getJobDocuments(selectedKB.id as number, { limit: 500 }, accessToken || undefined),
        api.getJobStats(selectedKB.id as number, accessToken || undefined),
      ]);

      setJobPapers(docsResponse.documents.map((doc: JobDocument) => ({
        doc_id: doc.doc_id,
        title: doc.title || doc.filename,
        authors: doc.authors || undefined,
        year: doc.year || undefined,
        phase: doc.phase || undefined,
        topic: doc.topic_category || undefined,
      })));

      setJobStats({ phases: statsResponse.phases, topics: statsResponse.topics });
    } catch (err) {
      console.error('Failed to load job data:', err);
      setJobError(err instanceof Error ? err.message : 'Failed to load data');
    } finally {
      setJobLoading(false);
    }
  };

  // Reset filters when KB changes
  useEffect(() => {
    setPhaseFilter('');
    setTopicFilter('');
    setSearchQuery('');
    setCurrentPage(1);
  }, [selectedKB?.id]);

  // Use appropriate data based on selected KB
  const loading = isDefaultSelected ? defaultLoading : jobLoading;
  const error = isDefaultSelected ? defaultError : jobError;
  const stats = isDefaultSelected ? defaultStats : jobStats;

  const papers: DisplayPaper[] = isDefaultSelected
    ? (papersData?.papers || []).map(p => ({
        doc_id: p.doc_id,
        title: p.title,
        authors: p.authors,
        year: p.year,
        phase: p.phase,
        topic: p.topic,
      }))
    : jobPapers;

  // Filter papers based on search and filters
  const filteredPapers = papers.filter(paper => {
    const matchesSearch = !searchQuery ||
      paper.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      paper.authors?.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesPhase = !phaseFilter || paper.phase === phaseFilter;
    const matchesTopic = !topicFilter || paper.topic === topicFilter;

    return matchesSearch && matchesPhase && matchesTopic;
  });

  // Pagination
  const totalPages = Math.ceil(filteredPapers.length / itemsPerPage);
  const paginatedPapers = filteredPapers.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  );

  const phases = stats ? Object.keys(stats.phases) : [];
  const topics = stats ? Object.keys(stats.topics) : [];

  // Filter out suspicious author names
  const formatAuthors = (authors?: string) => {
    if (!authors) return 'Unknown';
    const suspiciousWords = ['how', 'about', 'the', 'lessons', 'mapping', 'quality',
      'regional', 'drivers', 'managing', 'deindustrialization', 'entrepreneurship',
      'just', 'transition', 'unknown', 'covid', 'germany'];
    const authorLower = authors.toLowerCase().trim();
    if (suspiciousWords.includes(authorLower) ||
        authorLower.length < 3 ||
        /^\d/.test(authors) ||
        authorLower.startsWith('the ')) {
      return 'Unknown';
    }
    return authors;
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
              <Database className="w-5 h-5 text-primary" />
            </div>
            <div>
              <h1 className="text-2xl font-semibold text-white">Dataset</h1>
              {/* Show which KB is being viewed */}
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                {isDefaultSelected ? (
                  <Database className="w-3 h-3" />
                ) : (
                  <Folder className="w-3 h-3" />
                )}
                <span>{selectedKB?.name} · {papers.length} papers</span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Phase Filter */}
            {phases.length > 0 && (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" className="border-border bg-secondary/50 hover:bg-secondary gap-2">
                    <Filter className="w-4 h-4" />
                    {phaseFilter || 'Phase'}
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
            )}

            {/* Topic Filter */}
            {topics.length > 0 && (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" className="border-border bg-secondary/50 hover:bg-secondary gap-2">
                    <Filter className="w-4 h-4" />
                    {topicFilter || 'Topic'}
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
            )}

            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                placeholder="Search papers..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10 w-[200px] bg-secondary/50 border-border focus:border-primary"
              />
            </div>
          </div>
        </motion.div>

        {/* Loading State */}
        {loading && (
          <div className="flex flex-col items-center justify-center py-32">
            <Loader2 className="w-8 h-8 animate-spin text-primary mb-4" />
            <p className="text-muted-foreground">Loading papers...</p>
          </div>
        )}

        {/* Error State */}
        {error && (
          <div className="flex flex-col items-center justify-center py-32">
            <p className="text-destructive mb-2">Failed to load papers</p>
            <p className="text-muted-foreground text-sm">{error}</p>
          </div>
        )}

        {/* Papers Table */}
        {!loading && !error && (
          <motion.div variants={itemVariants}>
            <div className="rounded-lg border border-border overflow-hidden">
              <Table>
                <TableHeader>
                  <TableRow className="bg-secondary/30 hover:bg-secondary/30 border-border">
                    <TableHead className="text-muted-foreground font-medium">Paper</TableHead>
                    <TableHead className="text-muted-foreground font-medium">Authors</TableHead>
                    <TableHead className="text-muted-foreground font-medium">Year</TableHead>
                    <TableHead className="text-muted-foreground font-medium">Phase</TableHead>
                    <TableHead className="text-muted-foreground font-medium">Topic</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {paginatedPapers.length === 0 ? (
                    <TableRow className="border-border">
                      <TableCell colSpan={5} className="text-center py-12 text-muted-foreground">
                        {papers.length === 0 ? 'No papers in this knowledge base' : 'No papers match your filters'}
                      </TableCell>
                    </TableRow>
                  ) : (
                    paginatedPapers.map((paper) => (
                      <TableRow
                        key={paper.doc_id}
                        className="border-border hover:bg-secondary/20 transition-colors"
                      >
                        <TableCell>
                          <div className="flex items-center gap-3">
                            <FileText className="w-5 h-5 text-primary" />
                            <span className="text-foreground font-medium">{paper.title}</span>
                          </div>
                        </TableCell>
                        <TableCell className="text-muted-foreground max-w-[200px] truncate">
                          {formatAuthors(paper.authors)}
                        </TableCell>
                        <TableCell className="text-muted-foreground">
                          {paper.year || '-'}
                        </TableCell>
                        <TableCell>
                          {paper.phase && (
                            <Badge variant="secondary" className="bg-secondary/50">
                              {paper.phase}
                            </Badge>
                          )}
                        </TableCell>
                        <TableCell>
                          {paper.topic && (
                            <Badge variant="secondary" className="bg-secondary/50">
                              {paper.topic}
                            </Badge>
                          )}
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </div>
          </motion.div>
        )}

        {/* Pagination */}
        {!loading && !error && filteredPapers.length > 0 && (
          <motion.div
            variants={itemVariants}
            className="flex items-center justify-end gap-4 mt-8 pt-4 border-t border-border"
          >
            <span className="text-sm text-muted-foreground">
              Total {filteredPapers.length}
            </span>

            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="icon"
                className="border-border bg-secondary/50 hover:bg-secondary"
                disabled={currentPage === 1}
                onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
              >
                <ChevronLeft className="w-4 h-4" />
              </Button>
              <Button variant="outline" size="sm" className="border-border bg-secondary/50 hover:bg-secondary">
                {currentPage} / {totalPages || 1}
              </Button>
              <Button
                variant="outline"
                size="icon"
                className="border-border bg-secondary/50 hover:bg-secondary"
                disabled={currentPage >= totalPages}
                onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
              >
                <ChevronRight className="w-4 h-4" />
              </Button>
            </div>

            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" className="border-border bg-secondary/50 hover:bg-secondary gap-2">
                  {itemsPerPage} / Page <ChevronLeft className="w-4 h-4 rotate-90" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="bg-card border-border">
                {[10, 20, 50, 100].map(num => (
                  <DropdownMenuItem key={num} onClick={() => {
                    setItemsPerPage(num);
                    setCurrentPage(1);
                  }}>
                    {num} / Page
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>
          </motion.div>
        )}
      </div>
    </motion.div>
  );
}
