import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, Eye, RotateCcw, XCircle, FileText } from 'lucide-react';
import { Job } from '@/types/job';
import { StatusBadge } from './StatusBadge';
import { ProgressBar } from './ProgressBar';
import { useSSE } from '@/hooks/useSSE';
import { cn } from '@/lib/utils';
import { useNavigate } from 'react-router-dom';

interface JobRowProps {
  job: Job;
  onRetry: (id: string) => void;
  onCancel: (id: string) => void;
  selected?: boolean;
  onSelect?: (id: string) => void;
}

export function JobRow({ job, onRetry, onCancel, selected, onSelect }: JobRowProps) {
  const [expanded, setExpanded] = useState(false);
  const navigate = useNavigate();
  const { progress } = useSSE(expanded && job.status === 'processing' ? job.id : null);

  const formatDate = (dateStr: string) => {
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const currentProgress = progress?.progress_pct ?? job.progress_pct;
  const currentStage = progress?.stage ?? job.current_stage;

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="group"
    >
      <div
        className={cn(
          'flex items-center gap-4 rounded-lg border border-transparent px-4 py-3 transition-all duration-200',
          'hover:bg-surface-2 hover:border-border',
          expanded && 'bg-surface-2 border-border'
        )}
      >
        {/* Checkbox */}
        {onSelect && (
          <input
            type="checkbox"
            checked={selected}
            onChange={() => onSelect(job.id)}
            className="h-3.5 w-3.5 rounded border-border bg-surface-3 accent-primary"
          />
        )}

        {/* File icon */}
        <FileText className="h-4 w-4 shrink-0 text-muted-foreground" />

        {/* Filename */}
        <div className="flex-1 min-w-0">
          <p className="truncate text-sm font-medium text-foreground">{job.filename}</p>
          <p className="text-xs text-muted-foreground">{formatSize(job.file_size)}</p>
        </div>

        {/* Status */}
        <StatusBadge status={job.status} />

        {/* Progress mini */}
        {(job.status === 'processing' || job.status === 'queued') && (
          <div className="w-24 hidden sm:block">
            <ProgressBar value={currentProgress} showLabel={false} />
          </div>
        )}

        {/* Time */}
        <span className="hidden md:block text-xs text-muted-foreground whitespace-nowrap">
          {formatDate(job.created_at)}
        </span>

        {/* Actions */}
        <div className="flex items-center gap-1">
          {job.status === 'completed' && (
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => navigate(`/jobs/${job.id}`)}
              className="rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-surface-3 hover:text-foreground"
              title="View details"
            >
              <Eye className="h-3.5 w-3.5" />
            </motion.button>
          )}
          {job.status === 'failed' && (
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => onRetry(job.id)}
              className="rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-surface-3 hover:text-status-processing"
              title="Retry"
            >
              <RotateCcw className="h-3.5 w-3.5" />
            </motion.button>
          )}
          {(job.status === 'queued' || job.status === 'processing') && (
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => onCancel(job.id)}
              className="rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-surface-3 hover:text-destructive"
              title="Cancel"
            >
              <XCircle className="h-3.5 w-3.5" />
            </motion.button>
          )}
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => setExpanded(!expanded)}
            className="rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-surface-3 hover:text-foreground"
          >
            <motion.div
              animate={{ rotate: expanded ? 180 : 0 }}
              transition={{ duration: 0.2 }}
            >
              <ChevronDown className="h-3.5 w-3.5" />
            </motion.div>
          </motion.button>
        </div>
      </div>

      {/* Expanded progress */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: [0.4, 0, 0.2, 1] }}
            className="overflow-hidden"
          >
            <div className="px-4 pb-4 pt-1 ml-8">
              <div className="rounded-lg border border-border bg-surface-1 p-4 space-y-3">
                <ProgressBar value={currentProgress} stage={currentStage} />
                
                {job.error_message && (
                  <motion.p
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="text-xs text-destructive bg-destructive/5 rounded-md px-3 py-2 border border-destructive/10"
                  >
                    {job.error_message}
                  </motion.p>
                )}

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                  <div>
                    <span className="text-muted-foreground">Job ID</span>
                    <p className="font-mono text-foreground/80 truncate">{job.id.slice(0, 8)}...</p>
                  </div>
                  <div>
                    <span className="text-muted-foreground">File type</span>
                    <p className="text-foreground/80">{job.file_type.split('/').pop()}</p>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Retries</span>
                    <p className="text-foreground/80">{job.retry_count}/3</p>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Updated</span>
                    <p className="text-foreground/80">{formatDate(job.updated_at)}</p>
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
