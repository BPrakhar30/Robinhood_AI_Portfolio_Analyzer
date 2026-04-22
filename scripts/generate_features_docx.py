"""
Generate Portfolio Copilot feature overview as .docx (stdlib only: zip + xml).
Run: python scripts/generate_features_docx.py
Output: docs/Portfolio_Copilot_Features_Retail_Investor.docx
"""
from __future__ import annotations

import zipfile
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "Portfolio_Copilot_Features_Retail_Investor.docx"


def p(text: str) -> str:
    return f'<w:p><w:r><w:t xml:space="preserve">{escape(text)}</w:t></w:r></w:p>'


def heading(text: str, level: int) -> str:
    # Word heading styles: Heading1, Heading2, ...
    style = f"Heading{min(level, 3)}"
    return (
        f'<w:p><w:pPr><w:pStyle w:val="{style}"/></w:pPr>'
        f'<w:r><w:t xml:space="preserve">{escape(text)}</w:t></w:r></w:p>'
    )


def bullet(text: str) -> str:
    return (
        "<w:p>"
        '<w:pPr><w:pStyle w:val="ListParagraph"/>'
        '<w:numPr><w:ilvl w:val="0"/><w:numId w:val="1"/></w:numPr>'
        "</w:pPr>"
        f'<w:r><w:t xml:space="preserve">{escape(text)}</w:t></w:r>'
        "</w:p>"
    )


def build_document_xml(body_paragraphs: list[str]) -> str:
    parts = "\n".join(body_paragraphs)
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
{parts}
    <w:sectPr>
      <w:pgSz w:w="12240" w:h="15840"/>
      <w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"/>
    </w:sectPr>
  </w:body>
</w:document>"""


CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
  <Override PartName="/word/numbering.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml"/>
</Types>"""

RELS_ROOT = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""

DOC_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/numbering" Target="numbering.xml"/>
</Relationships>"""

STYLES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:docDefaults><w:rPrDefault><w:rPr><w:sz w:val="24"/><w:szCs w:val="24"/></w:rPr></w:rPrDefault></w:docDefaults>
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal">
    <w:name w:val="Normal"/><w:qFormat/>
    <w:pPr/><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/><w:sz w:val="22"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading1">
    <w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/><w:uiPriority w:val="9"/>
    <w:pPr><w:keepNext/><w:spacing w:before="240" w:after="120"/></w:pPr>
    <w:rPr><w:b/><w:sz w:val="32"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading2">
    <w:name w:val="heading 2"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/><w:uiPriority w:val="9"/>
    <w:pPr><w:keepNext/><w:spacing w:before="200" w:after="80"/></w:pPr>
    <w:rPr><w:b/><w:sz w:val="26"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading3">
    <w:name w:val="heading 3"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/>
    <w:pPr><w:keepNext/><w:spacing w:before="160" w:after="60"/></w:pPr>
    <w:rPr><w:b/><w:sz w:val="24"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="ListParagraph">
    <w:name w:val="List Paragraph"/><w:basedOn w:val="Normal"/>
    <w:pPr><w:ind w:left="720"/></w:pPr>
  </w:style>
</w:styles>"""

NUMBERING = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:numbering xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:abstractNum w:abstractNumId="0">
    <w:multiLevelType w:val="hybridMultilevel"/>
    <w:lvl w:ilvl="0">
      <w:start w:val="1"/><w:numFmt w:val="bullet"/><w:lvlText w:val="•"/>
      <w:lvlJc w:val="left"/>
      <w:pPr><w:ind w:left="720" w:hanging="360"/></w:pPr>
    </w:lvl>
  </w:abstractNum>
  <w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num>
