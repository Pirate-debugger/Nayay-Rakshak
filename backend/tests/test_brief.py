import pytest


@pytest.mark.asyncio
async def test_citizen_brief_generation_and_export(client, auth_headers):
    # Load lease
    load_res = await client.post(
        "/api/v1/documents/load-sample",
        data={"sample_key": "harsh_landlord_lease_delhi"},
        headers=auth_headers
    )
    doc_id = load_res.json()["id"]

    # Create brief
    brief_res = await client.post(
        "/api/v1/briefs/",
        json={
            "document_id": doc_id,
            "client_name": "Ananya Iyer",
            "specific_questions": ["Can the landlord forfeit my entire security deposit if I leave at 8 months?"]
        },
        headers=auth_headers
    )
    assert brief_res.status_code == 201
    brief_data = brief_res.json()
    brief_id = brief_data["id"]

    assert "CITIZEN LEGAL CONSULTATION BRIEF" in brief_data["brief_markdown"]
    assert "Ananya Iyer" in brief_data["client_name"]
    assert len(brief_data["questions_for_lawyer"]) >= 4

    # Test export endpoint
    export_res = await client.get(f"/api/v1/briefs/{brief_id}/export", headers=auth_headers)
    assert export_res.status_code == 200
    assert "text/markdown" in export_res.headers["content-type"]
    assert len(export_res.text) > 100
