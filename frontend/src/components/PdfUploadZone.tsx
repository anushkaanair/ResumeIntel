import { useRef, useState, DragEvent, ChangeEvent } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { uploadResume } from "../lib/api";

type UploadState = "idle" | "dragging" | "uploading" | "success" | "error";

interface PdfUploadZoneProps {
  /** Called with the extracted plain-text resume once the upload succeeds. */
  onTextExtracted: (text: string, filename: string) => void;
}

/**
 * Drag-and-drop / click-to-upload zone for PDF and DOCX resume files.
 * Uploads to the backend parser and returns extracted plain text via onTextExtracted.
 */
export function PdfUploadZone({ onTextExtracted }: PdfUploadZoneProps) {
  const [uploadState, setUploadState] = useState<UploadState>("idle");
  const [uploadedFilename, setUploadedFilename] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const ACCEPTED = ".pdf,.doc,.docx,.txt";
  const ACCEPTED_TYPES = [
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
  ];

  const processFile = async (file: File) => {
    if (!ACCEPTED_TYPES.includes(file.type) && !file.name.match(/\.(pdf|docx?|txt)$/i)) {
      setUploadState("error");
      setErrorMessage("Unsupported file type. Please upload a PDF, DOCX, or TXT file.");
      return;
    }

    setUploadState("uploading");
    setErrorMessage(null);

    try {
      const data = await uploadResume(file);
      const text: string = data.data?.text || "";
      if (!text.trim()) throw new Error("No text could be extracted from the file.");
      setUploadedFilename(file.name);
      setUploadState("success");
      onTextExtracted(text, file.name);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Upload failed. Please try again.";
      setUploadState("error");
      setErrorMessage(msg);
    }
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file) processFile(file);
  };

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) processFile(file);
    // Reset input so same file can be re-selected after an error
    e.target.value = "";
  };

  const reset = () => {
    setUploadState("idle");
    setUploadedFilename(null);
    setErrorMessage(null);
  };

  const borderColor =
    uploadState === "dragging"
      ? "border-blue-500 bg-blue-50"
      : uploadState === "success"
      ? "border-green-400 bg-green-50"
      : uploadState === "error"
      ? "border-red-400 bg-red-50"
      : "border-gray-300 bg-gray-50 hover:border-blue-400 hover:bg-blue-50";

  return (
    <div className="flex h-full flex-col">
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED}
        className="hidden"
        onChange={handleFileChange}
        aria-label="Upload resume file"
      />

      <motion.div
        className={`flex flex-1 cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed p-8 text-center transition-colors ${borderColor}`}
        style={{ minHeight: "240px" }}
        onClick={() => uploadState !== "uploading" && inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          if (uploadState !== "uploading") setUploadState("dragging");
        }}
        onDragLeave={() => {
          if (uploadState === "dragging") setUploadState("idle");
        }}
        onDrop={handleDrop}
        animate={{ scale: uploadState === "dragging" ? 1.01 : 1 }}
        transition={{ type: "spring", stiffness: 300, damping: 25 }}
      >
        <AnimatePresence mode="wait">
          {uploadState === "uploading" && (
            <motion.div
              key="uploading"
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="flex flex-col items-center gap-3"
            >
              <motion.div
                className="h-10 w-10 rounded-full border-4 border-blue-200 border-t-blue-600"
                animate={{ rotate: 360 }}
                transition={{ duration: 0.8, repeat: Infinity, ease: "linear" }}
              />
              <p className="text-sm font-medium text-blue-700">Parsing your resume…</p>
            </motion.div>
          )}

          {uploadState === "success" && (
            <motion.div
              key="success"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0 }}
              className="flex flex-col items-center gap-3"
            >
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-green-100">
                <svg className="h-6 w-6 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <div>
                <p className="text-sm font-semibold text-green-700">Resume imported</p>
                <p className="mt-0.5 text-xs text-green-600">{uploadedFilename}</p>
              </div>
              <button
                type="button"
                onClick={(e) => { e.stopPropagation(); reset(); }}
                className="mt-1 text-xs text-gray-500 underline hover:text-gray-700"
              >
                Replace file
              </button>
            </motion.div>
          )}

          {uploadState === "error" && (
            <motion.div
              key="error"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0 }}
              className="flex flex-col items-center gap-3"
            >
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-red-100">
                <svg className="h-6 w-6 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </div>
              <p className="text-sm font-medium text-red-700">{errorMessage}</p>
              <button
                type="button"
                onClick={(e) => { e.stopPropagation(); reset(); }}
                className="text-xs text-gray-500 underline hover:text-gray-700"
              >
                Try again
              </button>
            </motion.div>
          )}

          {(uploadState === "idle" || uploadState === "dragging") && (
            <motion.div
              key="idle"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="flex flex-col items-center gap-3"
            >
              <div className={`flex h-14 w-14 items-center justify-center rounded-full transition-colors ${uploadState === "dragging" ? "bg-blue-100" : "bg-gray-100"}`}>
                <svg
                  className={`h-7 w-7 transition-colors ${uploadState === "dragging" ? "text-blue-600" : "text-gray-400"}`}
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                    d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                  />
                </svg>
              </div>
              <div>
                <p className={`text-sm font-semibold transition-colors ${uploadState === "dragging" ? "text-blue-700" : "text-gray-700"}`}>
                  {uploadState === "dragging" ? "Drop to import" : "Drop your resume here"}
                </p>
                <p className="mt-0.5 text-xs text-gray-400">or click to browse — PDF, DOCX, TXT</p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </div>
  );
}
