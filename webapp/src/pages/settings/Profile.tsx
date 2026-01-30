import { motion } from 'framer-motion';
import SettingsSidebar from '@/components/SettingsSidebar';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Pencil, X, User } from 'lucide-react';
import { toast } from 'sonner';

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

export default function Profile() {
  return (
    <div className="flex min-h-[calc(100vh-72px)]">
      <SettingsSidebar />
      
      <motion.main
        variants={containerVariants}
        initial="hidden"
        animate="visible"
        className="flex-1 p-8"
      >
        <div className="max-w-[600px]">
          <motion.div variants={itemVariants} className="mb-8">
            <h1 className="text-2xl font-bold text-white mb-2">Profile</h1>
            <p className="text-muted-foreground">Update your photo and personal details here.</p>
          </motion.div>

          <motion.div variants={itemVariants} className="space-y-6">
            {/* Name Field */}
            <div className="flex items-start gap-8">
              <label className="w-24 pt-2 text-sm text-foreground">Name</label>
              <div className="flex-1 flex items-center gap-3">
                <Input
                  value="Kanyuchi"
                  readOnly
                  className="bg-secondary/50 border-border focus:border-primary"
                />
                <Button
                  variant="outline"
                  size="icon"
                  className="border-border bg-secondary/50 hover:bg-secondary flex-shrink-0"
                  onClick={() => toast.info('Profile editing coming soon')}
                >
                  <Pencil className="w-4 h-4" />
                </Button>
              </div>
            </div>

            {/* Avatar Field */}
            <div className="flex items-start gap-8">
              <label className="w-24 pt-2 text-sm text-foreground">Avatar</label>
              <div className="flex-1 flex items-center gap-4">
                <div className="relative">
                  <div className="w-16 h-16 rounded-lg bg-secondary flex items-center justify-center overflow-hidden border border-border">
                    <User className="w-8 h-8 text-muted-foreground" />
                  </div>
                  <button className="absolute -top-2 -right-2 w-6 h-6 rounded-full bg-secondary border border-border flex items-center justify-center hover:bg-secondary/80 transition-colors">
                    <X className="w-3 h-3 text-muted-foreground" />
                  </button>
                </div>
                <p className="text-sm text-muted-foreground">This will be displayed on your profile.</p>
              </div>
            </div>

            {/* Time Zone Field */}
            <div className="flex items-start gap-8">
              <label className="w-24 pt-2 text-sm text-foreground">Time zone</label>
              <div className="flex-1 flex items-center gap-3">
                <Input
                  value="UTC+8 Asia/Shanghai"
                  readOnly
                  className="bg-secondary/50 border-border focus:border-primary"
                />
                <Button
                  variant="outline"
                  size="icon"
                  className="border-border bg-secondary/50 hover:bg-secondary flex-shrink-0"
                  onClick={() => toast.info('Profile editing coming soon')}
                >
                  <Pencil className="w-4 h-4" />
                </Button>
              </div>
            </div>

            {/* Email Field */}
            <div className="flex items-start gap-8">
              <label className="w-24 pt-2 text-sm text-foreground">Email</label>
              <div className="flex-1">
                <p className="text-foreground mb-1">shaunkudzi@gmail.com</p>
                <p className="text-xs text-muted-foreground">Once registered, E-mail cannot be changed.</p>
              </div>
            </div>

            {/* Password Field */}
            <div className="flex items-start gap-8">
              <label className="w-24 pt-2 text-sm text-foreground">Password</label>
              <div className="flex-1 flex items-center gap-3">
                <Input
                  type="password"
                  value="********"
                  readOnly
                  className="bg-secondary/50 border-border focus:border-primary"
                />
                <Button
                  variant="outline"
                  size="icon"
                  className="border-border bg-secondary/50 hover:bg-secondary flex-shrink-0"
                  onClick={() => toast.info('Profile editing coming soon')}
                >
                  <Pencil className="w-4 h-4" />
                </Button>
              </div>
            </div>
          </motion.div>
        </div>
      </motion.main>
    </div>
  );
}
