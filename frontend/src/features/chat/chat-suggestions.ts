import type { ChatMessage } from "./types";

const INITIAL_PROMPTS = [
  "Which 5 stocks have the best growth potential for the next 2-5 years?",
  "What are the biggest risks in my portfolio right now?",
  "Compare my top 3 holdings - which is the strongest buy?",
  "Screen for undervalued dividend stocks in healthcare.",
  "Show me the best and worst performing stocks this year.",
  "Which stock is hurting my returns most?",
  "Find me high-momentum stocks with reasonable valuations.",
  "Compare my portfolio vs S&P 500 and Nasdaq.",
  "Which sectors are leading the market right now?",
  "Explain my portfolio performance in simple language.",
];

export function getInitialAssistantSuggestions(count = 4): string[] {
  const start = new Date().getDate() % INITIAL_PROMPTS.length;
  return Array.from({ length: count }, (_, i) => INITIAL_PROMPTS[(start + i) % INITIAL_PROMPTS.length]);
}

// ── Follow-up suggestion pools ──────────────────────────────────────

function stockPool(symbol: string): string[] {
  return [
    `Is ${symbol} a buy, hold, or sell based on current fundamentals?`,
    `What would make ${symbol}'s technical setup improve or break down?`,
    `Compare ${symbol} against its top 3 competitors.`,
    `What should I watch next for ${symbol}?`,
    `Is ${symbol} overvalued or undervalued based on key stats?`,
    `How does ${symbol}'s performance compare to its sector peers?`,
    `What upcoming events could move ${symbol}'s price?`,
    `Should I increase, hold, or trim my ${symbol} position?`,
  ];
}

const MACRO_POOL = [
  "Which holdings are most exposed if rates keep rising?",
  "What would be the clearest macro warning sign for my portfolio?",
  "Turn this macro summary into 3 portfolio actions.",
  "Which macro signal matters most for my holdings right now?",
  "How would a VIX spike above 25 affect my positions?",
  "Which sectors in my portfolio benefit from current macro conditions?",
];

const MARKETS_POOL = [
  "Which portfolio news articles signal risk for my holdings?",
  "Which owned stocks look strongest based on today's market data?",
  "Are there any earnings surprises that affect my positions?",
  "Summarize the top 3 market stories and how they affect me.",
  "Screen for stocks that could replace my weakest holding.",
  "Which sectors are outperforming and do I have exposure?",
];

const RESEARCH_POOL = [
  "Screen for growth stocks with P/E under 25 and strong momentum.",
  "Find the top 5 dividend stocks for passive income.",
  "Which S&P 500 stocks have the best risk-adjusted returns?",
  "Compare the tech giants - AAPL, MSFT, GOOGL, AMZN, META.",
  "Find undervalued stocks in the energy sector.",
  "Which stocks have beaten earnings estimates 4 quarters in a row?",
  "Screen for defensive stocks with low beta and steady dividends.",
  "What are the best stocks for a 5-year buy-and-hold strategy?",
];

const RISK_POOL = [
  "Which risk should I prioritize first?",
  "What would make my portfolio more balanced?",
  "How concentrated is my portfolio by sector?",
  "Which single holding could cause the largest loss?",
  "What is my portfolio's biggest blind spot right now?",
  "How would a 10% market correction affect my holdings?",
];

const PERFORMANCE_POOL = [
  "Which holdings helped and hurt performance most?",
  "Compare this with the S&P 500 and Nasdaq.",
  "Break down my returns by sector allocation.",
  "Which holding has the best risk-adjusted return?",
  "What drove my portfolio's best and worst days recently?",
  "Am I beating or lagging a simple index fund?",
];

const GENERAL_POOL = [
  "What should I do next based on this answer?",
  "Show the biggest opportunity and biggest risk in my portfolio.",
  "What is the single most important thing I should know today?",
  "Which holding deserves the most attention right now?",
  "Give me a 3-sentence portfolio health check.",
  "What would a financial advisor tell me about my portfolio today?",
  "Screen for stocks that would diversify my portfolio.",
  "Which stocks should I research further based on this analysis?",
];

