import { useState, useEffect, useCallback, useRef } from 'react';
import { ProgressEvent } from '@/types/progress';

// Simulated SSE for demo purposes
const STAGES = [
  { stage: 'upload_received', pct: 10 },
  { stage: 'parsing_started', pct: 25 },
  { stage: 'parsing_completed', pct: 45 },
  { stage: 'extraction_started', pct: 60 },
  { stage: 'extraction_completed', pct: 85 },
  { stage: 'storage_completed', pct: 100 },
];

export function useSSE(jobId: string | null) {
  const [progress, setProgress] = useState<ProgressEvent | null>(null);
  const [connected, setConnected] = useState(false);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const stageRef = useRef(0);

  const startSimulation = useCallback(() => {
    if (!jobId) return;
    setConnected(true);
    stageRef.current = 0;

    intervalRef.current = setInterval(() => {
      if (stageRef.current >= STAGES.length) {
        if (intervalRef.current) clearInterval(intervalRef.current);
        setConnected(false);
        return;
      }

      const s = STAGES[stageRef.current];
      setProgress({
        event: s.stage,
        job_id: jobId,
        progress_pct: s.pct,
        stage: s.stage,
        timestamp: new Date().toISOString(),
        metadata: {},
      });
      stageRef.current += 1;
    }, 1500);
  }, [jobId]);

  useEffect(() => {
    if (jobId) startSimulation();
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [jobId, startSimulation]);

  return { progress, connected };
}
