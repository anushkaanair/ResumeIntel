import { useParams } from "react-router-dom";

/** Results page — displays optimization output. */
export function ResultsPage() {
  const { jobId } = useParams<{ jobId: string }>();

  return (
    <div className="mx-auto max-w-4xl px-4 py-12">
      <h1 className="text-3xl font-bold text-gray-900">Optimization Results</h1>
      <p className="mt-2 text-gray-600">Job ID: {jobId}</p>
      {/* TODO: Fetch and display results, alignment score, suggestions */}
      <div className="mt-8 rounded-lg border border-gray-200 bg-white p-6">
        <p className="text-gray-500">Results will appear here once the pipeline completes.</p>
      </div>
    </div>
  );
}
