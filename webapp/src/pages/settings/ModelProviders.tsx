import { useState } from 'react';
import { motion } from 'framer-motion';
import SettingsSidebar from '@/components/SettingsSidebar';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Search, Share2, Key, ChevronDown, Trash2 } from 'lucide-react';

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

const modelTypes = ['All', 'IMAGE2TEXT', 'LLM', 'MODERATION', 'SPEECH2TEXT', 'TEXT EMBEDDING', 'TEXT RE-RANK', 'TTS'];

const availableProviders = [
  {
    name: 'OpenAI',
    logo: (
      <svg className="w-8 h-8" viewBox="0 0 24 24" fill="currentColor">
        <path d="M22.282 9.821a5.985 5.985 0 0 0-.516-4.91 6.046 6.046 0 0 0-6.51-2.9A6.065 6.065 0 0 0 4.981 4.18a5.985 5.985 0 0 0-3.998 2.9 6.046 6.046 0 0 0 .743 7.097 5.98 5.98 0 0 0 .51 4.911 6.051 6.051 0 0 0 6.515 2.9A5.985 5.985 0 0 0 13.26 24a6.056 6.056 0 0 0 5.772-4.206 5.99 5.99 0 0 0 3.997-2.9 6.056 6.056 0 0 0-.747-7.073zM13.26 22.43a4.476 4.476 0 0 1-2.876-1.04l.141-.081 4.779-2.758a.795.795 0 0 0 .392-.681v-6.737l2.02 1.168a.071.071 0 0 1 .038.052v5.583a4.504 4.504 0 0 1-4.494 4.494zM3.6 18.304a4.47 4.47 0 0 1-.535-3.014l.142.085 4.783 2.759a.771.771 0 0 0 .78 0l5.843-3.369v2.332a.08.08 0 0 1-.033.062L9.74 19.95a4.5 4.5 0 0 1-6.14-1.646zM2.34 7.896a4.485 4.485 0 0 1 2.366-1.973V11.6a.766.766 0 0 0 .388.676l5.815 3.355-2.02 1.168a.076.076 0 0 1-.071 0l-4.83-2.786A4.504 4.504 0 0 1 2.34 7.896zm16.597 3.855l-5.833-3.387L15.119 7.2a.076.076 0 0 1 .071 0l4.83 2.791a4.494 4.494 0 0 1-.676 8.105v-5.678a.79.79 0 0 0-.407-.667zm2.01-3.023l-.141-.085-4.774-2.782a.776.776 0 0 0-.785 0L9.409 9.23V6.897a.066.066 0 0 1 .028-.061l4.83-2.787a4.5 4.5 0 0 1 6.68 4.66zm-12.64 4.135l-2.02-1.164a.08.08 0 0 1-.038-.057V6.075a4.5 4.5 0 0 1 7.375-3.453l-.142.08L8.704 5.46a.795.795 0 0 0-.393.681zm1.097-2.365l2.602-1.5 2.607 1.5v2.999l-2.597 1.5-2.607-1.5z"/>
      </svg>
    ),
    types: ['LLM', 'TEXT EMBEDDING', 'TEXT RE-RANK', 'TTS', 'SPEECH2TEXT', 'MODERATION'],
  },
  {
    name: 'Anthropic',
    logo: (
      <svg className="w-8 h-8" viewBox="0 0 24 24" fill="currentColor">
        <path d="M17.304 3.541h-3.672l6.696 16.918h3.672zm-10.608 0L0 20.459h3.744l1.368-3.6h6.624l1.368 3.6h3.744L8.928 3.541zm-.264 10.656 1.944-5.112 1.944 5.112z"/>
      </svg>
    ),
    types: ['LLM'],
  },
  {
    name: 'Gemini',
    logo: (
      <svg className="w-8 h-8" viewBox="0 0 24 24">
        <defs>
          <linearGradient id="gemini-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#4285F4"/>
            <stop offset="50%" stopColor="#9B72CB"/>
            <stop offset="100%" stopColor="#D96570"/>
          </linearGradient>
        </defs>
        <path fill="url(#gemini-gradient)" d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"/>
      </svg>
    ),
    types: ['LLM', 'TEXT EMBEDDING', 'IMAGE2TEXT'],
  },
  {
    name: 'Moonshot',
    logo: (
      <svg className="w-8 h-8" viewBox="0 0 24 24" fill="currentColor">
        <circle cx="12" cy="12" r="10" fill="#1a1a1a" stroke="currentColor" strokeWidth="2"/>
        <path d="M12 6v6l4 2" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round"/>
      </svg>
    ),
    types: ['LLM', 'TEXT EMBEDDING', 'IMAGE2TEXT'],
  },
];

