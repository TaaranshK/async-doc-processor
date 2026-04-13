import { get, post } from '@/lib/api-client';
import { Job, JobsListResponse, JobsFilter } from '@/types/job';
import { JobResult } from '@/types/result';

export async function fetchJobs(filters: JobsFilter = {}): Promise<JobsListResponse> {
  const params = new URLSearchParams();
  
  if (filters.search) params.append('search', filters.search);
  if (filters.status?.length) params.append('status', filters.status.join(','));
  params.append('page', String(filters.page || 1));
  params.append('page_size', String(filters.page_size || 10));
  if (filters.sort_by) params.append('sort_by', filters.sort_by);
  if (filters.sort_order) params.append('sort_order', filters.sort_order);

  const queryString = params.toString();
  const endpoint = queryString ? `/jobs?${queryString}` : '/jobs';
  
  return get<JobsListResponse>(endpoint);
}

export async function fetchJob(jobId: string): Promise<Job> {
  return get<Job>(`/jobs/${jobId}`);
}

export async function retryJob(jobId: string): Promise<Job> {
  return post<Job>(`/jobs/${jobId}/retry`);
}

export async function cancelJob(jobId: string): Promise<Job> {
  return post<Job>(`/jobs/${jobId}/cancel`);
}
