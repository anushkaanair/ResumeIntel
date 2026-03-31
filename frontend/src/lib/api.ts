import axios from "axios";

const API_BASE = (import.meta as any).env.VITE_API_URL || "http://localhost:8000/api/v1";

export const api = axios.create({
  baseURL: API_BASE,
  headers: { "Content-Type": "application/json" },
});

// ─── Resume ──────────────────────────────────────────────
export async function uploadResume(file: File) {
  const formData = new FormData();
  formData.append("file", file);
  const { data } = await api.post("/resume/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

// ─── Optimize ────────────────────────────────────────────
export async function startOptimization(resumeText: string, jobDescription: string) {
  const { data } = await api.post("/optimize", {
    resume_text: resumeText,
    job_description: jobDescription,
  });
  return data;
}

export async function getOptimizationStatus(jobId: string) {
  const { data } = await api.get(`/optimize/${jobId}/status`);
  return data;
}

export async function getOptimizationResult(jobId: string) {
  const { data } = await api.get(`/optimize/${jobId}/result`);
  return data;
}

// ─── Alignment ───────────────────────────────────────────
export async function getAlignmentScore(resumeText: string, jobDescription: string) {
  const { data } = await api.post("/alignment/score", {
    resume_text: resumeText,
    job_description: jobDescription,
  });
  return data;
}

// ─── JD ──────────────────────────────────────────────────
export async function parseJD(rawText: string) {
  const { data } = await api.post("/jd/parse", { raw_text: rawText });
  return data;
}

export async function getJD(jdId: string) {
  const { data } = await api.get(`/jd/${jdId}`);
  return data;
}

// ─── Bullet ──────────────────────────────────────────────
export async function scoreBullet(bulletId: string, text: string, jobDescription = "") {
  const { data } = await api.post(`/canvas/bullet/${bulletId}/score`, {
    text,
    job_description: jobDescription,
  });
  return data;
}

export async function suggestBullet(
  bulletId: string,
  text: string,
  jobDescription = "",
  resumeText = ""
) {
  const { data } = await api.post(`/canvas/bullet/${bulletId}/suggest`, {
    text,
    job_description: jobDescription,
    resume_text: resumeText,
  });
  return data;
}

export async function acceptBullet(bulletId: string, version: "ai" | "user" | "original", text = "") {
  const { data } = await api.post(`/canvas/bullet/${bulletId}/accept`, { version, text });
  return data;
}

export async function disputeBullet(
  bulletId: string,
  bulletText: string,
  userDisagreement: string,
  jobDescription = "",
  resumeText = ""
) {
  const { data } = await api.post(`/canvas/dispute/${bulletId}`, {
    bullet_text: bulletText,
    user_disagreement: userDisagreement,
    job_description: jobDescription,
    resume_text: resumeText,
  });
  return data;
}

// ─── Section ─────────────────────────────────────────────
export async function reoptimizeSection(
  sectionId: string,
  sectionTitle: string,
  sectionContent = "",
  jobDescription = "",
  resumeText = ""
) {
  const { data } = await api.post(`/canvas/section/${sectionId}/reoptimize`, {
    section_id: sectionId,
    section_title: sectionTitle,
    section_content: sectionContent,
    job_description: jobDescription,
    resume_text: resumeText,
  });
  return data;
}

export async function enhanceSection(
  sectionId: string,
  sectionTitle: string,
  prompt: string,
  sectionContent = "",
  resumeText = ""
) {
  const { data } = await api.post(`/canvas/section/${sectionId}/enhance`, {
    section_id: sectionId,
    section_title: sectionTitle,
    prompt,
    section_content: sectionContent,
    resume_text: resumeText,
  });
  return data;
}

// ─── ATS ─────────────────────────────────────────────────
export async function quickATSScore(resumeText: string, jobDescription = "") {
  const { data } = await api.post("/canvas/ats/quick-score", {
    resume_text: resumeText,
    job_description: jobDescription,
  });
  return data;
}

// ─── Profile sync ─────────────────────────────────────────
export async function refreshLinkedin(jobDescription = "", lastSyncAt = "") {
  const { data } = await api.post("/canvas/profile/linkedin/refresh", {
    job_description: jobDescription,
    last_sync_at: lastSyncAt,
  });
  return data;
}

export async function refreshGithub(jobDescription = "", lastSyncAt = "") {
  const { data } = await api.post("/canvas/profile/github/refresh", {
    job_description: jobDescription,
    last_sync_at: lastSyncAt,
  });
  return data;
}

// ─── Export ──────────────────────────────────────────────
export async function exportCanvas(
  resumeId: string,
  sections: object[],
  format: "docx" | "pdf" = "docx"
) {
  const resp = await api.post(
    "/canvas/export",
    { resume_id: resumeId, sections, format },
    { responseType: "blob" }
  );
  return resp;
}

// ─── Version history ─────────────────────────────────────
export async function createSnapshot(resumeId: string, content: string, changeSource = "user_edit") {
  const { data } = await api.post(`/canvas/${resumeId}/version/snapshot`, {
    resume_id: resumeId,
    content,
    change_source: changeSource,
  });
  return data;
}

export async function getVersionHistory(resumeId: string) {
  const { data } = await api.get(`/canvas/${resumeId}/version/history`);
  return data;
}

export async function getVersionDiff(resumeId: string, versionId: string) {
  const { data } = await api.get(`/canvas/${resumeId}/version/${versionId}/diff`);
  return data;
}

export async function revertVersion(resumeId: string, versionId: string) {
  const { data } = await api.post(`/canvas/${resumeId}/version/revert`, {
    version_id: versionId,
  });
  return data;
}

// ─── Interview ───────────────────────────────────────────
export async function generateInterview(jobId: string, resumeText: string, jobDescription: string, resumeId = "") {
  const { data } = await api.post(`/interview/${jobId}/generate`, {
    resume_text: resumeText,
    job_description: jobDescription,
    resume_id: resumeId,
  });
  return data;
}

export async function getInterviewData(jobId: string) {
  const { data } = await api.get(`/interview/${jobId}`);
  return data;
}

export async function practiceAnswer(
  questionId: string,
  userAnswer: string,
  questionText = "",
  questionCategory = "behavioral",
  jobDescription = "",
  resumeText = ""
) {
  const { data } = await api.post(`/interview/question/${questionId}/answer`, {
    user_answer: userAnswer,
    question_text: questionText,
    question_category: questionCategory,
    job_description: jobDescription,
    resume_text: resumeText,
  });
  return data;
}