const addedModels = [
  {
    name: 'BAAI',
    logo: (
      <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center text-white text-xs font-bold">
        B
      </div>
    ),
  },
  {
    name: 'DeepSeek',
    logo: (
      <svg className="w-8 h-8" viewBox="0 0 24 24" fill="#4D6BFF">
        <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
      </svg>
    ),
  },
];

export default function ModelProviders() {
  const [selectedType, setSelectedType] = useState('All');

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
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Left Column - Set Default Models */}
            <motion.div variants={itemVariants}>
              <h1 className="text-2xl font-bold text-white mb-2">Set default models</h1>
              <p className="text-muted-foreground mb-6">Please complete these settings before beginning</p>

              <div className="space-y-4">
                {[
                  { label: 'LLM', required: true },
                  { label: 'Embedding', required: false },
                  { label: 'VLM', required: false },
                  { label: 'ASR', required: false },
                  { label: 'Rerank', required: false },
                  { label: 'TTS', required: false },
                ].map((field) => (
                  <div key={field.label} className="flex items-center gap-4">
                    <label className="w-24 text-sm text-foreground flex items-center gap-1">
                      {field.required && <span className="text-red-500">*</span>}
                      {field.label}
                      <svg className="w-4 h-4 text-muted-foreground" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <circle cx="12" cy="12" r="10"/>
                        <path d="M12 16v-4M12 8h.01"/>
                      </svg>
                    </label>
                    <Select>
                      <SelectTrigger className="flex-1 bg-secondary/50 border-border">
                        <SelectValue placeholder="Select model" />
                      </SelectTrigger>
                      <SelectContent className="bg-card border-border">
                        <SelectItem value="gpt-4">GPT-4</SelectItem>
                        <SelectItem value="gpt-3.5">GPT-3.5</SelectItem>
                        <SelectItem value="claude">Claude</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                ))}
              </div>
            </motion.div>

            {/* Right Column - Available Models */}
            <motion.div variants={itemVariants}>
              <h2 className="text-xl font-bold text-white mb-4">Available models</h2>
              
              {/* Search */}
              <div className="relative mb-4">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <Input 
                  placeholder="Search" 
                  className="pl-10 bg-secondary/50 border-border focus:border-primary"
                />
              </div>

              {/* Type Filters */}
              <div className="flex flex-wrap gap-2 mb-4">
                {modelTypes.map((type) => (
                  <button
                    key={type}
                    onClick={() => setSelectedType(type)}
                    className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                      selectedType === type
                        ? 'bg-white text-background'
                        : 'bg-secondary/50 text-muted-foreground hover:text-foreground'
                    }`}
                  >
                    {type}
                  </button>
                ))}
              </div>

              {/* Provider List */}
              <div className="space-y-3">
                {availableProviders.map((provider) => (
                  <motion.div
                    key={provider.name}
                    whileHover={{ scale: 1.01 }}
                    className="p-4 bg-card border border-border rounded-lg hover:border-primary/50 transition-colors"
                  >
                    <div className="flex items-center gap-3 mb-2">
                      {provider.logo}
                      <span className="font-semibold text-white">{provider.name}</span>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {provider.types.map((type) => (
                        <Badge 
                          key={type} 
                          variant="secondary"
                          className="bg-secondary/50 text-muted-foreground text-xs"
                        >
                          {type}
                        </Badge>
                      ))}
                    </div>
                  </motion.div>
                ))}
              </div>
            </motion.div>
          </div>

          {/* Added Models Section */}
          <motion.div variants={itemVariants} className="mt-8">
            <h2 className="text-xl font-bold text-white mb-4">Added models</h2>
            
            <div className="space-y-3">
              {addedModels.map((model) => (
                <motion.div
                  key={model.name}
                  whileHover={{ scale: 1.01 }}
                  className="flex items-center justify-between p-4 bg-card border border-border rounded-lg"
                >
                  <div className="flex items-center gap-3">
                    {model.logo}
                    <span className="font-semibold text-white">{model.name}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button variant="outline" size="sm" className="border-border bg-secondary/50 hover:bg-secondary gap-1">
                      <Share2 className="w-4 h-4" />
                      Share
                    </Button>
                    <Button variant="outline" size="sm" className="border-border bg-secondary/50 hover:bg-secondary gap-1">
                      <Key className="w-4 h-4" />
                      API-Key
                    </Button>
                    <Button variant="outline" size="sm" className="border-border bg-secondary/50 hover:bg-secondary gap-1">
                      View models
                      <ChevronDown className="w-4 h-4" />
                    </Button>
                    <Button variant="outline" size="icon" className="border-border bg-secondary/50 hover:bg-secondary hover:text-destructive">
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </motion.div>
              ))}
            </div>
          </motion.div>
        </div>
      </motion.main>
    </div>
  );
}
