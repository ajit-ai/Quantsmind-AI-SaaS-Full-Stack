export default function App() {
  return (
    <div className="min-h-screen bg-white dark:bg-zinc-950 text-zinc-900 dark:text-zinc-100 flex items-center justify-center">
      <div className="max-w-2xl p-8 text-center">
        <h1 className="text-4xl font-bold tracking-tight">Quantsmind AI SaaS</h1>
        <p className="mt-3 text-zinc-600 dark:text-zinc-400">
          Architecture v1 scaffold — React + Vite + Tailwind + shadcn/ui
        </p>
        <div className="mt-6 flex gap-3 justify-center">
          <a href="/api/v1/health" className="px-4 py-2 rounded-lg bg-zinc-900 text-white text-sm">
            API Health
          </a>
          <a href="http://localhost:8000/health" className="px-4 py-2 rounded-lg border text-sm">
            AI Health
          </a>
        </div>
      </div>
    </div>
  );
}
