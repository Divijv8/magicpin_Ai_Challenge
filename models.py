"""
models.py - Pydantic and dataclass models for the Vera Merchant AI Assistant
"""

from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime


class VoiceProfile(BaseModel):
    tone: Optional[str] = None
    register: Optional[str] = None
    code_mix: Optional[str] = None
    vocab_allowed: List[str] = Field(default_factory=list)
    vocab_taboo: List[str] = Field(default_factory=list)
    salutation_examples: List[str] = Field(default_factory=list)
    tone_examples: List[str] = Field(default_factory=list)


class OfferTemplate(BaseModel):
    id: Optional[str] = None
    title: str
    value: Optional[str] = None
    audience: Optional[str] = None
    type: Optional[str] = None


class PeerStats(BaseModel):
    scope: Optional[str] = None
    avg_rating: Optional[float] = None
    avg_review_count: Optional[int] = None
    avg_views_30d: Optional[int] = None
    avg_calls_30d: Optional[int] = None
    avg_directions_30d: Optional[int] = None
    avg_ctr: Optional[float] = None
    avg_photos: Optional[int] = None
    avg_post_freq_days: Optional[int] = None
    retention_6mo_pct: Optional[float] = None


class DigestItem(BaseModel):
    id: Optional[str] = None
    kind: Optional[str] = None
    title: str
    source: Optional[str] = None
    trial_n: Optional[int] = None
    patient_segment: Optional[str] = None
    summary: Optional[str] = None
    actionable: Optional[str] = None
    date: Optional[str] = None
    credits: Optional[int] = None


class CategoryContext(BaseModel):
    slug: str
    display_name: Optional[str] = None
    voice: VoiceProfile = Field(default_factory=VoiceProfile)
    offer_catalog: List[OfferTemplate] = Field(default_factory=list)
    peer_stats: Optional[PeerStats] = None
    digest: List[DigestItem] = Field(default_factory=list)
    patient_content_library: List[Dict[str, Any]] = Field(default_factory=list)
    seasonal_beats: List[Dict[str, Any]] = Field(default_factory=list)
    trend_signals: List[Dict[str, Any]] = Field(default_factory=list)


class MerchantIdentity(BaseModel):
    name: str
    city: Optional[str] = None
    locality: Optional[str] = None
    place_id: Optional[str] = None
    verified: Optional[bool] = True
    languages: List[str] = Field(default_factory=lambda: ["en", "hi"])
    owner_first_name: Optional[str] = None
    established_year: Optional[int] = None


class Subscription(BaseModel):
    status: Optional[str] = "active"
    plan: Optional[str] = "Pro"
    days_remaining: Optional[int] = 30
    renewed_at: Optional[str] = None


class PerformanceSnapshot(BaseModel):
    window_days: Optional[int] = 30
    views: Optional[int] = None
    calls: Optional[int] = None
    directions: Optional[int] = None
    ctr: Optional[float] = None
    leads: Optional[int] = None
    delta_7d: Optional[Dict[str, float]] = Field(default_factory=dict)


class MerchantOffer(BaseModel):
    id: Optional[str] = None
    title: str
    status: Optional[str] = "active"
    started: Optional[str] = None
    ended: Optional[str] = None


class ConversationTurn(BaseModel):
    ts: Optional[str] = None
    from_: Optional[str] = Field(None, alias="from")
    body: Optional[str] = None
    engagement: Optional[str] = None


class CustomerAggregate(BaseModel):
    total_unique_ytd: Optional[int] = None
    lapsed_180d_plus: Optional[int] = None
    retention_6mo_pct: Optional[float] = None
    high_risk_adult_count: Optional[int] = None


class ReviewTheme(BaseModel):
    theme: Optional[str] = None
    sentiment: Optional[str] = None
    occurrences_30d: Optional[int] = None
    common_quote: Optional[str] = None


