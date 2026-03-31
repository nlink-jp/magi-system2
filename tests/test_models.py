"""Tests for data models."""

from magi_system2.models import (
    AttachmentDigest,
    ConvergenceSnapshot,
    DiscussionState,
    FacilitatorAction,
    InnerThoughts,
    Message,
    PersonaDesign,
    PersonaResponse,
    PersonalityProfile,
    TokenUsage,
    TopicAnalysis,
)


def _make_personality() -> PersonalityProfile:
    return PersonalityProfile(
        communication_style="formal and precise",
        debate_approach="builds arguments with evidence",
        intellectual_tendencies="seeks first principles",
        risk_tolerance="moderate",
        decision_framework="cost-benefit analysis",
        cognitive_biases=["confirmation bias"],
        emotional_baseline="calm and measured",
        triggers=["dismissal of data"],
        persuasion_sensitivity="empirical evidence",
        conflict_style="diplomatic",
        concession_pattern="concedes on details not principles",
        listening_quality="references others' points",
    )


def _make_persona() -> PersonaDesign:
    return PersonaDesign(
        name="Dr. Test",
        archetype="Analyst",
        background="A test persona.",
        expertise=["testing"],
        perspective="analytical",
        core_values=["accuracy"],
        blind_spots=["creativity"],
        initial_stance="Data first.",
        personality=_make_personality(),
        temperature=0.5,
    )


def test_personality_profile():
    p = _make_personality()
    assert p.communication_style == "formal and precise"
    assert len(p.cognitive_biases) == 1


def test_persona_design():
    p = _make_persona()
    assert p.name == "Dr. Test"
    assert p.temperature == 0.5
    assert p.personality.conflict_style == "diplomatic"


def test_topic_analysis():
    a = TopicAnalysis(
        summary="Test topic",
        key_dimensions=["cost", "safety"],
        personas=[_make_persona(), _make_persona(), _make_persona()],
        discussion_strategy="explore then converge",
        expected_tensions=["cost vs safety"],
    )
    assert len(a.personas) == 3
    assert len(a.key_dimensions) == 2


def test_inner_thoughts():
    t = InnerThoughts(
        honest_reaction="I disagree but won't say it",
        doubts=["my cost estimate might be wrong"],
        strategic_thinking="concede on timing to win on scope",
        emotional_state="frustrated but composed",
        suppressed_opinions=["their plan is unrealistic"],
        assessment_of_others={"Prof. Kim": "insightful but impractical"},
        willingness_to_move="moderate on implementation, firm on principles",
    )
    assert len(t.doubts) == 1
    assert "Prof. Kim" in t.assessment_of_others


def test_persona_response():
    r = PersonaResponse(
        inner_thoughts=InnerThoughts(
            honest_reaction="interesting point",
            doubts=[],
            strategic_thinking="build on this",
            emotional_state="engaged",
            suppressed_opinions=[],
            assessment_of_others={},
            willingness_to_move="open",
        ),
        statement="I agree with the general direction.",
        key_points=["alignment on goals"],
        addressed_to="Prof. Kim",
        stance_evolution="shifted toward compromise",
        readiness_to_converge=0.6,
        convergence_conditions="need specifics on timeline",
    )
    assert r.readiness_to_converge == 0.6
    assert r.inner_thoughts.emotional_state == "engaged"


def test_token_usage():
    t = TokenUsage()
    t.add_pro(1000, 200)
    t.add_flash(500, 100)
    assert t.pro_total == 1200
    assert t.flash_total == 600
    assert t.total == 1800


def test_convergence_snapshot():
    s = ConvergenceSnapshot(
        turn=10,
        facilitator_assessment=0.75,
        persona_readiness={"A": 0.8, "B": 0.7, "C": 0.6},
        average_readiness=0.7,
        is_converged=False,
    )
    assert not s.is_converged
    assert s.persona_readiness["A"] == 0.8


def test_discussion_state():
    s = DiscussionState(
        topic_analysis=TopicAnalysis(
            summary="test",
            key_dimensions=["x"],
            personas=[_make_persona(), _make_persona(), _make_persona()],
            discussion_strategy="test",
            expected_tensions=["x vs y"],
        ),
    )
    assert s.turn == 0
    assert not s.is_converged
    assert s.phase == "initialization"
    assert s.token_usage.total == 0


def test_discussion_state_json_roundtrip():
    """State should survive JSON serialization for export/re-render."""
    s = DiscussionState(
        topic_analysis=TopicAnalysis(
            summary="test",
            key_dimensions=["x"],
            personas=[_make_persona(), _make_persona(), _make_persona()],
            discussion_strategy="test",
            expected_tensions=[],
        ),
    )
    s.messages.append(Message(turn=0, speaker="test", role="persona", content="hello"))
    s.token_usage.add_pro(100, 50)

    json_str = s.model_dump_json()
    restored = DiscussionState.model_validate_json(json_str)
    assert restored.messages[0].content == "hello"
    assert restored.token_usage.pro_total == 150
