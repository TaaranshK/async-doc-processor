import { useState, useEffect } from 'react';
import { ProgressEvent } from '@/types/progress';

const EVENT_TYPES = [
  'document_received',
  'parsing_started',
  'parsing_completed',
  'extraction_started',
  'extraction_completed',
  'job_completed',
  'job_failed',
  'job_cancelled',
];

export function useSSE(jobId: string | null) {
  const [progress, setProgress] = useState<ProgressEvent | null>(null);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    if (!jobId) return;

    const base = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    const source = new EventSource(`${base}/api/v1/jobs/${jobId}/progress`);

    const handleEvent = (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data) as ProgressEvent;
        setProgress(data);
        if (['job_completed', 'job_failed', 'job_cancelled'].includes(data.event)) {
          setConnected(false);
        }
      } catch {
        // ignore malformed payloads
      }
    };

    EVENT_TYPES.forEach(type => source.addEventListener(type, handleEvent));

    source.onopen = () => setConnected(true);
    source.onerror = () => setConnected(false);

    return () => {
      EVENT_TYPES.forEach(type => source.removeEventListener(type, handleEvent));
      source.close();
    };
  }, [jobId]);

  return { progress, connected };
}
