import pytest


@pytest.mark.asyncio
async def test_document_comparison_and_risk_delta(client, auth_headers):
    # Load standard lease
    base_res = await client.post(
        "/api/v1/documents/load-sample",
        data={"sample_key": "standard_residential_lease_delhi"},
        headers=auth_headers
    )
    assert base_res.status_code == 201
    base_id = base_res.json()["id"]

    # Load harsh lease
    target_res = await client.post(
        "/api/v1/documents/load-sample",
        data={"sample_key": "harsh_landlord_lease_delhi"},
        headers=auth_headers
    )
    assert target_res.status_code == 201
    target_id = target_res.json()["id"]

    # Compare them
    comp_res = await client.post(
        "/api/v1/comparison/",
        json={"base_document_id": base_id, "target_document_id": target_id},
        headers=auth_headers
    )
    assert comp_res.status_code == 200
    data = comp_res.json()

    assert data["base_document_id"] == base_id
    assert data["target_document_id"] == target_id
    assert data["summary"]["net_risk_verdict"] == "TARGET_MORE_HARSH"
    assert data["summary"]["target_high_risks"] >= 2
    assert isinstance(data["findings"], list)
    assert len(data["findings"]) >= 1

    # Validate finding schema
    f = data["findings"][0]
    assert "finding_id" in f
    assert f["category"] in {"IDENTICAL", "SIMILAR", "MODIFIED", "NEW", "REMOVED", "CONFLICTING", "MISSING"}
    assert "dimension" in f
    assert "materiality" in f
    assert "difference_explanation" in f
    assert 0.0 <= f["confidence"] <= 1.0

    # Structural diff fields
    assert "structural_diff" in data
    sd = data["structural_diff"]
    assert sd["doc_a_clause_count"] >= 1
    assert sd["doc_b_clause_count"] >= 1
    assert 0.0 <= sd["structural_alignment_score"] <= 1.0

    # Dimensions analyzed
    assert "dimensions_analyzed" in data
    assert len(data["dimensions_analyzed"]) >= 1

    # At least one non-identical finding
    cats = {f["category"] for f in data["findings"]}
    assert cats & {"MODIFIED", "CONFLICTING", "NEW", "REMOVED", "MISSING"}
