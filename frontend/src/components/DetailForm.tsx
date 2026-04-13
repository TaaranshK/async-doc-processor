import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Save, Lock, Check, Loader2 } from 'lucide-react';
import { JobResult, ExtractedFields } from '@/types/result';
import { updateResult, finalizeResult } from '@/api/documents';
import { cn } from '@/lib/utils';
import { toast } from '@/hooks/use-toast';

interface DetailFormProps {
  result: JobResult;
  onUpdate: (updated: JobResult) => void;
}

export function DetailForm({ result, onUpdate }: DetailFormProps) {
  const currentData = result.reviewed_output || result.raw_output;
  const [fields, setFields] = useState<ExtractedFields>(currentData);
  const [saving, setSaving] = useState(false);
  const [finalizing, setFinalizing] = useState(false);
  const [saved, setSaved] = useState(false);
  const [dirty, setDirty] = useState(false);

  useEffect(() => {
    setFields(result.reviewed_output || result.raw_output);
    setDirty(false);
    setSaved(false);
  }, [result]);

  const handleChange = useCallback((key: keyof ExtractedFields, value: string | string[]) => {
    setFields(prev => ({ ...prev, [key]: value }));
    setDirty(true);
    setSaved(false);
  }, []);

  const handleSave = useCallback(async () => {
    setSaving(true);
    try {
      const updated = await updateResult(result.job_id, fields);
      onUpdate(updated);
      setSaved(true);
      setDirty(false);
      toast({ title: 'Saved', description: 'Changes saved successfully.' });
    } catch {
      toast({ title: 'Error', description: 'Failed to save changes.', variant: 'destructive' });
    } finally {
      setSaving(false);
    }
  }, [fields, result.job_id, onUpdate]);

  const handleFinalize = useCallback(async () => {
    setFinalizing(true);
    try {
      const updated = await finalizeResult(result.job_id);
      onUpdate(updated);
      toast({ title: 'Finalized', description: 'Document has been locked and finalized.' });
    } catch {
      toast({ title: 'Error', description: 'Failed to finalize.', variant: 'destructive' });
    } finally {
      setFinalizing(false);
    }
  }, [result.job_id, onUpdate]);

  const isLocked = result.is_finalized;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-6"
    >
      {/* Lock banner */}
      <AnimatePresence>
        {isLocked && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            className="flex items-center gap-2 rounded-lg border border-status-completed/20 bg-status-completed/5 px-4 py-3 text-sm text-status-completed"
          >
            <Lock className="h-4 w-4" />
            <span>This document has been finalized and is read-only.</span>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Fields */}
      <div className="space-y-4">
        {/* Title */}
        <div className="space-y-1.5">
          <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Title</label>
          <input
            type="text"
            value={fields.title}
            onChange={e => handleChange('title', e.target.value)}
            disabled={isLocked}
            className={cn(
              'w-full rounded-lg border bg-surface-1 px-4 py-2.5 text-sm text-foreground outline-none transition-all',
              'border-border focus:border-primary/50 focus:ring-1 focus:ring-primary/20',
              isLocked && 'opacity-60 cursor-not-allowed'
            )}
          />
        </div>

        {/* Category */}
        <div className="space-y-1.5">
          <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Category</label>
          <input
            type="text"
            value={fields.category}
            onChange={e => handleChange('category', e.target.value)}
            disabled={isLocked}
            className={cn(
              'w-full rounded-lg border bg-surface-1 px-4 py-2.5 text-sm text-foreground outline-none transition-all',
              'border-border focus:border-primary/50 focus:ring-1 focus:ring-primary/20',
              isLocked && 'opacity-60 cursor-not-allowed'
            )}
          />
        </div>

        {/* Summary */}
        <div className="space-y-1.5">
          <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Summary</label>
          <textarea
            value={fields.summary}
            onChange={e => handleChange('summary', e.target.value)}
            disabled={isLocked}
            rows={4}
            className={cn(
              'w-full rounded-lg border bg-surface-1 px-4 py-2.5 text-sm text-foreground outline-none transition-all resize-none',
              'border-border focus:border-primary/50 focus:ring-1 focus:ring-primary/20',
              isLocked && 'opacity-60 cursor-not-allowed'
            )}
          />
        </div>

        {/* Keywords */}
        <div className="space-y-1.5">
          <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Keywords</label>
          <input
            type="text"
            value={fields.keywords.join(', ')}
            onChange={e => handleChange('keywords', e.target.value.split(',').map(s => s.trim()).filter(Boolean))}
            disabled={isLocked}
            className={cn(
              'w-full rounded-lg border bg-surface-1 px-4 py-2.5 text-sm text-foreground outline-none transition-all',
              'border-border focus:border-primary/50 focus:ring-1 focus:ring-primary/20',
              isLocked && 'opacity-60 cursor-not-allowed'
            )}
          />
          <p className="text-xs text-muted-foreground">Comma-separated</p>
        </div>

        {/* Confidence */}
        {fields.extraction_confidence !== undefined && (
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Extraction Confidence</label>
            <div className="flex items-center gap-2">
              <div className="flex-1 h-1.5 rounded-full bg-surface-3">
                <motion.div
                  className="h-full rounded-full bg-gradient-to-r from-primary to-accent"
                  initial={{ width: 0 }}
                  animate={{ width: `${(fields.extraction_confidence || 0) * 100}%` }}
                  transition={{ duration: 0.6 }}
                />
              </div>
              <span className="text-xs font-mono text-foreground/70">
                {((fields.extraction_confidence || 0) * 100).toFixed(0)}%
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Actions */}
      {!isLocked && (
        <div className="flex items-center gap-3 pt-2">
          <motion.button
            whileHover={{ scale: 1.01 }}
            whileTap={{ scale: 0.99 }}
            onClick={handleSave}
            disabled={saving || !dirty}
            className={cn(
              'flex items-center gap-2 rounded-lg px-5 py-2.5 text-sm font-medium transition-all',
              dirty
                ? 'bg-primary text-primary-foreground hover:bg-primary/90'
                : 'bg-surface-3 text-muted-foreground cursor-not-allowed'
            )}
          >
            {saving ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : saved ? (
              <Check className="h-3.5 w-3.5" />
            ) : (
              <Save className="h-3.5 w-3.5" />
            )}
            {saved ? 'Saved' : 'Save changes'}
          </motion.button>

          <motion.button
            whileHover={{ scale: 1.01 }}
            whileTap={{ scale: 0.99 }}
            onClick={handleFinalize}
            disabled={finalizing || dirty || !saved}
            className={cn(
              'flex items-center gap-2 rounded-lg border px-5 py-2.5 text-sm font-medium transition-all',
              saved && !dirty
                ? 'border-status-completed/30 text-status-completed hover:bg-status-completed/5'
                : 'border-border text-muted-foreground cursor-not-allowed'
            )}
          >
            {finalizing ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Lock className="h-3.5 w-3.5" />
            )}
            Finalize
          </motion.button>
        </div>
      )}
    </motion.div>
  );
}
