# Understand and demonstrate the project

## Five-minute demo

1. Run `python -m variance_agent run known`. Open `outputs/known.html`. Explain the $3,000 delta and source reference.
2. Run `python -m variance_agent run missing`. Show the separate $2,500 open question.
3. Run `python -m variance_agent run offsetting`. Explain why net zero does not mean the analysis is complete.
4. Run `python -m variance_agent run conflict`. Show that contradictory evidence cannot be silently selected away.
5. Open the trace. Distinguish tool selection from deterministic validation and offline mode from live mode.

## Be able to answer

- Why might an agent help? Dynamic investigation across evidence sources; this small demo does not prove superiority over a workflow.
- What does the LLM decide? Tool sequence and proposed vendor/evidence selections. It cannot calculate authoritative totals, approve, or post.
- What prevents fabricated explanations? Scoped IDs, retrieval checks, complete evidence requirements, reconciliation, and source-based rendering. These checks do not prove that source documents are true.
- What happens on model failure? An incomplete draft with unresolved movements, never silent approval.
- How is success measured? Correct amounts, supported drivers, unresolved exceptions, traceability, and completion. Live reasoning, cost, latency, and human review effort remain to be measured.
- What did you personally contribute? Describe your actual use-case choice, review, design changes, and learning. The initial code and tests were AI-assisted. Do not imply deployment or work you have not done.

## Hands-on exercises

1. Read `core.py` and explain every rejection condition in `submit_findings`.
2. Change the synthetic CloudCo actual by $100 without changing the evidence. Predict and inspect the rejection.
3. Add a matching vendor credit and examine both net and gross residuals.
4. Add a new held-out fixture and write the expected outcome before running it.
5. Run a live investigation with your own authorized API key. Compare tool order and outcome with offline mode.

Complete these yourself before describing the implementation as work you can independently explain or maintain.
