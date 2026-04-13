import { get, post, put } from '@/lib/api-client';
import { JobResult, ExtractedFields } from '@/types/result';

export async function uploadDocuments(files: File[]): Promise<{ items: { job_id: string }[] }> {
  const formData = new FormData();
  files.forEach(file => formData.append('files', file));

  const response = await fetch(
    `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/v1/documents/upload`,
    { method: 'POST', body: formData }
  );
  if (!response.ok) throw new Error('Upload failed');
  return response.json();
}

export async function fetchResult(jobId: string): Promise<JobResult> {
  return get<JobResult>(`/jobs/${jobId}/result`);
}

export async function updateResult(jobId: string, reviewedOutput: ExtractedFields): Promise<JobResult> {
  return put<JobResult>(`/jobs/${jobId}/result`, reviewedOutput);
}

export async function finalizeResult(jobId: string): Promise<JobResult> {
  return post<JobResult>(`/jobs/${jobId}/finalize`);
}
