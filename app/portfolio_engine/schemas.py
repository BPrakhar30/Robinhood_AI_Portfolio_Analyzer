from pydantic import BaseModel


# ── Health Score ────────────────────────────────────────────────────

class SubScoreDetail(BaseModel):
    score: float
    label: str
    description: str
    details: dict | None = None


class HealthScoreResponse(BaseModel):
    overall_score: float
    grade: str
    sub_scores: dict[str, SubScoreDetail]
    top_issues: list[str]
    suggestions: list[str]


# ── Risk Alerts ─────────────────────────────────────────────────────

class RiskAlert(BaseModel):
    id: str
    severity: str
    category: str
    title: str
    description: str
    metric: str
    threshold: str


class AlertSummary(BaseModel):
    high: int
    medium: int
    low: int


class RiskAlertsResponse(BaseModel):
    alerts: list[RiskAlert]
    summary: AlertSummary
