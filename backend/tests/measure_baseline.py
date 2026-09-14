import asyncio
import os
import sys
import time
import tracemalloc

# Ensure backend path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.ai.mock_provider import DeterministicMockAIProvider
from app.services.document_parser import chunk_document_text
from app.services.pii_sanitizer import sanitize_pii
from app.services.retrieval.retriever import legal_retriever


async def run_benchmarks():
    tracemalloc.start()
    results = {}

    sample_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__), "../../sample_documents/standard_residential_lease_delhi.txt"
        )
    )
    if not os.path.exists(sample_path):
        sample_path = "sample_documents/standard_residential_lease_delhi.txt"

    with open(sample_path, "r", encoding="utf-8") as f:
        sample_text = f.read()

    print(f"[MEASUREMENT] Loaded sample text: {len(sample_text)} characters")

    # 1. PII Sanitization throughput
    t0 = time.perf_counter()
    for _ in range(20):
        sanitized_text, stats = sanitize_pii(sample_text)
    t_pii = (time.perf_counter() - t0) / 20.0
    results["pii_sanitization_ms"] = t_pii * 1000

    # 2. Document Chunking throughput
    t0 = time.perf_counter()
    for _ in range(20):
        chunks = chunk_document_text([(1, sanitized_text)], target_chunk_size=700, overlap=100)
    t_chunk = (time.perf_counter() - t0) / 20.0
    results["chunking_ms"] = t_chunk * 1000
    results["num_chunks"] = len(chunks)

    # 3. Retrieval latency (BM25 + statutory registry)
    t0 = time.perf_counter()
    for q in [
        "What is the lock-in period penalty?",
        "Can landlord enter without notice?",
        "How much security deposit?",
    ]:
        _res = await legal_retriever.retrieve(
            query=q,
            document_chunks=[
                {"content": c["content"], "page_number": c["page_number"]} for c in chunks
            ],
            top_k=5,
        )
    t_retrieval = (time.perf_counter() - t0) / 3.0
    results["retrieval_ms"] = t_retrieval * 1000

    # 4. Mock AI Analysis & QA latency
    ai = DeterministicMockAIProvider()
    t0 = time.perf_counter()
    _analysis = await ai.analyze_document(sanitized_text, "Standard Residential Lease")
    t_analysis = time.perf_counter() - t0
    results["ai_analysis_ms"] = t_analysis * 1000

    t0 = time.perf_counter()
    _qa_ans = await ai.answer_question(
        "What is the rent amount?",
        [{"clean_content": c["clean_content"], "page_number": c["page_number"]} for c in chunks],
    )
    t_qa = time.perf_counter() - t0
    results["ai_qa_ms"] = t_qa * 1000

    # 5. Database & API Measurement using AsyncClient
    from httpx import ASGITransport, AsyncClient

    from app.core.security import create_access_token
    from app.db.base import AsyncSessionLocal, init_db
    from app.db.models import User
    from app.main import app

    await init_db()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create user token
        async with AsyncSessionLocal() as session:
            from sqlalchemy.future import select

            user = (await session.execute(select(User).where(User.id == 1))).scalar_one_or_none()
            if not user:
                user = User(
                    id=1,
                    email="test.perf@example.com",
                    hashed_password="pw",
                    full_name="Perf Tester",
                    role="USER",
                )
                session.add(user)
                await session.commit()
            token = create_access_token({"sub": "1", "email": user.email, "role": user.role})

        headers = {"Authorization": f"Bearer {token}"}

        # Measure Document Upload / Load Sample
        t0 = time.perf_counter()
        doc_resp = await client.post(
            "/api/v1/documents/load-sample",
            data={"sample_key": "standard_residential_lease_delhi"},
            headers=headers,
        )
        t_upload = (time.perf_counter() - t0) * 1000
        results["http_upload_sample_ms"] = t_upload
        doc_id = doc_resp.json().get("id", 1)

        # Measure Document Analysis Endpoint
        t0 = time.perf_counter()
        _analysis_resp = await client.post(f"/api/v1/analysis/{doc_id}", headers=headers)
        t_http_analysis = (time.perf_counter() - t0) * 1000
        results["http_analysis_ms"] = t_http_analysis

        # Measure Q&A Endpoint (Cold Query 1)
        t0 = time.perf_counter()
        _qa_resp1 = await client.post(
            "/api/v1/qa/",
            json={
                "document_id": doc_id,
                "question": "What is the security deposit amount?",
                "language": "en",
            },
            headers=headers,
        )
        t_qa_cold = (time.perf_counter() - t0) * 1000
        results["http_qa_cold_ms"] = t_qa_cold

        # Measure Q&A Endpoint (Identical Query 2 - baseline without response cache)
        t0 = time.perf_counter()
        _qa_resp2 = await client.post(
            "/api/v1/qa/",
            json={
                "document_id": doc_id,
                "question": "What is the security deposit amount?",
                "language": "en",
            },
            headers=headers,
        )
        t_qa_repeated = (time.perf_counter() - t0) * 1000
        results["http_qa_repeated_no_cache_ms"] = t_qa_repeated

    current_mem, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    results["peak_memory_mb"] = peak_mem / (1024 * 1024)

    print("--- BASELINE MEASUREMENT RESULTS ---")
    for k, v in results.items():
        print(f"{k}: {v:.2f}")


if __name__ == "__main__":
    asyncio.run(run_benchmarks())
