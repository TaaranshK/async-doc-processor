import { motion } from 'framer-motion';
import { Plus, FileText } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { JobsTable } from '@/components/JobsTable';

export default function DashboardPage() {
  const navigate = useNavigate();

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.4 }}
      className="min-h-screen px-4 py-8 sm:px-6 lg:px-8"
    >
      <div className="mx-auto max-w-5xl space-y-8">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="flex items-center justify-between"
        >
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-primary/20 to-accent/20 border border-primary/10">
              <FileText className="h-4.5 w-4.5 text-primary" />
            </div>
            <div>
              <h1 className="text-xl font-semibold tracking-tight text-foreground">Jobs</h1>
              <p className="text-xs text-muted-foreground">Monitor and manage document processing</p>
            </div>
          </div>
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => navigate('/')}
            className="flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-shadow hover:shadow-lg hover:shadow-primary/20"
          >
            <Plus className="h-3.5 w-3.5" />
            Upload
          </motion.button>
        </motion.div>

        {/* Table */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
        >
          <JobsTable />
        </motion.div>
      </div>
    </motion.div>
  );
}