function routeBaseSuggestions(pathname: string, count: number): string[] {
  const stockMatch = pathname.match(/^\/markets\/([^/]+)/);
  const symbol = stockMatch?.[1]?.toUpperCase();

  if (symbol) return stockPool(symbol).slice(0, count);
  if (pathname.startsWith("/macro-pulse")) return MACRO_POOL.slice(0, count);
  if (pathname.startsWith("/markets")) return MARKETS_POOL.slice(0, count);
  if (pathname.startsWith("/dashboard")) return RESEARCH_POOL.slice(0, count);
  if (pathname.startsWith("/summary")) return PERFORMANCE_POOL.slice(0, count);
  if (pathname.startsWith("/brokers")) {
    return [
      "What portfolio data can you analyze after I connect my broker?",
      "What should I check after syncing my holdings?",
    ].slice(0, count);
  }

  return getInitialAssistantSuggestions(count);
}

function pickUnused(pool: string[], used: Set<string>, count: number): string[] {
  const available = pool.filter((s) => !used.has(s.toLowerCase()));
  if (available.length >= count) return available.slice(0, count);
  const lastTwo = [...used].slice(-2);
  const fallback = pool.filter((s) => !lastTwo.includes(s.toLowerCase()));
  return fallback.length >= count ? fallback.slice(0, count) : pool.slice(0, count);
}

export function getChatSuggestions(
  pathname: string,
  messages: ChatMessage[],
  count = 2,
): string[] {
  if (messages.length === 0) {
    return routeBaseSuggestions(pathname, count);
  }

  const usedMessages = new Set(
    messages.filter((m) => m.role === "user").map((m) => m.content.trim().toLowerCase()),
  );

  const combined = messages
    .slice(-4)
    .map((m) => m.content)
    .join(" ")
    .toLowerCase();

  const stockMatch = pathname.match(/^\/markets\/([^/]+)/);
  const symbol = stockMatch?.[1]?.toUpperCase();

  let pool: string[];

  if (symbol) {
    pool = stockPool(symbol);
  } else if (pathname.startsWith("/macro-pulse") || combined.includes("macro") || combined.includes("yield") || combined.includes("vix")) {
    pool = MACRO_POOL;
  } else if (combined.includes("screen") || combined.includes("find") || combined.includes("top") || combined.includes("best stocks") || combined.includes("compare")) {
    pool = RESEARCH_POOL;
  } else if (pathname.startsWith("/markets") || combined.includes("news") || combined.includes("earnings")) {
    pool = MARKETS_POOL;
  } else if (combined.includes("risk") || combined.includes("concentration") || combined.includes("divers") || combined.includes("balanced")) {
    pool = RISK_POOL;
  } else if (combined.includes("return") || combined.includes("performance") || combined.includes("lag") || combined.includes("beat")) {
    pool = PERFORMANCE_POOL;
  } else {
    pool = GENERAL_POOL;
  }

  const turnCount = messages.filter((m) => m.role === "user").length;
  const rotated = [...pool.slice(turnCount % pool.length), ...pool.slice(0, turnCount % pool.length)];

  return pickUnused(rotated, usedMessages, count);
}

// ── Generation stages ───────────────────────────────────────────────

export function getGenerationStages(question: string): string[] {
  const q = question.toLowerCase();
  const stages = ["Thinking through your question"];

  if (
    q.includes("portfolio") ||
    q.includes("holding") ||
    q.includes("return") ||
    q.includes("risk") ||
    q.includes("divers")
  ) {
    stages.push("Reviewing your portfolio");
  }

  if (
    q.includes("screen") ||
    q.includes("find") ||
    q.includes("top") ||
    q.includes("best") ||
    q.includes("compare") ||
    q.includes("undervalued")
  ) {
    stages.push("Running deep market research");
  }

  if (
    q.includes("stock") ||
    q.includes("ticker") ||
    q.includes("price") ||
    q.includes("chart") ||
    /\b[A-Z]{2,5}\b/.test(question)
  ) {
    stages.push("Checking stock and market data");
  }

  if (
    q.includes("news") ||
    q.includes("earnings") ||
    q.includes("macro") ||
    q.includes("rate") ||
    q.includes("oil") ||
    q.includes("vix")
  ) {
    stages.push("Doing market research");
  }

  if (
    q.includes("sector") ||
    q.includes("industry") ||
    q.includes("etf")
  ) {
    stages.push("Analyzing sector performance");
  }

  stages.push("Writing a clear answer");
  return Array.from(new Set(stages));
}
