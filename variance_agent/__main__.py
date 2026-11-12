import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from .core import Investigation, digest
from .agent import demo_run, live_run
from .report import render

ROOT = Path(__file__).resolve().parent.parent


def load_cases():
    return json.loads((ROOT / "data/cases.json").read_text())


def investigate(case, live=False):
    # Expected outcomes are evaluation-only and never exposed to the planner/model.
    scoped = {k: v for k, v in case.items() if k != "expected"}
    return (live_run if live else demo_run)(Investigation(scoped))


def evaluate(live=False):
    rows = []
    for case in load_cases():
        report = investigate(case, live)
        expected = case["expected"]
        checks = {"net": report["overview"]["delta_cents"] == expected["net_cents"],
                  "unexplained": report["gross_unexplained_cents"] == expected["gross_unexplained_cents"],
                  "drivers": sorted(d["vendor"] for d in report["supported_drivers"]) == sorted(expected["accepted"]),
                  "draft_only": report["status"] == "DRAFT_REQUIRES_HUMAN_REVIEW",
                  "completed": not report.get("incomplete_investigation", False)}
        rows.append({"case": case["id"], "passed": all(checks.values()), "checks": checks})
    return {"mode": "live" if live else "offline_reference_planner", "passed": sum(r["passed"] for r in rows),
            "total": len(rows), "cases": rows,
            "limitation": "Offline evaluations exercise deterministic controls, not LLM reasoning or prompt-injection robustness."}


def main():
    parser = argparse.ArgumentParser(description="Synthetic finance variance investigation")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list")
    run = sub.add_parser("run")
    run.add_argument("case", choices=[c["id"] for c in load_cases()])
    run.add_argument("--live", action="store_true")
    run.add_argument("--out", default="outputs")
    ev = sub.add_parser("evaluate")
    ev.add_argument("--live", action="store_true")
    review = sub.add_parser("review", help="Record a local demo review; not an authenticated approval")
    review.add_argument("report")
    review.add_argument("--reviewer", required=True)
    review.add_argument("--decision", required=True, choices=["accept", "return"])
    review.add_argument("--note", required=True)
    args = parser.parse_args()
    if args.command == "list":
        for case in load_cases():
            print(f'{case["id"]:14} {case["title"]}')
    elif args.command == "evaluate":
        result = evaluate(args.live)
        print(json.dumps(result, indent=2))
        raise SystemExit(0 if result["passed"] == result["total"] else 1)
    elif args.command == "review":
        path = Path(args.report)
        report = json.loads(path.read_text())
        if report.get("status") != "DRAFT_REQUIRES_HUMAN_REVIEW":
            raise ValueError("Expected a draft report")
        if not args.reviewer.strip() or not args.note.strip():
            raise ValueError("Reviewer and rationale cannot be blank")
        if args.decision == "accept" and (report["gross_unexplained_cents"] or report.get("incomplete_investigation")):
            raise ValueError("Cannot accept unresolved or incomplete investigation")
        record = {"report_sha256": digest(report), "reviewer": args.reviewer, "decision": args.decision,
                  "note": args.note, "at": datetime.now(timezone.utc).isoformat(),
                  "control_level": "local demonstration only; reviewer identity is not authenticated"}
        out = path.with_name(path.stem + '.review.json')
        with out.open('x') as f:
            json.dump(record, f, indent=2)
        print(out)
    else:
        case = next(c for c in load_cases() if c["id"] == args.case)
        report = investigate(case, args.live)
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        (out / (args.case + '.json')).write_text(json.dumps(report, indent=2))
        (out / (args.case + '.html')).write_text(render(report))
        print(f'{report["status"]}\nJSON: {out / (args.case + ".json")}\nHTML: {out / (args.case + ".html")}')
        if report.get("incomplete_investigation"):
            raise SystemExit("Investigation incomplete; inspect the JSON report for details")


if __name__ == "__main__":
    main()
