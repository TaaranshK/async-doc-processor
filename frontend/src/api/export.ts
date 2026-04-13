export async function exportJSON(jobIds: string[]): Promise<Blob> {
  const base = import.meta.env.VITE_API_URL || 'http://localhost:8000';
  const url =
    jobIds.length === 1
      ? `${base}/api/v1/jobs/${jobIds[0]}/export?format=json`
      : `${base}/api/v1/export/bulk?ids=${jobIds.join(',')}&format=json`;

  const response = await fetch(url);
  if (!response.ok) throw new Error('Export failed');
  return response.blob();
}

export async function exportCSV(jobIds: string[]): Promise<Blob> {
  const base = import.meta.env.VITE_API_URL || 'http://localhost:8000';
  const url =
    jobIds.length === 1
      ? `${base}/api/v1/jobs/${jobIds[0]}/export?format=csv`
      : `${base}/api/v1/export/bulk?ids=${jobIds.join(',')}&format=csv`;

  const response = await fetch(url);
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
