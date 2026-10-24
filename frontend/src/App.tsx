import { BrowserRouter, HashRouter, Link, Routes, Route } from "react-router-dom";
import { DEMO, DEMO_JOB_ID } from "./lib/demo";

// GitHub Pages cannot rewrite deep links, so the static demo uses hash routing.
const Router = DEMO ? HashRouter : BrowserRouter;
import { HomePage } from "./pages/HomePage";
import { OptimizePage } from "./pages/OptimizePage";
import { ResultsPage } from "./pages/ResultsPage";
import { CanvasPage } from "./pages/CanvasPage";
import { InterviewPage } from "./pages/InterviewPage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { AccessGate } from "./components/AccessGate";
import { Navbar } from "./components/Navbar";
import { Footer } from "./components/Footer";

/** Root application component with routing. */
export function App() {
  return (
    <Router>
      <AccessGate>
      <div className="min-h-screen flex flex-col" style={{ background: 'var(--bg, #06060f)' }}>
        {DEMO && (
          <div style={{ background: '#312e81', color: '#e0e7ff', fontSize: 13, textAlign: 'center', padding: '6px 12px' }}>
            Public demo — replaying one recorded real run (sample resume, Datadog posting, local 3B model). Nothing here calls a model.{' '}
            <Link to={`/canvas/${DEMO_JOB_ID}`} style={{ textDecoration: 'underline' }}>Open the result</Link> ·{' '}
            <a href="https://github.com/anushkaanair/ResumeIntel" style={{ textDecoration: 'underline' }}>Run it yourself</a>
          </div>
        )}
        <Navbar />
        <div className="flex-1">
          <Routes>
            <Route path="/" element={<HomePage />} />
            {/* V1 routes (kept for compatibility) */}
            <Route path="/optimize" element={<OptimizePage />} />
            <Route path="/results/:jobId" element={<ResultsPage />} />
            {/* V2 routes */}
            <Route path="/canvas/:resumeId" element={<CanvasPage />} />
            <Route path="/interview/:jobId" element={<InterviewPage />} />
            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </div>
        <Footer />
      </div>
      </AccessGate>
    </Router>
  );
}
