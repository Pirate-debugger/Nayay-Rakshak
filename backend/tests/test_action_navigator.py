"""
Tests for the Action Navigator endpoint and engine.

Tests verify:
1. Basic plan generation for a standard document
2. Harsh lease triggers escalation
3. Disclaimer is always present
4. No forbidden outcome-guarantee phrases in output
5. Every ActionStep has a non-empty evidence_source
6. CRITICAL risk deterministically triggers escalation
"""

import re
import pytest

# ── Forbidden phrases — must NEVER appear in any step/explanation output ──────

FORBIDDEN_PHRASES = [
    "you will win",
    "you will definitely",
    "guaranteed outcome",
    "definitely legal",
    "this is definitely",
    "will succeed",
    "case will succeed",
    "you are certain",
    "100% guaranteed",
    "legally guaranteed",
    "you cannot lose",
]


def _check_no_forbidden_phrases(text: str) -> None:
    text_lower = text.lower()
    for phrase in FORBIDDEN_PHRASES:
        assert phrase not in text_lower, (
            f"Forbidden outcome-guarantee phrase found: '{phrase}' in:\n{text}"
        )


# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_action_navigator_basic(client, auth_headers):
    """Action Navigator generates a valid plan for a standard document."""
    # Upload a standard lease sample
    doc_res = await client.post(
        "/api/v1/documents/load-sample",
        data={"sample_key": "standard_residential_lease_delhi"},
        headers=auth_headers,
    )
    assert doc_res.status_code == 201
    doc_id = doc_res.json()["id"]

    # Generate action plan
    plan_res = await client.post(
        f"/api/v1/analysis/{doc_id}/action-navigator",
        headers=auth_headers,
    )
    assert plan_res.status_code == 200, plan_res.text
    plan = plan_res.json()

    # Top-level fields
    assert plan["document_id"] == doc_id
    assert plan["document_title"]
    assert plan["engine_version"]

    # All 8 sections present
    assert "known_facts" in plan
    assert "unknown_facts" in plan
    assert "important_documents" in plan
    assert "important_dates" in plan
    assert "potential_issues" in plan
    assert "questions_to_ask" in plan
    assert "possible_next_steps" in plan
    assert "when_to_seek_professional_help" in plan

    # Basic content expectations
    assert len(plan["known_facts"]) >= 1, "Should extract at least one known fact"
    assert len(plan["important_documents"]) >= 1, "Should always list signed copy"
    assert len(plan["possible_next_steps"]) >= 1, "Should produce at least one step"

    # Disclaimer always populated
    assert plan["disclaimer"]
    assert "not" in plan["disclaimer"].lower()  # Must contain a limiting statement


@pytest.mark.asyncio
async def test_action_navigator_harsh_lease_escalates(client, auth_headers):
    """A harsh landlord lease must trigger professional review escalation."""
    doc_res = await client.post(
        "/api/v1/documents/load-sample",
        data={"sample_key": "harsh_landlord_lease_delhi"},
        headers=auth_headers,
    )
    assert doc_res.status_code == 201
    doc_id = doc_res.json()["id"]

    plan_res = await client.post(
        f"/api/v1/analysis/{doc_id}/action-navigator",
        headers=auth_headers,
    )
    assert plan_res.status_code == 200, plan_res.text
    plan = plan_res.json()

    assert plan["professional_review_recommended"] is True, (
        "Harsh landlord lease must trigger professional_review_recommended=True"
    )
    assert len(plan["when_to_seek_professional_help"]) >= 1, (
        "Must have at least one escalation trigger for a harsh lease"
    )
    # Professional review urgency should not be LOW
    assert plan["professional_review_urgency"] != "INFORMATIONAL"


@pytest.mark.asyncio
async def test_action_navigator_disclaimer_always_present(client, auth_headers):
    """The disclaimer must always be non-empty and contain a limiting clause."""
    doc_res = await client.post(
        "/api/v1/documents/load-sample",
        data={"sample_key": "standard_residential_lease_delhi"},
        headers=auth_headers,
    )
    doc_id = doc_res.json()["id"]

    plan_res = await client.post(
        f"/api/v1/analysis/{doc_id}/action-navigator",
        headers=auth_headers,
    )
    assert plan_res.status_code == 200
    plan = plan_res.json()

    disclaimer = plan.get("disclaimer", "")
    assert len(disclaimer) >= 50, "Disclaimer must be substantive, not a token string"
    assert any(
        phrase in disclaimer.lower()
        for phrase in ["not legal advice", "does not", "cannot guarantee", "not constitute"]
    ), f"Disclaimer must contain limiting language. Got: {disclaimer}"