</w:numbering>"""


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()

    paras: list[str] = []
    paras.append(heading("Portfolio Copilot — Features for Retail Investors", 1))
    paras.append(p(f"Document date: {today}"))
    paras.append(p(
        "This document summarizes product capabilities as implemented today (non-AI), "
        "maps them to the internal PRD (Robinhoodaiapp.md), and outlines how we can "
        "help retail investors make better buy, hold, and sell decisions—especially once "
        "market news and sentiment are integrated alongside the AI assistant."
    ))

    paras.append(heading("1. Product vision (from PRD)", 2))
    paras.append(p(
        "Build a secure portfolio copilot that understands holdings, allocation, and risk, "
        "so users can see concentration, overlap, costs, and volatility—and eventually ask "
        "questions and act with clearer context. Artificial intelligence (natural-language "
        "chat and narrative explanations) is planned but not yet wired to live models."
    ))

    paras.append(heading("2. What is implemented today (no AI backend)", 2))
    paras.append(heading("2.1 Account connection and data", 3))
    for t in (
        "Broker connections: Robinhood-style flow, Plaid, and CSV import (per app configuration).",
        "Positions: symbol, quantity, average cost, current price, market value, weight, gains.",
        "Transactions and account summary where supported by the integration.",
        "User authentication: registration, email verification, login, logout, account deletion.",
        "Password reset: forgot-password email link and secure token-based reset.",
    ):
        paras.append(bullet(t))

    paras.append(heading("2.2 Portfolio analytics UI", 3))
    for t in (
        "Dashboard: portfolio value, position count, unrealized gains, cash, top holdings, broker status.",
        "Dashboard widgets: Portfolio Health Score (summary ring) and Risk Alerts (severity counts) with links to detail pages.",
        "Positions page: holdings list with performance context.",
        "Allocation page: breakdowns by sector, asset class, geography, market cap bucket, and risk level (enriched from market data where available).",
    ):
        paras.append(bullet(t))

    paras.append(heading("2.3 Portfolio Health Score (rule-based)", 3))
    for t in (
        "Single 0–100 score from five weighted components: diversification (sector HHI), concentration (top positions), ETF overlap (static holdings database), volatility proxy (sector and ETF betas), expense efficiency (ETF expense ratios).",
        "Large static coverage of major ETFs (expense ratios, overlap pairs, beta overrides) plus sector/industry beta fallbacks for stocks.",
        "Plain-English descriptions, top issues, and improvement suggestions without an LLM.",
        "Dedicated Health Score page with visual score ring and sub-score cards.",
    ):
        paras.append(bullet(t))

    paras.append(heading("2.4 Allocation Risk Detection (rule-based alerts)", 3))
    for t in (
        "Sector overweight vs approximate S&P 500 sector weights.",
        "Single-stock concentration: elevated flags above configurable-style thresholds (e.g. 10% / 20%).",
        "ETF overlap alerts between held ETFs using pre-built top-holdings overlap.",
        "Centralized Alerts page sorted by severity; empty state when no rules fire.",
    ):
        paras.append(bullet(t))

    paras.append(heading("2.5 AI Assistant (UI only)", 3))
    paras.append(p(
        "The AI Assistant screen provides chat history, search, archive/star, sidebar layout, "
        "and placeholder responses. There is no production LLM or portfolio-aware backend "
        "for chat yet. Implement conversational answers and tool use when the AI stack is added."
    ))

    paras.append(heading("3. How today’s features help buy, hold, or sell", 2))
    paras.append(heading("3.1 Hold (stay diversified, avoid hidden risk)", 3))
    for t in (
        "Health Score and sub-scores surface whether the portfolio is too concentrated, too overlapping, too expensive, or too volatile for the user’s implicit risk posture.",
        "Allocation views show sector and geography skew—useful before adding another similar position.",
        "ETF overlap detection reduces accidental doubling of the same large-cap tech exposure across multiple funds.",
    ):
        paras.append(bullet(t))

    paras.append(heading("3.2 Sell or trim (reduce risk, simplify)", 3))
    for t in (
        "Concentration alerts flag when one stock dominates the portfolio—often a signal to trim or hedge.",
        "Sector overweight alerts suggest when a theme (e.g. technology) dominates versus a broad benchmark.",
        "Overlap alerts suggest consolidating redundant ETFs, which can lower fees and simplify rebalancing.",
    ):
        paras.append(bullet(t))

    paras.append(heading("3.3 Buy (add thoughtfully)", 3))
    for t in (
        "Diversification and expense sub-scores nudge toward broader index funds or lower-cost alternatives when scores are weak.",
        "Understanding current sector and asset-class weights helps choose what to buy next without further skewing the same factor.",
        "Volatility and beta context helps users see whether new purchases would amplify or dampen portfolio swings.",
    ):
        paras.append(bullet(t))

    paras.append(p(
        "Important: The app does not provide personalized investment advice, price targets, or "
        "guarantees. Users should combine these analytics with their own goals, time horizon, "
        "and tax situation, and consult a licensed professional when appropriate."
    ))

    paras.append(heading("4. PRD mapping (Robinhoodaiapp.md)", 2))
    paras.append(heading("4.1 Delivered or partially delivered (non-AI)", 3))
    for t in (
        "Account connection layer — Yes (multiple paths; holdings and performance fields as supported).",
        "Portfolio data model / allocation — Yes (sector, asset class, geography, market cap, risk).",
        "Portfolio Health Score — Yes (rule-based composite and breakdown).",
        "Allocation Risk Detection — Yes (sector overweight, concentration, ETF overlap).",
        "ETF overlap intelligence — Partially (strong static database; not a live holdings API for every ticker).",
        "AI Portfolio Chat Assistant — UI only; backend reasoning not shipped.",
    ):
        paras.append(bullet(t))

    paras.append(heading("4.2 Not yet implemented (from PRD)", 3))
    for t in (
        "Scenario simulator (e.g. Nasdaq −15%).",
        "AI buy/sell insight engine with transparent reasoning (needs AI + guardrails).",
        "Stock deep dive: fundamentals, valuation, analyst sentiment, news summary (needs data vendors + AI summarization).",
        "Automatic portfolio strategy detection.",
        "Smart rebalancing suggestions with targets.",
        "Benchmark comparison engine (returns, volatility, Sharpe vs S&P 500 / Nasdaq).",
        "Tax optimization / tax-loss harvesting assistant.",
        "News-aware monitoring and macro/event alerts.",
        "Portfolio forecast engine and trade impact simulator.",
        "Multi-broker beyond current integrations.",
    ):
        paras.append(bullet(t))

    paras.append(heading("5. Helping retail investors grow: news, sentiment, and timing", 2))
    paras.append(p(
        "Retail investors often react to price alone (e.g. “it’s down 40%—cheap”) or to headlines "
        "without measuring portfolio impact. The following information layers, when added, would "
        "complement the rule-based analytics already shipped."
    ))

    paras.append(heading("5.1 Information we should surface per holding and portfolio", 3))
    for t in (
        "Price context: 52-week range, drawdown from recent high, distance from long-term average (not as a buy signal alone).",
        "Event calendar: earnings dates, ex-dividend dates, and known catalysts for positions above a size threshold.",
        "News feed: top 3–5 recent headlines per holding, tagged by topic (earnings, regulation, litigation, macro).",
        "Sentiment aggregates: optional third-party or model-based sentiment score with clear methodology and timestamp.",
        "Peer and sector context: how the name moves vs sector ETF and vs S&P 500 over 1M / 3M / 1Y.",
        "Portfolio-level “attention” view: which holdings have the worst recent sentiment, highest upcoming event risk, or largest unrealized loss.",
    ):
        paras.append(bullet(t))

    paras.append(heading("5.2 How to frame buy / sell / hold (without reckless prompts)", 3))
    paras.append(p(
        "Regulated, trustworthy products separate “information” from “advice.” The product should "
        "present evidence and scenarios, not directives. Example patterns:"
    ))
    for t in (
        "Hold: “No new risk flags; overlap with QQQ remains moderate; consider monitoring ahead of earnings.”",
        "Trim: “Position exceeds your concentration guideline and overlaps 60% with VOO; reducing X% would align with typical diversification practice.”",
        "Research before buy: “Price is near 52-week low but sentiment is negative and earnings are in 5 days—review recent filings and guidance before sizing.”",
        "Combine rules + narrative: surface the Health Score issue first, then attach news/sentiment as supporting context in the AI chat when implemented.",
    ):
        paras.append(bullet(t))

    paras.append(heading("5.3 “Cheap” vs “falling knife”", 3))
    paras.append(p(
        "A stock at a 52-week or multi-year low is not automatically a buy. A useful copilot "
        "contrasts price action with sentiment trend, revision trends, balance-sheet red flags, "
        "and sector stress. When AI is added, the assistant should cite these factors explicitly "
        "and avoid single-metric cheerleading."
    ))

    paras.append(heading("6. Features to add with the AI chat wave (not in PRD verbatim)", 2))
    for t in (
        "Portfolio-aware news digest: daily or weekly summary of what moved the user’s top holdings, with impact tags (implement alongside AI chat).",
        "Natural-language “why is my portfolio down?” using returns, sector contribution, and headline themes (implement alongside AI chat).",
        "Contrarian / momentum labels as educational overlays only, with disclaimers (implement alongside AI chat).",
        "Simulated “if I buy/sell $X of TICKER” using current allocation and overlap rules before execution (implement alongside AI chat or as deterministic engine).",
    ):
        paras.append(bullet(t))

    paras.append(heading("7. Summary", 2))
    paras.append(p(
        "Today the product delivers strong non-AI foundations: connected portfolio data, rich "
        "allocation views, a composite Health Score, and a rules-based risk alert system—directly "
        "supporting smarter hold, trim, and buy decisions through structure and risk awareness. "
        "Market news, sentiment, and conversational guidance should be layered next, integrated "
        "with the AI Assistant, with clear non-advice framing and data provenance."
    ))

    doc_xml = build_document_xml(paras)

    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CONTENT_TYPES)
        z.writestr("_rels/.rels", RELS_ROOT)
        z.writestr("word/_rels/document.xml.rels", DOC_RELS)
        z.writestr("word/document.xml", doc_xml)
        z.writestr("word/styles.xml", STYLES)
        z.writestr("word/numbering.xml", NUMBERING)

    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
