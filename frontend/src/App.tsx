import { BrowserRouter, Routes, Route } from "react-router-dom";
import { HomePage } from "./pages/HomePage";
import { OptimizePage } from "./pages/OptimizePage";
import { ResultsPage } from "./pages/ResultsPage";

/** Root application component with routing. */
export function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-50">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/optimize" element={<OptimizePage />} />
          <Route path="/results/:jobId" element={<ResultsPage />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}
