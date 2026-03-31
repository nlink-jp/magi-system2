"""Pydantic data models for magi-system2."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Persona personality model
# ---------------------------------------------------------------------------


class PersonalityProfile(BaseModel):
    """Rich personality model for nuanced discussion behavior."""

    # Identity
    communication_style: str = Field(description="e.g. 'formal and precise', 'passionate and direct'")
    debate_approach: str = Field(description="How they build and present arguments")
    intellectual_tendencies: str = Field(description="e.g. 'seeks first principles', 'draws from case studies'")

    # Cognitive traits
    risk_tolerance: str = Field(description="Attitude toward risk and uncertainty")
    decision_framework: str = Field(description="e.g. 'utilitarian cost-benefit', 'precautionary principle'")
    cognitive_biases: list[str] = Field(description="Self-aware tendencies to watch for")

    # Emotional tendencies
    emotional_baseline: str = Field(description="Default emotional state and composure")
    triggers: list[str] = Field(description="What makes them passionate or frustrated")
    persuasion_sensitivity: str = Field(description="What kind of argument they find compelling")

    # Interpersonal style
    conflict_style: str = Field(description="e.g. 'diplomatic but persistent', 'confrontational'")
    concession_pattern: str = Field(description="How they compromise")
    listening_quality: str = Field(description="How they engage with others' points")


class PersonaDesign(BaseModel):
    """Complete persona specification generated per topic."""

    name: str = Field(description="Display name")
    icon: str = Field(default="👤", description="Single emoji representing this persona, e.g. 🛡️ 🚀 👥")
    archetype: str = Field(description="Short role label")
    background: str = Field(description="Professional/personal background (3-5 sentences)")
    expertise: list[str] = Field(description="Areas of expertise relevant to the topic")
    perspective: str = Field(description="Worldview lens on the topic")
    core_values: list[str] = Field(description="Priority values driving their stance")
    blind_spots: list[str] = Field(description="What they tend to underweight or miss")
    initial_stance: str = Field(description="Opening position on the topic")
    personality: PersonalityProfile
    temperature: float = Field(ge=0.1, le=1.0, description="LLM sampling temperature")


# ---------------------------------------------------------------------------
# Topic analysis
# ---------------------------------------------------------------------------


class AttachmentDigest(BaseModel):
    """Summary of an attached file for persona reference."""

    filename: str
    media_type: str
    summary: str
    key_points: list[str]
    reference_label: str = Field(description="Short citation label, e.g. [Design-PDF]")


class TopicAnalysis(BaseModel):
    """Facilitator's analysis of the input topic and attachments."""

    summary: str
    attachment_digests: list[AttachmentDigest] = Field(default_factory=list)
    key_dimensions: list[str] = Field(description="Axes of disagreement")
    personas: list[PersonaDesign] = Field(min_length=3, max_length=3)
    discussion_strategy: str
    expected_tensions: list[str] = Field(description="Predicted friction points")


# ---------------------------------------------------------------------------
# Dual memory: inner thoughts + public statement
# ---------------------------------------------------------------------------


class InnerThoughts(BaseModel):
    """Private internal monologue — never shared with other personas."""

    honest_reaction: str = Field(description="True reaction to recent arguments")
    doubts: list[str] = Field(description="Own position's weaknesses they recognize")
    strategic_thinking: str = Field(description="Tactical considerations")
    emotional_state: str = Field(description="How they actually feel")
    suppressed_opinions: list[str] = Field(description="Things they think but choose not to say")
    assessment_of_others: dict[str, str] = Field(description="Private evaluation of each persona")
    willingness_to_move: str = Field(description="Real flexibility level")


class PersonaResponse(BaseModel):
    """Complete persona output per turn — inner + public."""

    # Private
    inner_thoughts: InnerThoughts

    # Public
    statement: str = Field(description="The spoken opinion")
    key_points: list[str] = Field(description="Main arguments in this turn")
    addressed_to: str = Field(description="Primarily responding to whom")
    stance_evolution: str = Field(description="How their public position has shifted")

    # Convergence signals
    readiness_to_converge: float = Field(ge=0.0, le=1.0)
    convergence_conditions: str = Field(description="What would need to happen for agreement")


# ---------------------------------------------------------------------------
# Facilitator
# ---------------------------------------------------------------------------


class FacilitatorAction(BaseModel):
    """Facilitator's per-turn decision."""

    next_speaker: str
    instruction: str = Field(description="Guidance for the next speaker")
    intervention: str = Field(default="", description="Optional statement to inject into discussion")
    discussion_status: str = Field(description="Current phase label")

    # Analysis (informed by inner thoughts)
    convergence_assessment: float = Field(ge=0.0, le=1.0)
    hidden_dynamics: str = Field(description="What the facilitator sees beneath the surface")
    strategic_intent: str = Field(description="Why this action")


# ---------------------------------------------------------------------------
# Messages and state
# ---------------------------------------------------------------------------


class Message(BaseModel):
    """A single message in the shared conversation."""

    turn: int
    speaker: str = Field(description="Persona name or 'facilitator'")
    role: Literal["persona", "facilitator"]
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)


class ConvergenceSnapshot(BaseModel):
    """Per-turn convergence state."""

    turn: int
    facilitator_assessment: float
    persona_readiness: dict[str, float]
    average_readiness: float
    is_converged: bool


class TokenUsage(BaseModel):
    """Cumulative token usage tracking."""

    pro_input: int = 0
    pro_output: int = 0
    flash_input: int = 0
    flash_output: int = 0

    @property
    def pro_total(self) -> int:
        return self.pro_input + self.pro_output

    @property
    def flash_total(self) -> int:
        return self.flash_input + self.flash_output

    @property
    def total(self) -> int:
        return self.pro_total + self.flash_total

    def add_pro(self, input_tokens: int, output_tokens: int) -> None:
        self.pro_input += input_tokens
        self.pro_output += output_tokens

    def add_flash(self, input_tokens: int, output_tokens: int) -> None:
        self.flash_input += input_tokens
        self.flash_output += output_tokens


class DiscussionState(BaseModel):
    """Complete discussion state — serializable for export and re-render."""

    topic_analysis: TopicAnalysis
    messages: list[Message] = Field(default_factory=list)
    inner_thoughts: dict[str, list[InnerThoughts]] = Field(default_factory=dict)
    facilitator_actions: list[FacilitatorAction] = Field(default_factory=list)
    convergence_history: list[ConvergenceSnapshot] = Field(default_factory=list)
    token_usage: TokenUsage = Field(default_factory=TokenUsage)
    turn: int = 0
    phase: str = "initialization"
    is_converged: bool = False
    started_at: datetime = Field(default_factory=datetime.now)
    ended_at: datetime | None = None
