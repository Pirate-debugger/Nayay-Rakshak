import pytest


@pytest.mark.asyncio
async def test_harsh_lease_analysis(client, auth_headers):
    # 1. Load harsh lease sample document
    load_res = await client.post(
        "/api/v1/documents/load-sample",
        data={"sample_key": "harsh_landlord_lease_delhi"},
        headers=auth_headers,
    )
    assert load_res.status_code == 201
    doc_id = load_res.json()["id"]

    # 2. Trigger analysis
    an_res = await client.post(f"/api/v1/analysis/{doc_id}", headers=auth_headers)
    assert an_res.status_code == 200
    data = an_res.json()

    # Verify summaries
    assert len(data["summary_citizen"]) > 20
    assert len(data["summary_hindi"]) > 20
    assert "किराया" in data["summary_hindi"] or "अनुबंध" in data["summary_hindi"]

    # Verify clauses extracted
    assert len(data["clauses"]) >= 4

    # Verify harsh risks detected
    risks = data["risks"]
    assert len(risks) >= 2
    risk_titles = [r["title"].lower() for r in risks]
    assert any("penalty" in t or "18%" in t or "interest" in t for t in risk_titles)

    # Verify obligations
    assert len(data["obligations"]) >= 1

    # Verify checklist endpoint
    chk_res = await client.get(f"/api/v1/analysis/{doc_id}/checklist", headers=auth_headers)
    assert chk_res.status_code == 200
    assert len(chk_res.json()["items"]) >= 4