@pytest.mark.asyncio
async def test_action_navigator_no_outcome_claims(client, auth_headers):
    """
    Output text must NEVER contain outcome-guarantee phrases.
    Tests across: steps, explanations, questions, issues.
    """
    doc_res = await client.post(
        "/api/v1/documents/load-sample",
        data={"sample_key": "harsh_landlord_lease_delhi"},
        headers=auth_headers,
    )
    doc_id = doc_res.json()["id"]

    plan_res = await client.post(
        f"/api/v1/analysis/{doc_id}/action-navigator",
        headers=auth_headers,
    )
    assert plan_res.status_code == 200
    plan = plan_res.json()

    # Collect all textual output
    all_text_parts = []
    for step in plan.get("possible_next_steps", []):
        all_text_parts.extend([step.get("action", ""), step.get("reason", "")])
    for issue in plan.get("potential_issues", []):
        all_text_parts.extend([issue.get("explanation", ""), issue.get("potential_impact", "")])
    for q in plan.get("questions_to_ask", []):
        all_text_parts.append(q.get("question", ""))
    for trigger in plan.get("when_to_seek_professional_help", []):
        all_text_parts.append(trigger.get("reason", ""))

    combined = " ".join(all_text_parts)
    _check_no_forbidden_phrases(combined)


@pytest.mark.asyncio
async def test_action_navigator_steps_have_evidence(client, auth_headers):
    """Every ActionStep must have a non-empty evidence_source field."""
    doc_res = await client.post(
        "/api/v1/documents/load-sample",
        data={"sample_key": "standard_residential_lease_delhi"},
        headers=auth_headers,
    )
    doc_id = doc_res.json()["id"]

    plan_res = await client.post(
        f"/api/v1/analysis/{doc_id}/action-navigator",
        headers=auth_headers,
    )
    assert plan_res.status_code == 200
    plan = plan_res.json()

    for i, step in enumerate(plan.get("possible_next_steps", []), 1):
        evidence = step.get("evidence_source", "")
        assert evidence, (
            f"Step {i} ('{step.get('action', '')[:50]}...') "
            "has an empty evidence_source. Every step must be traceable."
        )
        assert len(evidence) >= 3, (
            f"Step {i} evidence_source is too short to be meaningful: '{evidence}'"
        )


@pytest.mark.asyncio
async def test_action_navigator_escalation_schema(client, auth_headers):
    """Escalation triggers have valid schema fields."""
    doc_res = await client.post(
        "/api/v1/documents/load-sample",
        data={"sample_key": "harsh_landlord_lease_delhi"},
        headers=auth_headers,
    )
    doc_id = doc_res.json()["id"]

    plan_res = await client.post(
        f"/api/v1/analysis/{doc_id}/action-navigator",
        headers=auth_headers,
    )
    assert plan_res.status_code == 200
    plan = plan_res.json()

    for trigger in plan.get("when_to_seek_professional_help", []):
        assert trigger["trigger_type"], "Escalation trigger must have a type"
        assert trigger["reason"], "Escalation trigger must have a reason"
        assert trigger["severity"] in ("CRITICAL", "HIGH", "MEDIUM", "LOW"), (
            f"Unexpected severity: {trigger['severity']}"
        )
        assert trigger["recommended_resource"], "Must recommend a specific resource"


@pytest.mark.asyncio
async def test_action_navigator_step_ordering(client, auth_headers):
    """Steps should be numbered sequentially starting from 1."""
    doc_res = await client.post(
        "/api/v1/documents/load-sample",
        data={"sample_key": "standard_residential_lease_delhi"},
        headers=auth_headers,
    )
    doc_id = doc_res.json()["id"]

    plan_res = await client.post(
        f"/api/v1/analysis/{doc_id}/action-navigator",
        headers=auth_headers,
    )
    assert plan_res.status_code == 200
    steps = plan_res.json().get("possible_next_steps", [])

    for i, step in enumerate(steps, 1):
        assert step["step_number"] == i, (
            f"Step at index {i-1} has step_number={step['step_number']}, expected {i}"
        )
