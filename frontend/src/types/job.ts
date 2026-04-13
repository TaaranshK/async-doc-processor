export type JobStatus = 'queued' | 'processing' | 'completed' | 'failed' | 'cancelled';

export interface Job {
  id: string;
  document_id: string;
  filename: string;
  file_type: string;
  file_size: number;
  status: JobStatus;
  celery_task_id: string | null;
  current_stage: string | null;
  progress_pct: number;
  error_message: string | null;
  retry_count: number;
  created_at: string;
  updated_at: string;
}

export interface JobsListResponse {
  items: Job[];
  total: number;
  page: number;
  page_size: number;
}

export interface JobsFilter {
  search?: string;
  status?: JobStatus[];
  sort_by?: 'created_at' | 'status';
  sort_order?: 'asc' | 'desc';
  page?: number;
  page_size?: number;
}
