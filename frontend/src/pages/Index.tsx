import { useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { FileText, ArrowRight } from 'lucide-react';
import { UploadDropzone } from '@/components/UploadDropzone';

const Index = () => {
  const navigate = useNavigate();

  const handleUploadComplete = useCallback((jobIds: string[]) => {
    navigate('/dashboard', { state: { newJobIds: jobIds } });
  }, [navigate]);

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.4 }}
      className="flex min-h-screen flex-col items-center justify-center px-4 py-16"
    >
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1, duration: 0.5 }}
        className="mb-12 text-center"
      >
        <div className="mx-auto mb-6 flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-primary/20 to-accent/20 border border-primary/10">
          <FileText className="h-7 w-7 text-primary" />
        </div>
        <h1 className="text-3xl font-semibold tracking-tight text-foreground">
          Document Processor
        </h1>
        <p className="mt-2 text-sm text-muted-foreground max-w-md mx-auto">
          Drop your documents to start async processing. We'll extract structured data and let you review the results.
        </p>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2, duration: 0.5 }}
        className="w-full max-w-2xl"
      >
        <UploadDropzone onUploadComplete={handleUploadComplete} />
      </motion.div>

      <motion.button
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.5 }}
        onClick={() => navigate('/dashboard')}
        className="mt-8 flex items-center gap-1.5 text-xs text-muted-foreground transition-colors hover:text-foreground"
      >
        Go to dashboard
        <ArrowRight className="h-3 w-3" />
      </motion.button>
    </motion.div>
  );
};

export default Index;
