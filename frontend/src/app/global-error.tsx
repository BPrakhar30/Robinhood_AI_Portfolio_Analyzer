"use client";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="en">
      <body className="bg-zinc-950 text-zinc-100">
        <div className="flex min-h-screen items-center justify-center px-4">
          <div className="text-center space-y-4">
            <h1 className="text-6xl font-bold text-zinc-500">500</h1>
            <h2 className="text-xl font-semibold">Something went wrong</h2>
            <p className="text-zinc-400 max-w-md">
              An unexpected error occurred. Please try again.
            </p>
            <button
              onClick={reset}
              className="mt-4 px-6 py-2 rounded-md bg-amber-600 text-white font-medium hover:bg-amber-700 transition-colors"
            >
              Try again
            </button>
          </div>
        </div>
      </body>
    </html>
  );
}
