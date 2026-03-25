import { useState } from 'react';
import { Card } from './Card';

export interface ResumePreviewProps {
  originalText: string;
  optimizedText: string;
}

export function ResumePreview({ originalText, optimizedText }: ResumePreviewProps) {
  const [view, setView] = useState<'side-by-side' | 'optimized'>('side-by-side');

  return (
    <div className="flex flex-col gap-4 w-full">
      <div className="flex justify-between items-center bg-white p-4 rounded-xl shadow-sm border border-gray-100">
        <h3 className="text-lg font-bold text-gray-900">Resume Comparison</h3>
        <div className="flex bg-gray-100 p-1 rounded-lg">
          <button
            onClick={() => setView('optimized')}
            className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
              view === 'optimized' ? 'bg-white shadow text-blue-600' : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            Optimized Only
          </button>
          <button
            onClick={() => setView('side-by-side')}
            className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
              view === 'side-by-side' ? 'bg-white shadow text-blue-600' : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            Side-by-Side
          </button>
        </div>
      </div>

      <div className={`grid gap-6 items-start ${view === 'side-by-side' ? 'grid-cols-1 md:grid-cols-2' : 'grid-cols-1 max-w-4xl mx-auto'}`}>
        {view === 'side-by-side' && (
          <Card title="Original Document">
            <pre className="whitespace-pre-wrap text-sm text-gray-500 font-sans leading-relaxed opacity-80">
              {originalText || "No original text provided."}
            </pre>
          </Card>
        )}
        <Card title={view === 'side-by-side' ? 'Optimized Version' : ''}>
          <pre className="whitespace-pre-wrap text-sm text-gray-800 font-sans leading-relaxed">
            {optimizedText || "No optimized text available yet."}
          </pre>
        </Card>
      </div>
    </div>
  );
}
