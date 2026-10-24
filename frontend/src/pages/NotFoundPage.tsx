import { Link } from "react-router-dom";
import { FileSearch } from "lucide-react";

export function NotFoundPage() {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        minHeight: "60vh",
        gap: "1.25rem",
        padding: "2rem",
        textAlign: "center",
      }}
    >
      <FileSearch size={48} style={{ color: "#38bdf8", opacity: 0.7 }} />
      <h1 style={{ fontSize: "2rem", fontWeight: 700, color: "#f1f5f9" }}>404 — Page not found</h1>
      <p style={{ color: "#94a3b8", maxWidth: "360px", lineHeight: 1.6 }}>
        The page you're looking for doesn't exist or has been moved.
      </p>
      <Link
        to="/"
        style={{
          marginTop: "0.5rem",
          padding: "0.6rem 1.4rem",
          borderRadius: "8px",
          background: "rgba(56,189,248,0.12)",
          border: "1px solid rgba(56,189,248,0.3)",
          color: "#38bdf8",
          textDecoration: "none",
          fontSize: "0.9rem",
        }}
      >
        ← Back to home
      </Link>
    </div>
  );
}
