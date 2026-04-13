import { useState, useMemo, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, Filter, ArrowUpDown, Download, ChevronLeft, ChevronRight } from 'lucide-react';
import { useJobs } from '@/hooks/useJobs';
import { useExport } from '@/hooks/useExport';
import { JobRow } from './JobRow';
import { JobsFilter, JobStatus } from '@/types/job';
import { retryJob, cancelJob } from '@/api/jobs';
import { cn } from '@/lib/utils';
import { useQueryClient } from '@tanstack/react-query';
import { toast } from '@/hooks/use-toast';

const STATUS_OPTIONS: { value: JobStatus; label: string }[] = [
  { value: 'queued', label: 'Queued' },
  { value: 'processing', label: 'Processing' },
  { value: 'completed', label: 'Completed' },
  { value: 'failed', label: 'Failed' },
  { value: 'cancelled', label: 'Cancelled' },
];

export function JobsTable() {
  const [filters, setFilters] = useState<JobsFilter>({ page: 1, page_size: 10 });
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<JobStatus[]>([]);
  const [showFilters, setShowFilters] = useState(false);
  const [selectedJobs, setSelectedJobs] = useState<Set<string>>(new Set());
  const queryClient = useQueryClient();
  const { exportJSON, exportCSV } = useExport();

  const activeFilters = useMemo(() => ({
    ...filters,
    search: search || undefined,
    status: statusFilter.length > 0 ? statusFilter : undefined,
  }), [filters, search, statusFilter]);

  const { data, isLoading } = useJobs(activeFilters);

  const handleRetry = useCallback(async (id: string) => {
    await retryJob(id);
    queryClient.invalidateQueries({ queryKey: ['jobs'] });
    toast({ title: 'Job retried', description: 'The job has been re-queued for processing.' });
  }, [queryClient]);

  const handleCancel = useCallback(async (id: string) => {
    await cancelJob(id);
    queryClient.invalidateQueries({ queryKey: ['jobs'] });
    toast({ title: 'Job cancelled', description: 'The job has been cancelled.' });
  }, [queryClient]);

  const toggleStatus = useCallback((status: JobStatus) => {
    setStatusFilter(prev =>
      prev.includes(status) ? prev.filter(s => s !== status) : [...prev, status]
    );
  }, []);

  const toggleSelect = useCallback((id: string) => {
    setSelectedJobs(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const toggleSort = useCallback(() => {
    setFilters(prev => ({
      ...prev,
      sort_order: prev.sort_order === 'desc' ? 'asc' : 'desc',
    }));
  }, []);

  const totalPages = data ? Math.ceil(data.total / (filters.page_size || 10)) : 1;

  return (
    <div className="space-y-4">
      {/* Toolbar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
        {/* Search */}
        <div className="relative flex-1 w-full sm:max-w-xs">
          <Search className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search files..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="w-full rounded-lg border border-border bg-surface-1 py-2 pl-9 pr-3 text-sm text-foreground placeholder:text-muted-foreground outline-none transition-colors focus:border-primary/50 focus:ring-1 focus:ring-primary/20"
          />
        </div>

        {/* Filter toggle */}
        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={() => setShowFilters(!showFilters)}
          className={cn(
            'flex items-center gap-1.5 rounded-lg border px-3 py-2 text-xs font-medium transition-colors',
            showFilters
              ? 'border-primary/30 bg-primary/5 text-primary'
              : 'border-border bg-surface-1 text-muted-foreground hover:text-foreground'
          )}
        >
          <Filter className="h-3.5 w-3.5" />
          Filter
          {statusFilter.length > 0 && (
            <span className="ml-1 rounded-full bg-primary/20 px-1.5 text-[10px] text-primary">
              {statusFilter.length}
            </span>
          )}
        </motion.button>

        {/* Sort */}
        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={toggleSort}
          className="flex items-center gap-1.5 rounded-lg border border-border bg-surface-1 px-3 py-2 text-xs font-medium text-muted-foreground transition-colors hover:text-foreground"
        >
          <ArrowUpDown className="h-3.5 w-3.5" />
          {filters.sort_order === 'asc' ? 'Oldest' : 'Newest'}
        </motion.button>

        {/* Bulk export */}
        {selectedJobs.size > 0 && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="flex items-center gap-2"
          >
            <button
              onClick={() => exportJSON(Array.from(selectedJobs))}
              className="flex items-center gap-1.5 rounded-lg bg-primary/10 px-3 py-2 text-xs font-medium text-primary transition-colors hover:bg-primary/20"
            >
              <Download className="h-3 w-3" />
              JSON
            </button>
            <button
              onClick={() => exportCSV(Array.from(selectedJobs))}
              className="flex items-center gap-1.5 rounded-lg bg-primary/10 px-3 py-2 text-xs font-medium text-primary transition-colors hover:bg-primary/20"
            >
              <Download className="h-3 w-3" />
              CSV
            </button>
            <span className="text-xs text-muted-foreground">
              {selectedJobs.size} selected
            </span>
          </motion.div>
        )}
      </div>

      {/* Status filter chips */}
      <AnimatePresence>
        {showFilters && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="flex flex-wrap gap-2 overflow-hidden"
          >
            {STATUS_OPTIONS.map(opt => (
              <button
                key={opt.value}
                onClick={() => toggleStatus(opt.value)}
                className={cn(
                  'rounded-full border px-3 py-1 text-xs font-medium transition-all',
                  statusFilter.includes(opt.value)
                    ? 'border-primary/30 bg-primary/10 text-primary'
                    : 'border-border bg-surface-1 text-muted-foreground hover:text-foreground'
                )}
              >
                {opt.label}
              </button>
            ))}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Table */}
      <div className="rounded-xl border border-border bg-card">
        {isLoading ? (
          <div className="space-y-1 p-2">
            {Array.from({ length: 5 }).map((_, i) => (
              <div
                key={i}
                className="flex items-center gap-4 rounded-lg px-4 py-3"
              >
                <div className="h-3.5 w-3.5 rounded bg-surface-3 animate-shimmer" style={{ backgroundSize: '200% 100%', backgroundImage: 'linear-gradient(90deg, transparent, hsl(var(--surface-3)) 50%, transparent)' }} />
                <div className="flex-1 space-y-1.5">
                  <div className="h-3.5 w-48 rounded bg-surface-3" />
                  <div className="h-2.5 w-20 rounded bg-surface-3" />
                </div>
                <div className="h-5 w-20 rounded-full bg-surface-3" />
              </div>
            ))}
          </div>
        ) : data?.jobs.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <p className="text-sm text-muted-foreground">No jobs found</p>
            <p className="text-xs text-muted-foreground/60 mt-1">Upload documents to get started</p>
          </div>
        ) : (
          <div className="divide-y divide-border/50 p-1">
            <AnimatePresence mode="popLayout">
              {data?.jobs.map(job => (
                <JobRow
                  key={job.id}
                  job={job}
                  onRetry={handleRetry}
                  onCancel={handleCancel}
                  selected={selectedJobs.has(job.id)}
                  onSelect={toggleSelect}
                />
              ))}
            </AnimatePresence>
          </div>
        )}
      </div>

      {/* Pagination */}
      {data && totalPages > 1 && (
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>
            {data.total} total job{data.total !== 1 ? 's' : ''}
          </span>
          <div className="flex items-center gap-2">
            <button
              disabled={(filters.page || 1) <= 1}
              onClick={() => setFilters(f => ({ ...f, page: (f.page || 1) - 1 }))}
              className="rounded-md p-1 transition-colors hover:bg-surface-2 disabled:opacity-30"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <span>
              Page {filters.page || 1} of {totalPages}
            </span>
            <button
              disabled={(filters.page || 1) >= totalPages}
              onClick={() => setFilters(f => ({ ...f, page: (f.page || 1) + 1 }))}
              className="rounded-md p-1 transition-colors hover:bg-surface-2 disabled:opacity-30"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
