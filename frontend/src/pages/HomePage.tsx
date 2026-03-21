/** Landing page — upload resume and JD to start optimization. */
export function HomePage() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="text-center">
        <h1 className="text-4xl font-bold text-gray-900">Resume Intelligence</h1>
        <p className="mt-4 text-lg text-gray-600">
          AI-powered resume optimization for ATS alignment
        </p>
        <a
          href="/optimize"
          className="mt-8 inline-block rounded-lg bg-blue-600 px-6 py-3 text-white hover:bg-blue-700"
        >
          Get Started
        </a>
      </div>
    </div>
  );
}
