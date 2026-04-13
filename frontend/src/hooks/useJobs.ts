import { useQuery } from '@tanstack/react-query';
import { fetchJobs, fetchJob } from '@/api/jobs';
import { JobsFilter } from '@/types/job';

export function useJobs(filters: JobsFilter = {}) {
  return useQuery({
    queryKey: ['jobs', filters],
    queryFn: () => fetchJobs(filters),
    refetchInterval: 5000,
  });
}

export function useJob(jobId: string) {
  return useQuery({
    queryKey: ['job', jobId],
    queryFn: () => fetchJob(jobId),
    enabled: !!jobId,
    refetchInterval: 3000,
  });
}
