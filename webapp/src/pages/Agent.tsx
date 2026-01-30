import { motion } from 'framer-motion';
import { Bot, Filter, Search, Plus, ChevronLeft, ChevronRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
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

export default function Agent() {
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
              <Bot className="w-5 h-5 text-primary" />
            </div>
            <h1 className="text-2xl font-semibold text-white">Agents</h1>
          </div>
          
          <div className="flex items-center gap-3">
            <Button variant="outline" size="icon" className="border-border bg-secondary/50 hover:bg-secondary">
              <Filter className="w-4 h-4" />
            </Button>
            
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input 
                placeholder="Search..." 
                className="pl-10 w-[200px] bg-secondary/50 border-border focus:border-primary"
              />
            </div>
            
            <Button className="bg-white text-background hover:bg-white/90 gap-2">
              <Plus className="w-4 h-4" />
              Create agent
            </Button>
          </div>
        </motion.div>

        {/* Empty State */}
        <motion.div 
          variants={itemVariants}
          className="flex flex-col items-center justify-center py-32"
        >
          <div className="w-16 h-16 rounded-full bg-secondary/50 flex items-center justify-center mb-4">
            <Bot className="w-8 h-8 text-muted-foreground" />
          </div>
          <p className="text-muted-foreground text-sm">No agents found</p>
        </motion.div>

        {/* Pagination */}
        <motion.div 
          variants={itemVariants}
          className="flex items-center justify-end gap-4 mt-8 pt-4 border-t border-border"
        >
          <span className="text-sm text-muted-foreground">Total 0</span>
          
          <div className="flex items-center gap-2">
            <Button variant="outline" size="icon" className="border-border bg-secondary/50 hover:bg-secondary" disabled>
              <ChevronLeft className="w-4 h-4" />
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
