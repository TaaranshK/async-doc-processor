import { useCallback, useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Upload, X, FileText, AlertCircle } from 'lucide-react';
import { useUpload } from '@/hooks/useUpload';
import { cn } from '@/lib/utils';
import { ProgressBar } from './ProgressBar';

interface UploadDropzoneProps {
  onUploadComplete: (jobIds: string[]) => void;
}

export function UploadDropzone({ onUploadComplete }: UploadDropzoneProps) {
  const { files, uploading, progress, error, addFiles, removeFile, upload, clearError } = useUpload();
  const [dragActive, setDragActive] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    const droppedFiles = Array.from(e.dataTransfer.files);
    addFiles(droppedFiles);
  }, [addFiles]);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      addFiles(Array.from(e.target.files));
    }
  }, [addFiles]);

  const handleSubmit = useCallback(async () => {
    if (files.length === 0) return;
    const jobIds = await upload();
    onUploadComplete(jobIds);
  }, [files, upload, onUploadComplete]);

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="w-full max-w-2xl mx-auto space-y-6">
      {/* Drop zone */}
      <motion.div
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        animate={dragActive ? { scale: 1.02 } : { scale: 1 }}
        transition={{ type: 'spring', stiffness: 300, damping: 20 }}
        className={cn(
          'relative flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed p-12 transition-all duration-300',
          'bg-surface-1 hover:bg-surface-2',
          dragActive
            ? 'drag-active border-primary'
            : 'border-border hover:border-muted-foreground/30',
          uploading && 'pointer-events-none opacity-60'
        )}
      >
        <input
          ref={inputRef}
          type="file"
          multiple
          accept=".pdf,.docx,.doc,.txt,.csv"
          onChange={handleFileSelect}
          className="hidden"
        />
        
        <motion.div
          animate={dragActive ? { y: -4, scale: 1.1 } : { y: 0, scale: 1 }}
          transition={{ type: 'spring', stiffness: 300, damping: 20 }}
        >
          <Upload className="mb-4 h-10 w-10 text-muted-foreground" />
        </motion.div>
        
        <p className="text-sm font-medium text-foreground">
          {dragActive ? 'Drop files here' : 'Drag & drop files or click to browse'}
        </p>
        <p className="mt-1 text-xs text-muted-foreground">
          PDF, DOCX, DOC, TXT, CSV — up to 50MB each
        </p>
      </motion.div>

      {/* Error */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, y: -8, height: 0 }}
            animate={{ opacity: 1, y: 0, height: 'auto' }}
            exit={{ opacity: 0, y: -8, height: 0 }}
            className="flex items-center gap-2 rounded-lg border border-destructive/20 bg-destructive/5 px-4 py-3 text-sm text-destructive"
          >
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
            <button onClick={clearError} className="ml-auto">
              <X className="h-3.5 w-3.5" />
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* File list */}
      <AnimatePresence mode="popLayout">
        {files.map((file, index) => (
          <motion.div
            key={`${file.name}-${index}`}
            layout
            initial={{ opacity: 0, y: 10, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="flex items-center gap-3 rounded-lg border border-border bg-surface-1 px-4 py-3"
          >
            <FileText className="h-4 w-4 shrink-0 text-primary" />
            <div className="flex-1 min-w-0">
              <p className="truncate text-sm font-medium text-foreground">{file.name}</p>
              <p className="text-xs text-muted-foreground">{formatSize(file.size)}</p>
            </div>
            <button
              onClick={(e) => { e.stopPropagation(); removeFile(index); }}
              className="rounded p-1 text-muted-foreground transition-colors hover:bg-surface-3 hover:text-foreground"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </motion.div>
        ))}
      </AnimatePresence>

      {/* Upload progress */}
      {uploading && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="space-y-2"
        >
          <ProgressBar value={progress} stage="Uploading files..." showLabel={false} />
          <p className="text-center text-xs text-muted-foreground">
            Uploading {files.length} file{files.length !== 1 ? 's' : ''}...
          </p>
        </motion.div>
      )}

      {/* Submit button */}
      <AnimatePresence>
        {files.length > 0 && !uploading && (
          <motion.button
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 8 }}
            whileHover={{ scale: 1.01 }}
            whileTap={{ scale: 0.99 }}
            onClick={handleSubmit}
            className="w-full rounded-lg bg-gradient-to-r from-primary to-accent px-6 py-3 text-sm font-medium text-primary-foreground transition-shadow hover:shadow-lg hover:shadow-primary/20"
          >
            Upload {files.length} file{files.length !== 1 ? 's' : ''}
          </motion.button>
        )}
      </AnimatePresence>
    </div>
  );
}
