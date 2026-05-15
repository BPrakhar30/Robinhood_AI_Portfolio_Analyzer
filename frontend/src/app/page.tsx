import Link from "next/link";
import {
  TrendingUp,
  Brain,
  BarChart3,
  ArrowRight,
  Shield,
  Activity,
  Newspaper,
  MessageSquare,
  PieChart,
  Zap,
  Globe,
  ChevronRight,
} from "lucide-react";
import { buttonVariants } from "@/components/ui/button-variants";
import { Card, CardContent } from "@/components/ui/card";

const FEATURES = [
  {
    icon: Brain,
    title: "AI Portfolio Assistant",
    description:
      "Ask anything about your portfolio in plain English. Get answers backed by real-time data, not generic advice.",
  },
  {
    icon: Activity,
    title: "Portfolio Health Score",
    description:
      "A single 0-100 score across diversification, concentration, ETF overlap, volatility, and expense efficiency.",
  },
  {
    icon: Newspaper,
    title: "AI-Summarized Market News",
    description:
      "Market headlines and portfolio-specific news, each with an AI-generated summary and sentiment tag.",
  },
  {
    icon: Globe,
    title: "Macro Pulse",
    description:
      "Track GDP, inflation, employment, and Fed policy in one view — with AI commentary on what it means for your holdings.",
  },
  {
    icon: PieChart,
    title: "Deep Allocation Analysis",
    description:
      "Breakdowns by sector, asset class, geography, market cap, and risk level. See exactly where your money sits.",
  },
  {
    icon: Shield,
    title: "Risk Alerts",
    description:
      "Automatic detection of concentration risk, sector overweight, and ETF overlap — with severity-ranked alerts.",
  },
];

const WORKFLOW_STEPS = [
  {
    step: "01",
    title: "Connect your portfolio",
    description: "Link Robinhood, import via CSV, or connect through Plaid. Your data stays encrypted.",
  },
  {
    step: "02",
    title: "Get instant insights",
    description: "Health score, risk alerts, allocation breakdowns, and AI-summarized news — all computed in seconds.",
  },
  {
    step: "03",
    title: "Ask your copilot",
    description: "\"Why is my portfolio down?\" \"Am I too concentrated in tech?\" — the AI assistant answers with your real data.",
  },
];

