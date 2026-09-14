import pytest


@pytest.mark.asyncio
async def test_legal_aid_resources_and_eligibility(client):
    # Test resource listing
    res = await client.get("/api/v1/legal-aid/resources")
    assert res.status_code == 200
    resources = res.json()
    assert len(resources) >= 5

    # Check NALSA and DSLSA
    org_names = [r["name"] for r in resources]
    assert any("NALSA" in n for n in org_names)

    # Test Section 12 free legal aid eligibility:
    # 1. Woman applicant (statutory entitlement regardless of income)
    elig_res_woman = await client.post(
        "/api/v1/legal-aid/check-eligibility",
        json={
            "annual_income": 1200000.0,
            "state": "Delhi",
            "is_woman_or_child": True
        }
    )
    assert elig_res_woman.status_code == 200
    w_data = elig_res_woman.json()
    assert w_data["is_eligible_for_free_legal_aid"] is True
    assert any("Section 12(c)" in r for r in w_data["eligibility_reasons"])

    # 2. Low income applicant below threshold
    elig_res_income = await client.post(
        "/api/v1/legal-aid/check-eligibility",
        json={
            "annual_income": 180000.0,
            "state": "Delhi",
            "is_woman_or_child": False
        }
    )
    assert elig_res_income.status_code == 200
    inc_data = elig_res_income.json()
    assert inc_data["is_eligible_for_free_legal_aid"] is True
    assert any("annual income" in r.lower() for r in inc_data["eligibility_reasons"])

    # 3. High income non-qualifying applicant
    elig_res_high = await client.post(
        "/api/v1/legal-aid/check-eligibility",
        json={
            "annual_income": 1500000.0,
            "state": "Delhi",
            "is_woman_or_child": False
        }
    )
    assert elig_res_high.status_code == 200
    high_data = elig_res_high.json()
    assert high_data["is_eligible_for_free_legal_aid"] is False

@pytest.mark.asyncio
async def test_glossary_search(client):
    # Test searching for "Indemnity"
    res = await client.get("/api/v1/glossary/?query=Indemnity")
    assert res.status_code == 200
    items = res.json()
    assert len(items) >= 1
    assert items[0]["term"] == "Indemnity"
    assert "हर्जाना" in items[0]["hindi_term"]
