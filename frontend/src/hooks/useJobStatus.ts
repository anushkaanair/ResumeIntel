import { useState, useEffect, useRef } from "react";
import { getOptimizationStatus, getOptimizationResult } from "../lib/api";

export type JobStatus = "idle" | "queued" | "running" | "completed" | "failed";

interface JobResult {
  ingestion?: { content: string; quality_score: number; metadata: Record<string, unknown> };
  generation?: { content: string; quality_score: number; suggestions: string[] };
  quality?: { content: string; quality_score: number; suggestions: string[] };
  weak_detection?: { content: string; quality_score: number; suggestions: string[] };
  tailoring?: { content: string; quality_score: number; metadata: Record<string, unknown> };
  interview?: { content: string; quality_score: number };
}

interface UseJobStatusReturn {
  status: JobStatus;
  result: JobResult | null;
  error: string | null;
}

/** Polls optimization job status and fetches results when complete. */
export function useJobStatus(jobId: string | null, pollIntervalMs = 2000): UseJobStatusReturn {
  const [status, setStatus] = useState<JobStatus>("idle");
  const [result, setResult] = useState<JobResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!jobId) {
      setStatus("idle");
      return;
    }

    setStatus("queued");

    const poll = async () => {
      try {
        const statusData = await getOptimizationStatus(jobId);
        const jobStatus: JobStatus = statusData.data.job_status || "queued";
        setStatus(jobStatus);

        if (jobStatus === "completed") {
          if (intervalRef.current) clearInterval(intervalRef.current);
          const resultData = await getOptimizationResult(jobId);
          setResult(resultData.data.results || resultData.data);
        } else if (jobStatus === "failed") {
          if (intervalRef.current) clearInterval(intervalRef.current);
          setError("Optimization pipeline failed. Please try again.");
        }
      } catch (err) {
        if (intervalRef.current) clearInterval(intervalRef.current);
        setError("Failed to check job status.");
      }
    };

    poll(); // immediate first poll
    intervalRef.current = setInterval(poll, pollIntervalMs);

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [jobId, pollIntervalMs]);

  return { status, result, error };
}
