import axios from "axios";

const API_BASE = (import.meta as any).env.VITE_API_URL || "http://localhost:8000/api/v1";

export const api = axios.create({
  baseURL: API_BASE,
  headers: { "Content-Type": "application/json" },
});

/** Upload and parse a resume file. */
export async function uploadResume(file: File) {
  const formData = new FormData();
  formData.append("file", file);
  const { data } = await api.post("/resume/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

/** Start the optimization pipeline. */
export async function startOptimization(resumeText: string, jobDescription: string) {
  const { data } = await api.post("/optimize", {
    resume_text: resumeText,
    job_description: jobDescription,
  });
  return data;
}

/** Check optimization job status. */
export async function getOptimizationStatus(jobId: string) {
  const { data } = await api.get(`/optimize/${jobId}/status`);
  return data;
}

/** Get optimization results. */
export async function getOptimizationResult(jobId: string) {
  const { data } = await api.get(`/optimize/${jobId}/result`);
  return data;
}

/** Get alignment score between resume and JD. */
export async function getAlignmentScore(resumeText: string, jobDescription: string) {
  const { data } = await api.post("/alignment/score", {
    resume_text: resumeText,
    job_description: jobDescription,
  });
  return data;
}

/** Re-optimize an entire section. */
export async function reoptimizeSection(sectionId: string, sectionTitle: string) {
  const { data } = await api.post(`/canvas/section/${sectionId}/reoptimize`, {
    section_id: sectionId,
    section_title: sectionTitle,
  });
  return data;
}

/** Enhance a section with manual AI prompt. */
export async function enhanceSection(sectionId: string, sectionTitle: string, prompt: string) {
  const { data } = await api.post(`/canvas/section/${sectionId}/enhance`, {
    section_id: sectionId,
    section_title: sectionTitle,
    prompt,
  });
  return data;
}

/** Refresh LinkedIn profile. */
export async function refreshLinkedin() {
  const { data } = await api.post("/canvas/profile/linkedin/refresh");
  return data;
}

/** Refresh GitHub profile. */
export async function refreshGithub() {
  const { data } = await api.post("/canvas/profile/github/refresh");
  return data;
}
