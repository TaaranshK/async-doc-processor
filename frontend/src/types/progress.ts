export interface ProgressEvent {
  event: string;
  job_id: string;
  progress_pct: number;
  stage: string;
  timestamp: string;
  metadata: Record<string, unknown>;
}