const STATS = [
  { value: "500+", label: "Stocks tracked" },
  { value: "Real-time", label: "Market quotes" },
  { value: "AI-powered", label: "News summaries" },
  { value: "5", label: "Risk dimensions" },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-background">
      {/* Navigation */}
      <header className="border-b border-border/40 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 sticky top-0 z-50">
        <div className="mx-auto flex h-14 w-full max-w-7xl 2xl:max-w-[88rem] items-center justify-between px-4 sm:px-6 lg:px-10 xl:px-12">
          <Link href="/" className="flex items-center gap-2 cursor-pointer hover:opacity-80 transition-opacity">
            <div className="h-8 w-8 rounded-lg bg-amber-500 flex items-center justify-center">
              <TrendingUp className="h-4 w-4 text-white" />
            </div>
            <span className="font-semibold text-sm">Portfolio Copilot</span>
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
      <section className="py-20 sm:py-28 lg:py-32 2xl:py-36 relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-amber-500/5 via-transparent to-transparent pointer-events-none" />
        <div className="mx-auto w-full max-w-5xl 2xl:max-w-6xl px-4 sm:px-6 lg:px-10 text-center relative">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-amber-500/20 bg-amber-500/5 text-sm text-amber-700 dark:text-amber-400 mb-8">
            <Zap className="h-3.5 w-3.5" />
            Powered by Gemini AI
          </div>
          <h1 className="text-4xl sm:text-5xl lg:text-6xl 2xl:text-7xl font-bold tracking-tight leading-[1.1]">
            Your portfolio,
            <br />
            <span className="text-amber-500">understood by AI</span>
          </h1>
          <p className="mt-6 text-base sm:text-lg 2xl:text-xl text-muted-foreground max-w-2xl 2xl:max-w-3xl mx-auto leading-relaxed">
            Connect your brokerage. Get a health score, risk alerts, AI-summarized news,
            and a copilot that answers questions about your actual holdings — not generic tips.
          </p>
          <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-3">
            <Link href="/register" className={buttonVariants({ size: "lg", className: "bg-amber-500 hover:bg-amber-600 text-white shadow-lg shadow-amber-500/20" })}>
              Start for free
              <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
            <Link href="/login" className={buttonVariants({ size: "lg", variant: "outline" })}>
              Log in
            </Link>
          </div>
        </div>
      </section>

      {/* Stats bar */}
      <section className="border-y border-border/40 bg-muted/30">
        <div className="mx-auto w-full max-w-7xl 2xl:max-w-[88rem] px-4 sm:px-6 lg:px-10 xl:px-12">
          <div className="grid grid-cols-2 lg:grid-cols-4 divide-x divide-border/40">
            {STATS.map((stat) => (
              <div key={stat.label} className="py-8 px-4 text-center">
                <p className="text-2xl sm:text-3xl font-bold text-foreground">{stat.value}</p>
                <p className="text-sm text-muted-foreground mt-1">{stat.label}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="py-20 lg:py-24">
        <div className="mx-auto w-full max-w-7xl 2xl:max-w-[88rem] px-4 sm:px-6 lg:px-10 xl:px-12">
          <div className="text-center mb-14">
            <h2 className="text-2xl sm:text-3xl 2xl:text-4xl font-bold tracking-tight">
              Everything a retail investor needs
            </h2>
            <p className="mt-3 text-muted-foreground max-w-xl mx-auto">
              Portfolio analytics, risk detection, market intelligence, and an AI assistant — in one place.
            </p>
          </div>
          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3 2xl:gap-6">
            {FEATURES.map((feature) => (
              <Card key={feature.title} className="h-full transition-all hover:shadow-md hover:border-amber-500/30">
                <CardContent className="p-6">
                  <div className="rounded-xl bg-amber-500/10 w-11 h-11 flex items-center justify-center mb-4">
                    <feature.icon className="h-5 w-5 text-amber-600 dark:text-amber-400" />
                  </div>
                  <h3 className="font-semibold mb-2 text-base">{feature.title}</h3>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    {feature.description}
                  </p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="py-20 lg:py-24 border-t border-border/40 bg-muted/20">
        <div className="mx-auto w-full max-w-4xl 2xl:max-w-5xl px-4 sm:px-6 lg:px-10">
          <div className="text-center mb-14">
            <h2 className="text-2xl sm:text-3xl 2xl:text-4xl font-bold tracking-tight">
              Up and running in minutes
            </h2>
            <p className="mt-3 text-muted-foreground">
              No complicated setup. No subscription required to get started.
            </p>
          </div>
          <div className="space-y-8">
            {WORKFLOW_STEPS.map((step) => (
              <div key={step.step} className="flex gap-5 items-start">
                <div className="shrink-0 w-12 h-12 rounded-xl bg-amber-500 text-white flex items-center justify-center font-bold text-lg shadow-lg shadow-amber-500/20">
                  {step.step}
                </div>
                <div className="pt-1">
                  <h3 className="font-semibold text-lg">{step.title}</h3>
                  <p className="text-sm text-muted-foreground mt-1 leading-relaxed">{step.description}</p>
                </div>
              </div>
            ))}
          </div>
          <div className="mt-12 text-center">
            <Link href="/register" className={buttonVariants({ size: "lg", className: "bg-amber-500 hover:bg-amber-600 text-white" })}>
              Create your free account
              <ChevronRight className="ml-1 h-4 w-4" />
            </Link>
          </div>
        </div>
      </section>

      {/* AI assistant highlight */}
      <section className="py-20 lg:py-24 border-t border-border/40">
        <div className="mx-auto w-full max-w-7xl 2xl:max-w-[88rem] px-4 sm:px-6 lg:px-10 xl:px-12">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div>
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-amber-500/20 bg-amber-500/5 text-sm text-amber-700 dark:text-amber-400 mb-4">
                <MessageSquare className="h-3.5 w-3.5" />
                AI Assistant
              </div>
              <h2 className="text-2xl sm:text-3xl font-bold tracking-tight mb-4">
                Ask anything about your portfolio
              </h2>
              <p className="text-muted-foreground leading-relaxed mb-6">
                The AI assistant has access to your live holdings, market data, and portfolio analytics
                through secure tool integrations. It doesn&apos;t guess — it queries your real data.
              </p>
              <ul className="space-y-3">
                {[
                  "\"What's my biggest risk right now?\"",
                  "\"How diversified am I across sectors?\"",
                  "\"Summarize the latest news for my holdings\"",
                  "\"What happens if the market drops 20%?\"",
                ].map((q) => (
                  <li key={q} className="flex items-start gap-2.5 text-sm">
                    <ChevronRight className="h-4 w-4 text-amber-500 mt-0.5 shrink-0" />
                    <span className="text-muted-foreground">{q}</span>
                  </li>
                ))}
              </ul>
            </div>
            <div className="relative">
              <Card className="border-amber-500/20 shadow-xl shadow-amber-500/5">
                <CardContent className="p-6 space-y-4">
                  <div className="flex items-center gap-2 mb-2">
                    <div className="h-7 w-7 rounded-lg bg-amber-500/10 flex items-center justify-center">
                      <Brain className="h-4 w-4 text-amber-600" />
                    </div>
                    <span className="text-sm font-medium">Portfolio Copilot</span>
                  </div>
                  <div className="bg-muted rounded-xl p-4">
                    <p className="text-sm text-muted-foreground italic">Am I too concentrated in tech?</p>
                  </div>
                  <div className="bg-amber-500/5 border border-amber-500/10 rounded-xl p-4 space-y-2">
                    <p className="text-sm leading-relaxed">
                      Your tech exposure is <strong>42.3%</strong> across 8 positions — well above the S&P 500&apos;s ~31% weight.
                      AAPL alone is 14.8% of your portfolio.
                    </p>
                    <p className="text-sm leading-relaxed">
                      Your health score&apos;s <strong>concentration sub-score is 52/100</strong>, flagged as elevated.
                      Consider diversifying into underweight sectors like Healthcare (2.1%) or Energy (0%).
                    </p>
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        </div>
      </section>

      {/* Security + trust */}
      <section className="py-16 lg:py-20 border-t border-border/40 bg-muted/30">
        <div className="mx-auto w-full max-w-7xl 2xl:max-w-[88rem] px-4 sm:px-6 lg:px-10 xl:px-12 text-center">
          <h2 className="text-xl sm:text-2xl font-semibold tracking-tight mb-8">
            Your data, locked down
          </h2>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-8 lg:gap-14">
            {[
              { icon: Shield, label: "Encrypted at rest and in transit" },
              { icon: BarChart3, label: "Read-only brokerage access" },
              { icon: Activity, label: "No trading, ever" },
            ].map((item) => (
              <div key={item.label} className="flex items-center gap-2.5 text-sm text-muted-foreground">
                <item.icon className="h-4 w-4 text-emerald-600" />
                {item.label}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <section className="py-20 lg:py-24 border-t border-border/40">
        <div className="mx-auto w-full max-w-3xl px-4 sm:px-6 text-center">
          <h2 className="text-2xl sm:text-3xl font-bold tracking-tight mb-4">
            Stop guessing. Start understanding.
          </h2>
          <p className="text-muted-foreground mb-8 max-w-xl mx-auto">
            Join investors who use AI to understand their portfolio — not replace their judgment.
          </p>
          <Link href="/register" className={buttonVariants({ size: "lg", className: "bg-amber-500 hover:bg-amber-600 text-white shadow-lg shadow-amber-500/20" })}>
            Get started for free
            <ArrowRight className="ml-2 h-4 w-4" />
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border/40 py-8">
        <div className="mx-auto w-full max-w-7xl 2xl:max-w-[88rem] px-4 sm:px-6 lg:px-10 xl:px-12 text-center text-sm text-muted-foreground">
          &copy; {new Date().getFullYear()} Portfolio Copilot. Not financial advice. Not affiliated with Robinhood Markets, Inc.
        </div>
      </footer>
    </div>
  );
}
