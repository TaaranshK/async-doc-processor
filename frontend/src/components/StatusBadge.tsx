import { JobStatus } from '@/types/job';
import { cn } from '@/lib/utils';
import { motion } from 'framer-motion';

const statusConfig: Record<JobStatus, { label: string; className: string; dotClass: string }> = {
  queued: {
    label: 'Queued',
    className: 'bg-status-queued/10 text-status-queued border-status-queued/20',
    dotClass: 'bg-status-queued',
  },
  processing: {
    label: 'Processing',
    className: 'bg-status-processing/10 text-status-processing border-status-processing/20',
    dotClass: 'bg-status-processing animate-pulse-glow',
  },
  completed: {
    label: 'Completed',
    className: 'bg-status-completed/10 text-status-completed border-status-completed/20',
    dotClass: 'bg-status-completed',
  },
  failed: {
    label: 'Failed',
    className: 'bg-status-failed/10 text-status-failed border-status-failed/20',
    dotClass: 'bg-status-failed',
  },
  cancelled: {
    label: 'Cancelled',
    className: 'bg-status-cancelled/10 text-status-cancelled border-status-cancelled/20',
    dotClass: 'bg-status-cancelled',
  },
};

interface StatusBadgeProps {
  status: JobStatus;
  className?: string;
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const config = statusConfig[status];

  return (
    <motion.span
      initial={{ scale: 0.9, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium',
        config.className,
        className
      )}
    >
      <span className={cn('h-1.5 w-1.5 rounded-full', config.dotClass)} />
      {config.label}
    </motion.span>
  );
}
