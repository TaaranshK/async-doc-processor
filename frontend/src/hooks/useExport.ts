import { useCallback } from 'react';
import { exportJSON, exportCSV, downloadBlob } from '@/api/export';
import { toast } from '@/hooks/use-toast';

export function useExport() {
  const handleExportJSON = useCallback(async (jobIds: string[]) => {
    try {
      const blob = await exportJSON(jobIds);
      downloadBlob(blob, `export-${Date.now()}.json`);
      toast({ title: 'Export complete', description: 'JSON file downloaded successfully.' });
    } catch {
      toast({ title: 'Export failed', description: 'Could not generate JSON export.', variant: 'destructive' });
    }
  }, []);

  const handleExportCSV = useCallback(async (jobIds: string[]) => {
    try {
      const blob = await exportCSV(jobIds);
      downloadBlob(blob, `export-${Date.now()}.csv`);
      toast({ title: 'Export complete', description: 'CSV file downloaded successfully.' });
    } catch {
      toast({ title: 'Export failed', description: 'Could not generate CSV export.', variant: 'destructive' });
    }
  }, []);

  return { exportJSON: handleExportJSON, exportCSV: handleExportCSV };
}
