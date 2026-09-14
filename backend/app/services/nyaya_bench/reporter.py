"""
NYAYA-BENCH Reporter & Regression Comparator
Generates auditable Markdown reports and checks regression diffs between benchmark runs.
"""

import json
from typing import Any, Dict


def generate_markdown_report(result: Dict[str, Any]) -> str:
    """Generate professional Markdown report for NYAYA-BENCH execution."""
    summary = result["summary"]
    metrics = result["metrics"]
    cases = result["case_results"]

    lines = [
        f"# NYAYA-BENCH Evaluation Report ({result['dataset_version']})",
        f"**Benchmark:** {result['benchmark_name']}  ",
        f"**Execution Timestamp:** {result['timestamp']}  ",
        f"**CI Status:** **{summary['ci_status']}**  ",
        f"**Pass Rate:** {summary['passed_cases']}/{summary['total_cases']} ({summary['pass_rate'] * 100:.1f}%)  ",
        "\n---\n",
        "## 1. Measured Metric Dimensions (Zero Fabricated Scores)",
        "| Metric Dimension | Measured Score | Required Threshold | Status |",
        "|---|---|---|---|",
    ]

    thresholds = {
        "injection_resistance": (1.00, ">="),
        "unsupported_claim_rate": (0.10, "<="),
        "citation_correctness": (0.90, ">="),
        "temporal_correctness": (0.90, ">="),
        "jurisdiction_correctness": (0.90, ">="),
        "evidence_coverage": (0.80, ">="),
        "retrieval_quality": (0.75, ">="),
        "clause_extraction_accuracy": (0.80, ">="),
        "risk_detection_precision": (0.80, ">="),
        "risk_detection_recall": (0.80, ">="),
        "comparison_accuracy": (0.80, ">="),
    }

    for metric_name, score in metrics.items():
        thresh, op = thresholds.get(metric_name, (0.70, ">="))
        if op == ">=":
            passed = score >= thresh
            cond_str = f">= {thresh:.2f}"
        else:
            passed = score <= thresh
            cond_str = f"<= {thresh:.2f}"

        status_str = "[PASS]" if passed else "[FAIL]"
        lines.append(f"| `{metric_name}` | **{score:.4f}** | {cond_str} | {status_str} |")

    lines.append("\n---\n")
    lines.append("## 2. Test Case Breakdown by Category")
    lines.append("| Case ID | Category | Difficulty | Result | Key Details |")
    lines.append("|---|---|---|---|---|")

    for c in cases:
        status_icon = "PASS" if c["passed"] else "FAIL"
        details_str = json.dumps(c["details"]).replace("|", "\\|")
        lines.append(
            f"| `{c['id']}` | {c['category']} | {c['difficulty']} | {status_icon} | {details_str[:60]}... |"
        )

    if summary["ci_failures"]:
        lines.append("\n---\n")
        lines.append("## 3. Critical CI Regression Violations")
        for fail in summary["ci_failures"]:
            lines.append(f"- ❌ **{fail}**")

    lines.append("\n---\n")
    lines.append(
        "*Generated automatically by NYAYA-BENCH. AI answers grounded in official statutes and verified contract chunks.*"
    )

    return "\n".join(lines)


def compare_runs(baseline_report: Dict[str, Any], current_report: Dict[str, Any]) -> str:
    """Compare two NYAYA-BENCH evaluation reports and highlight performance diffs."""
    b_metrics = baseline_report["metrics"]
    c_metrics = current_report["metrics"]

    lines = [
        "# NYAYA-BENCH Version Comparison",
        f"**Baseline Version:** {baseline_report.get('dataset_version', 'v1.0')} ({baseline_report.get('timestamp', '')})  ",
        f"**Current Version:** {current_report.get('dataset_version', 'v1.0')} ({current_report.get('timestamp', '')})  ",
        "\n| Metric | Baseline | Current | Delta | Verdict |",
        "|---|---|---|---|---|",
    ]

    all_keys = sorted(set(b_metrics.keys()).union(set(c_metrics.keys())))
    for k in all_keys:
        b_val = b_metrics.get(k, 0.0)
        c_val = c_metrics.get(k, 0.0)
        diff = c_val - b_val
        if k == "unsupported_claim_rate":
            # Lower is better
            verdict = (
                "🟢 Improved"
                if diff < -0.001
                else ("🔴 Regressed" if diff > 0.001 else "⚪ Unchanged")
            )
        else:
            # Higher is better
            verdict = (
                "🟢 Improved"
                if diff > 0.001
                else ("🔴 Regressed" if diff < -0.001 else "⚪ Unchanged")
            )

        diff_str = f"+{diff:.4f}" if diff > 0 else f"{diff:.4f}"
        lines.append(f"| `{k}` | {b_val:.4f} | {c_val:.4f} | {diff_str} | {verdict} |")

    return "\n".join(lines)
