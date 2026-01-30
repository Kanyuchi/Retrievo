import { motion } from 'framer-motion';
import { FolderOpen, Search, Upload, ChevronLeft, ChevronRight, Folder } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Checkbox } from '@/components/ui/checkbox';
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

const files = [
  {
    id: 1,
    name: '.knowledgebase',
    uploadDate: '04/06/2025 17:38:28',
    size: '0 B',
    dataset: '',
    isFolder: true,
  },
];

export default function Files() {
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
              <FolderOpen className="w-5 h-5 text-primary" />
            </div>
            <h1 className="text-2xl font-semibold text-white">Files</h1>
          </div>
          
          <div className="flex items-center gap-3">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input 
                placeholder="Search..." 
                className="pl-10 w-[200px] bg-secondary/50 border-border focus:border-primary"
              />
            </div>
            
            <Button className="bg-white text-background hover:bg-white/90 gap-2">
              <Upload className="w-4 h-4" />
              Add file
            </Button>
          </div>
        </motion.div>

        {/* Files Table */}
        <motion.div variants={itemVariants}>
          <div className="rounded-lg border border-border overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow className="bg-secondary/30 hover:bg-secondary/30 border-border">
                  <TableHead className="w-12">
                    <Checkbox className="border-border" />
                  </TableHead>
                  <TableHead className="text-muted-foreground font-medium">
                    <div className="flex items-center gap-2 cursor-pointer hover:text-foreground">
                      Name
                      <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M7 15l5 5 5-5M7 9l5-5 5 5" />
                      </svg>
                    </div>
                  </TableHead>
                  <TableHead className="text-muted-foreground font-medium">
                    <div className="flex items-center gap-2 cursor-pointer hover:text-foreground">
                      Upload Date
                      <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M7 15l5 5 5-5M7 9l5-5 5 5" />
                      </svg>
                    </div>
                  </TableHead>
                  <TableHead className="text-muted-foreground font-medium">
                    <div className="flex items-center gap-2 cursor-pointer hover:text-foreground">
                      Size
                      <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M7 15l5 5 5-5M7 9l5-5 5 5" />
                      </svg>
                    </div>
                  </TableHead>
                  <TableHead className="text-muted-foreground font-medium">Dataset</TableHead>
                  <TableHead className="text-muted-foreground font-medium text-right">Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {files.map((file) => (
                  <TableRow 
                    key={file.id} 
                    className="border-border hover:bg-secondary/20 transition-colors"
                  >
                    <TableCell>
                      <Checkbox className="border-border" />
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-3">
                        <Folder className="w-5 h-5 text-yellow-500" />
                        <span className="text-foreground">{file.name}</span>
                      </div>
                    </TableCell>
                    <TableCell className="text-muted-foreground">{file.uploadDate}</TableCell>
                    <TableCell className="text-muted-foreground">{file.size}</TableCell>
                    <TableCell className="text-muted-foreground">{file.dataset}</TableCell>
                    <TableCell className="text-right">
                      <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-foreground">
                        Actions
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </motion.div>

        {/* Pagination */}
        <motion.div 
          variants={itemVariants}
          className="flex items-center justify-end gap-4 mt-8 pt-4 border-t border-border"
        >
          <span className="text-sm text-muted-foreground">Total 1</span>
          
          <div className="flex items-center gap-2">
            <Button variant="outline" size="icon" className="border-border bg-secondary/50 hover:bg-secondary" disabled>
              <ChevronLeft className="w-4 h-4" />
            </Button>
            <Button variant="outline" size="sm" className="border-border bg-secondary/50 hover:bg-secondary">
              1
            </Button>
            <Button variant="outline" size="icon" className="border-border bg-secondary/50 hover:bg-secondary" disabled>
              <ChevronRight className="w-4 h-4" />
            </Button>
          </div>
          
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" className="border-border bg-secondary/50 hover:bg-secondary gap-2">
                50 / Page <ChevronLeft className="w-4 h-4 rotate-90" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="bg-card border-border">
              <DropdownMenuItem>10 / Page</DropdownMenuItem>
              <DropdownMenuItem>20 / Page</DropdownMenuItem>
              <DropdownMenuItem>50 / Page</DropdownMenuItem>
              <DropdownMenuItem>100 / Page</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </motion.div>
      </div>
    </motion.div>
  );
}
