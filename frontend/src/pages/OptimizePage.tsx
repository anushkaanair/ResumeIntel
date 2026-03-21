import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { Button } from "../components/Button";
import { PdfUploadZone } from "../components/PdfUploadZone";
import { startOptimization } from "../lib/api";

type ResumeInputMode = "paste" | "pdf";

/** Page for uploading resume and JD, then running optimization. */
export function OptimizePage() {
  const [resumeMode, setResumeMode] = useState<ResumeInputMode>("paste");
  const [resumeText, setResumeText] = useState("");
  const [resumeFilename, setResumeFilename] = useState<string | null>(null);
  const [jdText, setJdText] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  const handleModeSwitch = (mode: ResumeInputMode) => {
    setResumeMode(mode);
    // Clear resume text when switching modes to avoid stale data confusion
    setResumeText("");
    setResumeFilename(null);
  };

  const handlePdfExtracted = (text: string, filename: string) => {
    setResumeText(text);
    setResumeFilename(filename);
  };

  const handleOptimize = async () => {
    if (resumeText.length < 50 || jdText.length < 20) return;
    setLoading(true);
    setError(null);
    try {
      const data = await startOptimization(resumeText, jdText);
      const jobId = data.data?.job_id;
      if (!jobId) throw new Error("No job ID returned from server.");
      navigate(`/results/${jobId}`);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to start optimization.";
      setError(message);
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-4xl px-4 py-12">
      {/* Header */}
      <h1 className="text-3xl font-bold text-gray-900">Optimize Resume</h1>
      <p className="mt-2 text-gray-500">
        Import or paste your resume, add the target job description, and let the AI pipeline do the rest.
      </p>

      {/* Error banner */}
      {error && (
        <motion.div
          initial={{ opacity: 0, y: -4 }}
          animate={{ opacity: 1, y: 0 }}
          className="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
        >
          {error}
        </motion.div>
      )}

      <div className="mt-8 grid grid-cols-1 gap-6 md:grid-cols-2">
        {/* ── Resume column ── */}
        <div className="flex flex-col gap-3">
          {/* Mode toggle — the two starting options */}
          <div className="flex items-center gap-1 rounded-lg border border-gray-200 bg-gray-50 p-1">
            <button
              type="button"
              onClick={() => handleModeSwitch("paste")}
              className={`flex flex-1 items-center justify-center gap-1.5 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                resumeMode === "paste"
                  ? "bg-white text-blue-700 shadow-sm"
                  : "text-gray-500 hover:text-gray-700"
              }`}
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
                />
              </svg>
              Paste Text
            </button>
            <button
              type="button"
              onClick={() => handleModeSwitch("pdf")}
              className={`flex flex-1 items-center justify-center gap-1.5 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                resumeMode === "pdf"
                  ? "bg-white text-blue-700 shadow-sm"
                  : "text-gray-500 hover:text-gray-700"
              }`}
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                />
              </svg>
              Import PDF
            </button>
          </div>

          {/* Resume input — animates between paste and PDF mode */}
          <AnimatePresence mode="wait">
            {resumeMode === "paste" ? (
              <motion.div
                key="paste"
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -8 }}
                transition={{ duration: 0.15 }}
                className="flex flex-col"
              >
                <label className="mb-1 block text-sm font-medium text-gray-700">
                  Resume <span className="text-gray-400">(min 50 chars)</span>
                </label>
                <textarea
                  className="w-full rounded-lg border border-gray-300 p-3 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  rows={14}
                  placeholder="Paste your resume here..."
                  value={resumeText}
                  onChange={(e) => setResumeText(e.target.value)}
                />
                <p className="mt-1 text-xs text-gray-400">{resumeText.length} characters</p>
              </motion.div>
            ) : (
              <motion.div
                key="pdf"
                initial={{ opacity: 0, x: 8 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 8 }}
                transition={{ duration: 0.15 }}
                className="flex flex-col"
              >
                <label className="mb-1 block text-sm font-medium text-gray-700">
                  Resume <span className="text-gray-400">— PDF, DOCX, or TXT</span>
                </label>
                <PdfUploadZone onTextExtracted={handlePdfExtracted} />

                {/* Show character count + preview toggle after successful import */}
                {resumeText && resumeFilename && (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="mt-2 flex items-center justify-between text-xs text-gray-400"
                  >
                    <span>{resumeText.length} characters extracted</span>
                    <button
                      type="button"
                      className="text-blue-500 underline hover:text-blue-700"
                      onClick={() => handleModeSwitch("paste")}
                    >
                      Edit extracted text
                    </button>
                  </motion.div>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* ── Job Description column ── */}
        <div className="flex flex-col gap-3">
          <div className="rounded-lg border border-transparent bg-transparent p-1">
            <p className="px-3 py-2 text-sm font-medium text-gray-700">Job Description</p>
          </div>
          <div className="flex flex-col">
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Job Description <span className="text-gray-400">(min 20 chars)</span>
            </label>
            <textarea
              className="w-full rounded-lg border border-gray-300 p-3 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              rows={14}
              placeholder="Paste the job description here..."
              value={jdText}
              onChange={(e) => setJdText(e.target.value)}
            />
            <p className="mt-1 text-xs text-gray-400">{jdText.length} characters</p>
          </div>
        </div>
      </div>

      {/* Submit */}
      <div className="mt-6 flex items-center gap-4">
        <Button
          disabled={resumeText.length < 50 || jdText.length < 20}
          loading={loading}
          onClick={handleOptimize}
        >
          {loading ? "Starting Pipeline…" : "Optimize Resume"}
        </Button>

        {resumeText.length < 50 && resumeText.length > 0 && (
          <p className="text-xs text-gray-400">Resume needs {50 - resumeText.length} more characters</p>
        )}
        {resumeText.length === 0 && (
          <p className="text-xs text-gray-400">
            {resumeMode === "pdf" ? "Import a file to get started" : "Paste your resume to get started"}
          </p>
        )}
      </div>
    </div>
  );
}
