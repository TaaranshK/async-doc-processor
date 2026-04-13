import { post } from '@/lib/api-client';
import { JobResult } from '@/types/result';

export async function exportJSON(jobIds: string[]): Promise<Blob> {
  const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/v1/export/json`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ job_ids: jobIds }),
  });
  
  if (!response.ok) throw new Error('Export failed');
  return response.blob();
}

export async function exportCSV(jobIds: string[]): Promise<Blob> {
  const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/v1/export/csv`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ job_ids: jobIds }),
  });
  
  if (!response.ok) throw new Error('Export failed');
  return response.blob();
}

export function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
