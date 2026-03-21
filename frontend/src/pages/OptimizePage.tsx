import { useState } from "react";

/** Page for uploading resume and JD, then running optimization. */
export function OptimizePage() {
  const [resumeText, setResumeText] = useState("");
  const [jdText, setJdText] = useState("");

  return (
    <div className="mx-auto max-w-4xl px-4 py-12">
      <h1 className="text-3xl font-bold text-gray-900">Optimize Resume</h1>
      <p className="mt-2 text-gray-600">Paste your resume and target job description</p>

      <div className="mt-8 grid grid-cols-1 gap-6 md:grid-cols-2">
        <div>
          <label className="block text-sm font-medium text-gray-700">Resume</label>
          <textarea
            className="mt-1 w-full rounded-lg border border-gray-300 p-3 text-sm"
            rows={12}
            placeholder="Paste your resume here..."
            value={resumeText}
            onChange={(e) => setResumeText(e.target.value)}
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">Job Description</label>
          <textarea
            className="mt-1 w-full rounded-lg border border-gray-300 p-3 text-sm"
            rows={12}
            placeholder="Paste the job description here..."
            value={jdText}
            onChange={(e) => setJdText(e.target.value)}
          />
        </div>
      </div>

      <button
        className="mt-6 rounded-lg bg-blue-600 px-8 py-3 text-white hover:bg-blue-700 disabled:opacity-50"
        disabled={!resumeText || !jdText}
      >
        Optimize
      </button>
    </div>
  );
}
