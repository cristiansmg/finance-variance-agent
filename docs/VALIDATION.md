# Validation record — November 12, 2026

- `python -m unittest discover -s tests -v`: 20 tests passed.
- `python -m variance_agent evaluate`: 7/7 offline synthetic scenarios passed.
- CLI generated reports and JSON traces for known, missing, and offsetting scenarios.
- Review-command tests verify unresolved acceptance is blocked, accepted records bind to report hashes, original reports remain unchanged, and existing review records cannot be silently overwritten.
- Provider tests use scripted tool responses and a simulated timeout. No live Claude API evaluation has been performed.
- Prompt-injection checks establish that the host has no approval or posting tool and that unverified evidence is rejected. They do not establish resistance of a real model to malicious instructions.

Python runtime: 3.12. Standard library only. See `examples/evaluation.json` for individual checks and `tests/test_agent.py` for executable tests.

Not validated: live-model behavior, semantic extraction of arbitrary documents, production identity/access management, immutable audit storage, cost/latency, large datasets, multiple currencies, source-system reconciliation, or operational finance controls.
