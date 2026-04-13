import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';

interface ProgressBarProps {
  value: number;
  stage?: string | null;
  className?: string;
  showLabel?: boolean;
}

const stageLabels: Record<string, string> = {
  upload_received: 'Upload received',
  parsing_started: 'Parsing document...',
  parsing_completed: 'Parsing complete',
  extraction_started: 'Extracting fields...',
  extraction_completed: 'Extraction complete',
  storage_completed: 'Storing results...',
};

export function ProgressBar({ value, stage, className, showLabel = true }: ProgressBarProps) {
  const isComplete = value >= 100;

  return (
    <div className={cn('space-y-2', className)}>
      <div className="relative h-1.5 w-full overflow-hidden rounded-full bg-surface-3">
        <motion.div
          className={cn(
            'absolute inset-y-0 left-0 rounded-full',
            isComplete
              ? 'bg-status-completed'
              : 'bg-gradient-to-r from-primary to-accent'
          )}
          initial={{ width: 0 }}
          animate={{ width: `${Math.min(value, 100)}%` }}
          transition={{ duration: 0.6, ease: [0.4, 0, 0.2, 1] }}
        />
        {!isComplete && value > 0 && (
          <motion.div
            className="absolute inset-y-0 w-20 rounded-full bg-gradient-to-r from-transparent via-foreground/10 to-transparent"
            animate={{ left: ['-20%', '120%'] }}
            transition={{ duration: 1.5, repeat: Infinity, ease: 'linear' }}
          />
        )}
      </div>
      {showLabel && (
        <div className="flex items-center justify-between text-xs">
          <motion.span
            key={stage}
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-muted-foreground"
          >
            {stage ? stageLabels[stage] || stage : 'Waiting...'}
          </motion.span>
          <span className="font-mono text-foreground/70">{Math.round(value)}%</span>
        </div>
      )}
    </div>
  );
}
