import { get, post, put } from '@/lib/api-client';
import { JobResult, ExtractedFields } from '@/types/result';

export async function fetchResult(jobId: string): Promise<JobResult> {
  return get<JobResult>(`/jobs/${jobId}/result`);
}

export async function updateResult(jobId: string, reviewedOutput: ExtractedFields): Promise<JobResult> {
  return put<JobResult>(`/jobs/${jobId}/result`, { reviewed_output: reviewedOutput });
}

export async function finalizeResult(jobId: string): Promise<JobResult> {
  return post<JobResult>(`/jobs/${jobId}/result/finalize`);
}
