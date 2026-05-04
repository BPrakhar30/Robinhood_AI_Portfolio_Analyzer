import Link from "next/link";

export default function NotFound() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="text-center space-y-4">
        <h1 className="text-6xl font-bold text-muted-foreground">404</h1>
        <h2 className="text-xl font-semibold text-foreground">Page not found</h2>
        <p className="text-muted-foreground max-w-md">
          The page you are looking for does not exist or has been moved.
        </p>
        <Link
          href="/dashboard"
          className="inline-block mt-4 px-6 py-2 rounded-md bg-amber-600 text-white font-medium hover:bg-amber-700 transition-colors"
        >
          Back to Dashboard
        </Link>
      </div>
    </div>
  );
}
