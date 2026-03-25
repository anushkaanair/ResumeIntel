import { BrowserRouter, Routes, Route } from "react-router-dom";
import { HomePage } from "./pages/HomePage";
import { OptimizePage } from "./pages/OptimizePage";
import { ResultsPage } from "./pages/ResultsPage";
import { CanvasPage } from "./pages/CanvasPage";
import { InterviewPage } from "./pages/InterviewPage";
import { Navbar } from "./components/Navbar";
import { Footer } from "./components/Footer";

/** Root application component with routing. */
export function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen flex flex-col" style={{ background: 'var(--bg, #06060f)' }}>
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
          </Routes>
        </div>
        <Footer />
      </div>
    </BrowserRouter>
  );
}
