import Link from "next/link";
import {
  TrendingUp,
  Shield,
  Brain,
  BarChart3,
  ArrowRight,
  Lock,
  RefreshCw,
  FileSpreadsheet,
} from "lucide-react";
import { buttonVariants } from "@/components/ui/button-variants";
import { Card, CardContent } from "@/components/ui/card";

const FEATURES = [
  {
    icon: Shield,
    title: "Secure Account Linking",
    description:
      "Connect your Robinhood account via OAuth, Plaid, or CSV import. Tokens are encrypted at rest — never stored in plaintext.",
  },
  {
    icon: BarChart3,
    title: "Understand Your Holdings",
    description:
      "See your full portfolio at a glance — positions, cost basis, unrealized gains, and allocation breakdown.",
  },
  {
    icon: Brain,
    title: "AI-Powered Insights",
    description:
      "Ask natural-language questions about your portfolio. Detect concentration risk, overlap, and diversification gaps.",
  },
  {
    icon: TrendingUp,
    title: "Scenario Simulation",
    description:
      "Model market scenarios — what happens if Nasdaq drops 15%? What if BTC hits 150k? See projected portfolio impact.",
  },
];

const TRUST_ITEMS = [
  { icon: Lock, label: "Encrypted token storage" },
  { icon: RefreshCw, label: "Automatic fallback data sourcing" },
  { icon: FileSpreadsheet, label: "CSV import if APIs are unavailable" },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-background">
      {/* Navigation */}
      <header className="border-b border-border/40 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
          <Link href="/dashboard" className="flex items-center gap-2 cursor-pointer hover:opacity-80 transition-opacity">
            <div className="h-8 w-8 rounded-lg bg-primary flex items-center justify-center">
              <TrendingUp className="h-4 w-4 text-primary-foreground" />
            </div>
            <span className="font-semibold text-sm">RobinhoodAI Copilot</span>
          </Link>
          <div className="flex items-center gap-2">
            <Link href="/login" className={buttonVariants({ variant: "ghost", size: "sm" })}>
              Log in
            </Link>
            <Link href="/register" className={buttonVariants({ size: "sm" })}>
              Get Started
            </Link>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="py-20 sm:py-32">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 text-center">
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight">
            Your AI Portfolio
            <br />
            <span className="text-muted-foreground">Copilot</span>
          </h1>
          <p className="mt-6 text-lg text-muted-foreground max-w-2xl mx-auto leading-relaxed">
            Securely connect your Robinhood account, understand your portfolio deeply,
            and make smarter investment decisions with AI-driven analytics.
          </p>
          <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-3">
            <Link href="/register" className={buttonVariants({ size: "lg" })}>
              Create account
              <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
            <Link href="/login" className={buttonVariants({ size: "lg", variant: "outline" })}>
              Log in
            </Link>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="py-16 border-t border-border/40">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <div className="text-center mb-12">
            <h2 className="text-2xl sm:text-3xl font-semibold tracking-tight">
              Everything you need to manage your portfolio
            </h2>
            <p className="mt-3 text-muted-foreground">
              From account linking to scenario simulation — built for serious retail investors.
            </p>
          </div>
          <div className="grid gap-6 sm:grid-cols-2">
            {FEATURES.map((feature) => (
              <Card key={feature.title} className="transition-shadow hover:shadow-md">
                <CardContent className="p-6">
                  <div className="rounded-lg bg-muted w-10 h-10 flex items-center justify-center mb-4">
                    <feature.icon className="h-5 w-5 text-muted-foreground" />
                  </div>
                  <h3 className="font-semibold mb-2">{feature.title}</h3>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    {feature.description}
                  </p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Trust */}
      <section className="py-16 border-t border-border/40 bg-muted/30">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 text-center">
          <h2 className="text-2xl font-semibold tracking-tight mb-8">
            Built with security first
          </h2>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-8">
            {TRUST_ITEMS.map((item) => (
              <div key={item.label} className="flex items-center gap-2 text-sm text-muted-foreground">
                <item.icon className="h-4 w-4 text-emerald-600" />
                {item.label}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border/40 py-8">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 text-center text-sm text-muted-foreground">
          &copy; {new Date().getFullYear()} RobinhoodAI Copilot. Not financial advice. Not affiliated with Robinhood Markets, Inc.
        </div>
      </footer>
    </div>
  );
}
