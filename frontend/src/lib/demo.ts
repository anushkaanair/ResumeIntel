/**
 * Public demo mode (VITE_DEMO=1): no backend. The UI replays one recorded real pipeline run
 * (src/demo/run.json) so people can look around; anything that would need the live model is
 * refused with a clear message instead of faking a result.
 */
import type { AxiosInstance, AxiosResponse, InternalAxiosRequestConfig } from "axios";
import run from "../demo/run.json";

export const DEMO: boolean = (import.meta as any).env.VITE_DEMO === "1";
export const DEMO_JOB_ID = "demo";

export function seedDemoSession(): void {
  try {
    sessionStorage.setItem("ri_resume_text", run.resume_text);
    sessionStorage.setItem("ri_jd_text", run.job_description);
    sessionStorage.setItem("ri_job_id", DEMO_JOB_ID);
    sessionStorage.setItem("ri_resume_filename", "sample_resume.pdf");
  } catch { /* storage unavailable: the canvas still renders from the result */ }
}

function reply(config: InternalAxiosRequestConfig, data: unknown): AxiosResponse {
  return { data, status: 200, statusText: "OK", headers: {}, config };
}

export function installDemoAdapter(api: AxiosInstance): void {
  api.defaults.adapter = async (config) => {
    const url = (config.url || "").replace(/^\/+/, "");
    const method = (config.method || "get").toLowerCase();
    if (method === "post" && url === "optimize") return reply(config, { status: "ok", data: { job_id: DEMO_JOB_ID } });
    if (method === "get" && /^optimize\/[^/]+\/status$/.test(url))
      return reply(config, { status: "ok", data: { job_id: DEMO_JOB_ID, job_status: "completed" } });
    if (method === "get" && /^optimize\/[^/]+\/result$/.test(url)) return reply(config, { status: "ok", data: run.result });
    if (method === "get" && /^auth\/\w+\/status$/.test(url)) return reply(config, { status: "ok", data: { connected: false } });
    throw new Error("This action needs the live model, so it is disabled in the public demo. Run ResumeIntel locally to use it.");
  };
}
