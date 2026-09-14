"""
NYAYA-BENCH CLI Execution Script
Usage:
    python run_nyaya_bench.py [--fail-on-regression]
"""

import asyncio
import os
import sys
import json

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.services.nyaya_bench.runner import NYAYABenchRunner
from app.services.nyaya_bench.reporter import generate_markdown_report


async def main():
    runner = NYAYABenchRunner()
    result = await runner.run()

    # Generate reports
    md_report = generate_markdown_report(result)
    print(md_report)

    output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "reports"))
    os.makedirs(output_dir, exist_ok=True)

    md_path = os.path.join(output_dir, "nyaya_bench_report.md")
    json_path = os.path.join(output_dir, "nyaya_bench_report.json")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_report)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print(f"\n[NYAYA-BENCH] Reports saved to:\n  - {md_path}\n  - {json_path}")

    # Check CI status
    if "--fail-on-regression" in sys.argv and result["summary"]["ci_status"] == "FAIL":
        print("\n[CI GATE] Critical regression thresholds violated! Exiting with status 1.")
        sys.exit(1)

    print("\n[CI GATE] All critical thresholds passed.")
    sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
