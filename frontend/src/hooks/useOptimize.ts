import { useState } from "react";
import { startOptimization } from "../lib/api";

interface UseOptimizeReturn {
  jobId: string | null;
  loading: boolean;
  error: string | null;
  optimize: (resumeText: string, jobDescription: string) => Promise<void>;
  reset: () => void;
}

/** Starts the optimization pipeline and returns the job ID for polling. */
export function useOptimize(): UseOptimizeReturn {
  const [jobId, setJobId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const optimize = async (resumeText: string, jobDescription: string) => {
    setLoading(true);
    setError(null);
    setJobId(null);

    try {
      const data = await startOptimization(resumeText, jobDescription);
      const id = data.data?.job_id;
      if (!id) throw new Error("No job ID returned from server");
      setJobId(id);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to start optimization";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  const reset = () => {
    setJobId(null);
    setError(null);
    setLoading(false);
  };

  return { jobId, loading, error, optimize, reset };
}