class MerchantContext(BaseModel):
    merchant_id: str
    category_slug: Optional[str] = None
    identity: MerchantIdentity
    subscription: Optional[Subscription] = Field(default_factory=Subscription)
    performance: Optional[PerformanceSnapshot] = Field(default_factory=PerformanceSnapshot)
    offers: List[MerchantOffer] = Field(default_factory=list)
    conversation_history: List[Dict[str, Any]] = Field(default_factory=list)
    customer_aggregate: Optional[CustomerAggregate] = Field(default_factory=CustomerAggregate)
    signals: List[str] = Field(default_factory=list)
    review_themes: List[ReviewTheme] = Field(default_factory=list)


class CustomerIdentity(BaseModel):
    name: str
    phone_redacted: Optional[str] = None
    language_pref: Optional[str] = "hi-en mix"


class CustomerRelationship(BaseModel):
    first_visit: Optional[str] = None
    last_visit: Optional[str] = None
    visits_total: Optional[int] = None
    services_received: List[str] = Field(default_factory=list)
    lifetime_spend: Optional[int] = None


class CustomerContext(BaseModel):
    customer_id: str
    merchant_id: str
    identity: CustomerIdentity
    relationship: Optional[CustomerRelationship] = Field(default_factory=CustomerRelationship)
    state: Optional[str] = "active"  # new, active, lapsed_soft, lapsed_hard, churned
    preferences: Optional[Dict[str, Any]] = Field(default_factory=dict)
    consent: Optional[Dict[str, Any]] = Field(default_factory=dict)


class TriggerContext(BaseModel):
    id: str
    scope: Literal["merchant", "customer"] = "merchant"
    kind: str
    source: Optional[Literal["external", "internal"]] = "internal"
    merchant_id: Optional[str] = None
    customer_id: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    urgency: Optional[int] = 2
    suppression_key: Optional[str] = ""
    expires_at: Optional[str] = None


class ComposedMessage(BaseModel):
    body: str
    cta: str = "open_ended"  # binary, open_ended, none, multi_choice
    send_as: Literal["vera", "merchant_on_behalf"] = "vera"
    suppression_key: str = ""
    rationale: str = ""
    template_name: Optional[str] = "vera_generic_v1"
    template_params: Optional[List[str]] = Field(default_factory=list)


# API Schema Models
class HealthzResponse(BaseModel):
    status: str = "ok"
    uptime_seconds: int
    contexts_loaded: Dict[str, int]


class MetadataResponse(BaseModel):
    team_name: str
    team_members: List[str]
    model: str
    approach: str
    contact_email: str
    version: str
    submitted_at: str


class ContextPushRequest(BaseModel):
    scope: Literal["category", "merchant", "customer", "trigger"]
    context_id: str
    version: int
    payload: Dict[str, Any]
    delivered_at: Optional[str] = None


class ContextPushResponse(BaseModel):
    accepted: bool
    ack_id: Optional[str] = None
    stored_at: Optional[str] = None
    reason: Optional[str] = None
    current_version: Optional[int] = None


class TickRequest(BaseModel):
    now: str
    available_triggers: List[str] = Field(default_factory=list)


class TickAction(BaseModel):
    conversation_id: str
    merchant_id: str
    customer_id: Optional[str] = None
    send_as: Literal["vera", "merchant_on_behalf"] = "vera"
    trigger_id: str
    template_name: str = "vera_generic_v1"
    template_params: List[str] = Field(default_factory=list)
    body: str
    cta: str = "open_ended"
    suppression_key: str = ""
    rationale: str = ""


class TickResponse(BaseModel):
    actions: List[TickAction] = Field(default_factory=list)


class ReplyRequest(BaseModel):
    conversation_id: str
    merchant_id: Optional[str] = None
    customer_id: Optional[str] = None
    from_role: str = "merchant"
    message: str
    received_at: Optional[str] = None
    turn_number: int = 1


class ReplyResponse(BaseModel):
    action: Literal["send", "wait", "end"]
    body: Optional[str] = None
    cta: Optional[str] = None
    wait_seconds: Optional[int] = None
    rationale: str
