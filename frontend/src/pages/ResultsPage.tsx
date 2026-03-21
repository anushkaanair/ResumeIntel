import { useParams, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { useJobStatus } from "../hooks/useJobStatus";
import { LoadingSpinner } from "../components/LoadingSpinner";
import { Card } from "../components/Card";
import { AlignmentGauge } from "../components/AlignmentGauge";
import { ScoreBadge } from "../components/ScoreBadge";
import { SuggestionList } from "../components/SuggestionList";
import { Button } from "../components/Button";

const STATUS_MESSAGES: Record<string, string> = {
  idle: "Waiting...",
  queued: "Queued — waiting for a worker...",
  running: "Running optimization pipeline...",
  completed: "Complete!",
  failed: "Pipeline failed.",
};

/** Results page — displays optimization output. */
export function ResultsPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();
  const { status, result, error } = useJobStatus(jobId ?? null);

  const tailoringScore = result?.tailoring?.quality_score ?? 0;
  const qualityScore = result?.quality?.quality_score ?? 0;
  const suggestions = [
    ...(result?.quality?.suggestions ?? []),
    ...(result?.weak_detection?.suggestions ?? []),
  ];

  return (
    <div className="mx-auto max-w-5xl px-4 py-12">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">Optimization Results</h1>
        <Button variant="ghost" onClick={() => navigate("/optimize")}>
          ← New Optimization
        </Button>
      </div>

      {/* Status indicator */}
      {status !== "completed" && (
        <div className="mt-8 flex flex-col items-center gap-4 py-12">
          {status === "failed" ? (
            <div className="rounded-lg border border-red-200 bg-red-50 px-6 py-4 text-center">
              <p className="text-red-700 font-medium">Pipeline failed</p>
              <p className="mt-1 text-sm text-red-500">{error || "An unexpected error occurred."}</p>
            </div>
          ) : (
            <LoadingSpinner size={48} message={STATUS_MESSAGES[status]} />
          )}
        </div>
      )}

      {/* Results */}
      {status === "completed" && result && (
        <motion.div
          className="mt-8 space-y-6"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
        >
          {/* Score overview */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <AlignmentGauge score={tailoringScore} label="JD Alignment" />
            <AlignmentGauge score={qualityScore} label="Quality Score" />
            <div className="flex flex-col items-center justify-center gap-2 rounded-xl bg-blue-50 p-6">
              <span className="text-4xl font-bold text-blue-600">
                {Object.keys(result).length}
              </span>
              <span className="text-sm font-medium text-gray-600">Agents Completed</span>
            </div>
          </div>

          {/* Agent score badges */}
          <Card title="Pipeline Scores">
            <div className="flex flex-wrap gap-2">
              {Object.entries(result).map(([agent, output]) => (
                <ScoreBadge
                  key={agent}
                  label={agent.replace("_", " ")}
                  score={(output as any).quality_score ?? 0}
                />
              ))}
            </div>
          </Card>

          {/* Optimized resume */}
          {result.tailoring?.content && (
            <Card title="Optimized Resume">
              <pre className="whitespace-pre-wrap text-sm text-gray-700 font-sans leading-relaxed">
                {result.tailoring.content}
              </pre>
            </Card>
          )}

          {/* Suggestions */}
          {suggestions.length > 0 && (
            <Card title="Improvement Suggestions">
              <SuggestionList suggestions={suggestions} />
            </Card>
          )}

          {/* Interview prep */}
          {result.interview?.content && (
            <Card title="Interview Preparation">
              <pre className="whitespace-pre-wrap text-sm text-gray-700 font-sans leading-relaxed">
                {result.interview.content}
              </pre>
            </Card>
          )}
        </motion.div>
      )}
    </div>
  );
}
