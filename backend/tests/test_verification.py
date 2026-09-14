import pytest


@pytest.mark.asyncio
async def test_claim_verification_engine_states(client, auth_headers):
    # Load standard lease
    load_res = await client.post(
        "/api/v1/documents/load-sample",
        data={"sample_key": "standard_residential_lease_delhi"},
        headers=auth_headers,
    )
    assert load_res.status_code == 201
    doc_id = load_res.json()["id"]

    claims = [
        # Supported claim
        "The monthly rent payable is Thirty-Five Thousand Indian Rupees.",
        # Conflicting claim
        "The tenant is strictly not allowed to terminate the lease at all.",
        # Unsupported claim
        "The agreement gives the employee company equity stock options vesting over 4 years.",
        # Statutory claim
        "Cheating is defined under Bharatiya Nyaya Sanhita Section 318.",
    ]

    ver_res = await client.post(
        "/api/v1/verification/",
        json={"document_id": doc_id, "claims": claims},
        headers=auth_headers,
    )
    assert ver_res.status_code == 200
    data = ver_res.json()
    assert data["total_claims"] == 4

    results = data["results"]
    statuses = [r["verification_status"] for r in results]

    # Verify presence of states
    assert "SUPPORTED" in statuses
    assert "UNSUPPORTED" in statuses or "UNVERIFIED" in statuses

    for r in results:
        assert "claim_text" in r
        assert "evidence_source" in r
        assert "source_authority" in r
        assert "confidence_strength" in r
        assert 0.0 <= r["confidence_strength"] <= 1.0
