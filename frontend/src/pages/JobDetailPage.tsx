import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowLeft, Download, FileText, Clock } from 'lucide-react';
import { useJob } from '@/hooks/useJobs';
import { fetchResult } from '@/api/documents';
import { useExport } from '@/hooks/useExport';
import { StatusBadge } from '@/components/StatusBadge';
import { ProgressBar } from '@/components/ProgressBar';
import { DetailForm } from '@/components/DetailForm';
import { JobResult } from '@/types/result';
import { cn } from '@/lib/utils';

export default function JobDetailPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();
  const { data: job, isLoading: jobLoading } = useJob(jobId || '');
  const [result, setResult] = useState<JobResult | null>(null);
  const [resultLoading, setResultLoading] = useState(true);
  const { exportJSON, exportCSV } = useExport();

  useEffect(() => {
    if (!jobId) return;
    setResultLoading(true);
    fetchResult(jobId)
      .then(setResult)
      .catch(() => setResult(null))
      .finally(() => setResultLoading(false));
  }, [jobId]);

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString('en-US', {
      month: 'short', day: 'numeric', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    });
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  if (jobLoading || resultLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="space-y-4 w-full max-w-2xl px-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-12 rounded-lg bg-surface-2 animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  if (!job) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-muted-foreground">Job not found</p>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.4 }}
      className="min-h-screen px-4 py-8 sm:px-6 lg:px-8"
    >
      <div className="mx-auto max-w-3xl space-y-8">
        {/* Back + title */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <button
            onClick={() => navigate('/dashboard')}
            className="mb-4 flex items-center gap-1.5 text-xs text-muted-foreground transition-colors hover:text-foreground"
          >
            <ArrowLeft className="h-3 w-3" />
            Back to dashboard
          </button>

          <div className="flex items-start justify-between gap-4">
            <div className="flex items-center gap-3 min-w-0">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-surface-2 border border-border">
                <FileText className="h-5 w-5 text-muted-foreground" />
              </div>
              <div className="min-w-0">
                <h1 className="text-lg font-semibold tracking-tight text-foreground truncate">
                  {job.filename}
                </h1>
                <div className="flex items-center gap-3 mt-0.5">
                  <StatusBadge status={job.status} />
                  <span className="text-xs text-muted-foreground">{formatSize(job.file_size)}</span>
                </div>
              </div>
            </div>

            {/* Export buttons */}
            {result?.is_finalized && (
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="flex items-center gap-2 shrink-0"
              >
                <button
                  onClick={() => exportJSON([job.id])}
                  className="flex items-center gap-1.5 rounded-lg border border-border bg-surface-1 px-3 py-2 text-xs font-medium text-foreground transition-colors hover:bg-surface-2"
                >
                  <Download className="h-3 w-3" />
                  JSON
                </button>
                <button
                  onClick={() => exportCSV([job.id])}
                  className="flex items-center gap-1.5 rounded-lg border border-border bg-surface-1 px-3 py-2 text-xs font-medium text-foreground transition-colors hover:bg-surface-2"
                >
                  <Download className="h-3 w-3" />
                  CSV
                </button>
              </motion.div>
            )}
          </div>
        </motion.div>

        {/* Metadata */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="grid grid-cols-2 sm:grid-cols-4 gap-4"
        >
          {[
            { label: 'Created', value: formatDate(job.created_at), icon: Clock },
            { label: 'Job ID', value: job.id.slice(0, 8) + '...', icon: FileText },
            { label: 'Type', value: job.file_type.split('/').pop() || '-', icon: FileText },
            { label: 'Retries', value: `${job.retry_count}/3`, icon: FileText },
          ].map(({ label, value }) => (
            <div key={label} className="rounded-lg border border-border bg-surface-1 p-3">
              <p className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">{label}</p>
              <p className="mt-1 text-sm font-medium text-foreground truncate font-mono">{value}</p>
            </div>
          ))}
        </motion.div>

        {/* Progress */}
        {(job.status === 'processing' || job.status === 'queued') && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15 }}
            className="rounded-xl border border-border bg-card p-6"
          >
            <h2 className="mb-4 text-sm font-medium text-foreground">Processing Progress</h2>
            <ProgressBar value={job.progress_pct} stage={job.current_stage} />
          </motion.div>
        )}

        {/* Detail form */}
        {result && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="rounded-xl border border-border bg-card p-6"
          >
            <h2 className="mb-6 text-sm font-medium text-foreground">Extracted Data</h2>
            <DetailForm result={result} onUpdate={setResult} />
          </motion.div>
        )}

        {/* No result */}
        {!result && job.status === 'completed' && (
          <div className="rounded-xl border border-border bg-card p-8 text-center">
            <p className="text-sm text-muted-foreground">No extraction result available.</p>
          </div>
        )}
      </div>
    </motion.div>
  );
}
