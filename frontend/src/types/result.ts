export interface ExtractedFields {
  title: string;
  category: string;
  summary: string;
  keywords: string[];
  file_metadata: {
    name: string;
    type: string;
    size: number;
  };
  status: string;
  extraction_confidence?: number;
}

export interface JobResult {
  id: string;
  job_id: string;
  raw_output: ExtractedFields;
  reviewed_output: ExtractedFields | null;
  is_finalized: boolean;
  finalized_at: string | null;
  created_at: string;
  updated_at: string;
}
