import { motion } from 'framer-motion';
import SettingsSidebar from '@/components/SettingsSidebar';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Search, UserPlus, User } from 'lucide-react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

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

const joinedTeams = [
  {
    name: 'Kanyuchi',
    date: '25/01/2026 08:13:55',
    email: 'shaunkudzi@gmail.com',
  },
];

export default function Team() {
  return (
    <div className="flex min-h-[calc(100vh-72px)]">
      <SettingsSidebar />
      
      <motion.main
        variants={containerVariants}
        initial="hidden"
        animate="visible"
        className="flex-1 p-8"
      >
        <div className="max-w-[1200px]">
          {/* Workspace Title */}
          <motion.h1 
            variants={itemVariants}
            className="text-2xl font-bold text-white mb-8"
          >
            Kanyuchi workspace
          </motion.h1>

          {/* Team Members Section */}
          <motion.div variants={itemVariants} className="mb-8">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
              <h2 className="text-lg font-semibold text-white">Team members</h2>
              
              <div className="flex items-center gap-3">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                  <Input 
                    placeholder="Search" 
                    className="pl-10 w-[200px] bg-secondary/50 border-border focus:border-primary"
                  />
                </div>
                <Button className="bg-white text-background hover:bg-white/90 gap-2">
                  <UserPlus className="w-4 h-4" />
                  Invite member
                </Button>
              </div>
            </div>

            {/* Team Members Table */}
            <div className="rounded-lg border border-border overflow-hidden">
              <Table>
                <TableHeader>
                  <TableRow className="bg-secondary/30 hover:bg-secondary/30 border-border">
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
                        Date
                        <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M7 15l5 5 5-5M7 9l5-5 5 5" />
                        </svg>
                      </div>
                    </TableHead>
                    <TableHead className="text-muted-foreground font-medium">Email</TableHead>
                    <TableHead className="text-muted-foreground font-medium">State</TableHead>
                    <TableHead className="text-muted-foreground font-medium text-right">Action</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  <TableRow className="border-border">
                    <TableCell colSpan={5} className="text-center py-12 text-muted-foreground">
                      No data
                    </TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            </div>
          </motion.div>

          {/* Joined Teams Section */}
          <motion.div variants={itemVariants}>
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
              <h2 className="text-lg font-semibold text-white">Joined teams</h2>
              
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <Input 
                  placeholder="Search" 
                  className="pl-10 w-[200px] bg-secondary/50 border-border focus:border-primary"
                />
              </div>
            </div>

            {/* Joined Teams Table */}
            <div className="rounded-lg border border-border overflow-hidden">
              <Table>
                <TableHeader>
                  <TableRow className="bg-secondary/30 hover:bg-secondary/30 border-border">
                    <TableHead className="text-muted-foreground font-medium">Name</TableHead>
                    <TableHead className="text-muted-foreground font-medium">
                      <div className="flex items-center gap-2 cursor-pointer hover:text-foreground">
                        Date
                        <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M7 15l5 5 5-5M7 9l5-5 5 5" />
                        </svg>
                      </div>
                    </TableHead>
                    <TableHead className="text-muted-foreground font-medium">Email</TableHead>
                    <TableHead className="text-muted-foreground font-medium text-right">Action</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {joinedTeams.map((team, index) => (
                    <TableRow 
                      key={index} 
                      className="border-border hover:bg-secondary/20 transition-colors"
                    >
                      <TableCell>
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-full bg-secondary flex items-center justify-center">
                            <User className="w-4 h-4 text-muted-foreground" />
                          </div>
                          <span className="text-foreground">{team.name}</span>
                        </div>
                      </TableCell>
                      <TableCell className="text-muted-foreground">{team.date}</TableCell>
                      <TableCell className="text-muted-foreground">{team.email}</TableCell>
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
        </div>
      </motion.main>
    </div>
  );
}
