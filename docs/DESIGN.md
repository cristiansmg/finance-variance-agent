# Design decisions

## Why an agent at all?

On these tiny fixtures, a deterministic workflow is sufficient and cheaper. The live agent mode demonstrates a candidate architecture for investigations whose next step depends on findings: which vendor to inspect, which source to request, and when evidence is insufficient. It does not establish that an LLM outperforms the reference planner. The offline planner is an explicit comparison baseline.

## Why one agent?

One case, four tools, one validator. Multiple agents would add coordination overhead without a demonstrated need here. A production system may split independent investigations, but needs controlled aggregation and duplicate prevention.

## Why does the model not write the final explanation?

The model selects evidence; the host calculates amounts and uses the validated source reason. This intentionally constrains unsupported narrative. A future prose-generation stage would need separate claim-to-evidence checks and human assessment. Fluent text is not evidence.

## What is trusted?

The case fixture supplies scoped ledger rows, vendor metadata, and document verification labels. The host trusts these structured inputs for the demo. Raw document text is untrusted and HTML-escaped. There is no OCR, embedding database, arbitrary SQL, shell, URL fetch tool, or access to other cases. In production, the trusted input boundary must include identity, entitlements, source-system reconciliation, and verified document metadata.

## Completeness tradeoff

Requiring every available vendor document prevents cherry-picking conflicting evidence but is conservative and scales poorly. The claim unit is the entire vendor movement; partial evidence and multiple independent drivers for one vendor are intentionally unsupported. A production design would use granular transaction/driver allocations with overlap checks.

## Human review

The agent cannot access the review command. The local CLI emits a separate hash-bound record and blocks acceptance if unresolved movements remain. Anyone with local file access can modify files or supply a reviewer name; this is a demonstration of separation, not an enterprise control.

## Next validation milestones

1. Run live mode with an authorized key and record model ID, usage, timings, repeated outcomes, and failure traces.
2. Have a finance reviewer score a new held-out set without seeing expected outputs.
3. Add granular allocations and source-period/currency consistency checks.
4. Add authenticated reviewer identities, immutable storage, and entitlement tests before any real data.
5. Compare live agent value against the deterministic baseline. Keep the simpler approach unless the agent earns its complexity.
