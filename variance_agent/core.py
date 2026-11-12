"""Financial arithmetic and evidence checks; no model-generated math is trusted."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class Investigation:
    def __init__(self, case, max_calls=24):
        self.case = deepcopy(case)
        self.max_calls = max_calls
        self.events = []
        self.seen = set()
        self.overview_read = False
        self.vendors_read = set()
        self.report = None
        self.groups = {}
        for row in self.case["ledger"]:
            if row["period"] not in ("budget", "actual") or type(row["cents"]) is not int:
                raise ValueError("Ledger requires integer cents and actual/budget periods")
            group = self.groups.setdefault(row["vendor"], {"budget_cents": 0, "actual_cents": 0, "transaction_ids": []})
            group[row["period"] + "_cents"] += row["cents"]
            group["transaction_ids"].append(row["id"])
        for group in self.groups.values():
            group["delta_cents"] = group["actual_cents"] - group["budget_cents"]

    def overview(self):
        self.overview_read = True
        budget = sum(x["budget_cents"] for x in self.groups.values())
        actual = sum(x["actual_cents"] for x in self.groups.values())
        gross = sum(abs(x["delta_cents"]) for x in self.groups.values())
        return {"case_id": self.case["id"], "account": self.case["account"], "currency": "USD",
                "budget_cents": budget, "actual_cents": actual, "delta_cents": actual-budget,
                "variance_percent": round(100*(actual-budget)/abs(budget), 2) if budget else None,
                "gross_movement_cents": gross,
                "material": abs(actual-budget) >= self.case["threshold_cents"] or gross >= self.case["threshold_cents"],
                "vendors": sorted(self.groups, key=lambda v: (-abs(self.groups[v]["delta_cents"]), v))}

    def vendor_detail(self, vendor):
        if vendor not in self.groups:
            raise ValueError("Vendor outside this case")
        self.vendors_read.add(vendor)
        return {"vendor": vendor, **self.groups[vendor], "documents": [d["id"] for d in self.case["documents"] if d["vendor"] == vendor]}

    def read_evidence(self, document_id):
        for d in self.case["documents"]:
            if d["id"] == document_id:
                self.seen.add(document_id)
                return {"untrusted_source": True, **d}
        raise ValueError("Document outside this case")

    def submit_findings(self, claims):
        if not self.overview_read:
            raise ValueError("Read the overview before submission")
        accepted, rejected, used = [], [], set()
        for claim in claims:
            vendor, ids = claim.get("vendor"), claim.get("evidence_ids")
            reason = None
            docs = [d for d in self.case["documents"] if d["vendor"] == vendor]
            if vendor not in self.vendors_read:
                reason = "Vendor detail not inspected"
            elif vendor in used:
                reason = "Duplicate vendor claim"
            elif not isinstance(ids, list) or not ids or any(not isinstance(i, str) for i in ids):
                reason = "Evidence IDs required"
            elif set(ids) != {d["id"] for d in docs} or not set(ids).issubset(self.seen):
                reason = "Inspect and cite every available document for this vendor"
            elif any(d["status"] != "verified" for d in docs):
                reason = "Unverified source; human clarification required"
            elif len({(d["supported_delta_cents"], d["reason"]) for d in docs}) != 1:
                reason = "Conflicting evidence; human clarification required"
            elif docs[0]["supported_delta_cents"] != self.groups[vendor]["delta_cents"]:
                reason = "Evidence amount does not reconcile to vendor movement"
            if reason:
                rejected.append({"vendor": vendor, "reason": reason})
                continue
            used.add(vendor)
            accepted.append({"vendor": vendor, "delta_cents": self.groups[vendor]["delta_cents"],
                             "reason": docs[0]["reason"], "evidence_ids": sorted(set(ids)),
                             "transaction_ids": self.groups[vendor]["transaction_ids"]})
        unresolved = [{"vendor": v, "delta_cents": g["delta_cents"],
                       "question": "Provide reconciled, verified evidence for this movement."}
                      for v, g in self.groups.items() if v not in used and g["delta_cents"]]
        overview = self.overview()
        net_explained = sum(c["delta_cents"] for c in accepted)
        gross_supported = sum(abs(c["delta_cents"]) for c in accepted)
        self.report = {"schema_version": 1, "case_id": self.case["id"], "title": self.case["title"],
                       "created_at": datetime.now(timezone.utc).isoformat(),
                       "data_sha256": digest(self.case), "synthetic_data": True,
                       "status": "DRAFT_REQUIRES_HUMAN_REVIEW", "overview": overview,
                       "supported_drivers": accepted, "rejected_claims": rejected, "unresolved": unresolved,
                       "net_explained_cents": net_explained,
                       "net_unexplained_cents": overview["delta_cents"] - net_explained,
                       "gross_unexplained_cents": sum(abs(c["delta_cents"]) for c in unresolved),
                       "gross_evidence_coverage": gross_supported / overview["gross_movement_cents"] if overview["gross_movement_cents"] else 1.0,
                       "evidence": [d for d in self.case["documents"] if d["id"] in self.seen]}
        return {"status": self.report["status"], "accepted": len(accepted), "rejected": rejected,
                "unresolved_vendors": [u["vendor"] for u in unresolved]}

    def call(self, name, args):
        if self.report is not None:
            raise ValueError("Investigation already submitted")
        if len(self.events) >= self.max_calls:
            raise ValueError("Tool-call budget exceeded")
        allowed = {"get_overview": self.overview, "get_vendor_detail": self.vendor_detail,
                   "read_evidence": self.read_evidence, "submit_findings": self.submit_findings}
        entry = {"sequence": len(self.events)+1, "tool": name, "arguments": deepcopy(args)}
        try:
            if name not in allowed:
                raise ValueError("Tool not allowed")
            result = allowed[name](**args)
            entry["result"] = result
        except (ValueError, TypeError, KeyError) as e:
            result = {"error": str(e)}
            entry["result"] = result
        self.events.append(entry)
        return result

    def finalize(self, mode):
        if self.report is None:
            # Fail closed on timeout, refusal, malformed response, or early stop.
            self.overview()
            self.submit_findings([])
            self.report["incomplete_investigation"] = True
        self.report["mode"] = mode
        self.report["audit_trail"] = deepcopy(self.events)
        return self.report
