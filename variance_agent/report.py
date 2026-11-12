"""Self-contained report renderer. Escape all source and model-derived strings."""
import html
import json


def money(cents):
    return f"${cents / 100:,.2f}"


def render(report):
    e = lambda x: html.escape(str(x))
    o = report["overview"]
    drivers = "".join(f'<tr><td>{e(d["vendor"])}</td><td>{money(d["delta_cents"])}</td><td>{e(d["reason"])}</td><td>{e(", ".join(d["evidence_ids"]))}</td></tr>' for d in report["supported_drivers"])
    unresolved = "".join(f'<li><strong>{e(d["vendor"])}</strong> · {money(d["delta_cents"])}<br>{e(d["question"])}</li>' for d in report["unresolved"])
    sources = "".join(f'<details><summary>{e(d["id"])} · {e(d["status"])}</summary><p>{e(d["text"])}</p><small>{e(d["provenance"])}</small></details>' for d in report["evidence"])
    audit = "".join(f'<details><summary>{x["sequence"]:02d} · {e(x["tool"])}</summary><pre>{e(json.dumps(x, indent=2))}</pre></details>' for x in report["audit_trail"])
    return f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Variance investigation · {e(report['title'])}</title><style>
*{{box-sizing:border-box}}body{{margin:0;background:#f3f5f4;color:#152c2b;font:16px/1.6 system-ui,sans-serif}}main{{max-width:1080px;margin:auto;padding:48px 24px}}header{{border-top:5px solid #226e63;padding:24px 0}}.eyebrow{{text-transform:uppercase;letter-spacing:.16em;font-size:12px;font-weight:700;color:#226e63}}h1{{font-size:clamp(28px,4vw,44px);line-height:1.15;margin:14px 0}}h2{{font-size:21px}}.badge{{display:inline-block;background:#f7e9c7;padding:6px 12px;border-radius:5px;font-size:13px}}.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:16px;margin:24px 0}}.card,section{{background:white;border:1px solid #dbe3df;border-radius:10px;padding:24px;margin-bottom:16px}}.card strong{{display:block;font-size:27px}}.card small,small{{color:#526763}}table{{border-collapse:collapse;width:100%;font-size:14px}}td,th{{text-align:left;padding:12px 8px;border-bottom:1px solid #e3e9e6;vertical-align:top}}.scroll{{overflow-x:auto}}details{{border-bottom:1px solid #dbe3df;padding:12px 0}}summary{{cursor:pointer;font-weight:600}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px;background:#eff3f1;padding:16px}}li{{margin:12px 0}}footer{{font-size:12px;color:#526763;overflow-wrap:anywhere}}@media print{{body{{background:white}}main{{padding:0}}details{{break-inside:avoid}}}}
</style><main><header><div class="eyebrow">Finance variance agent / research prototype</div><h1>{e(report['title'])}</h1><p>{e(o['account'])} · USD · Synthetic data</p><span class="badge">Draft — human review required</span></header>
<div class="cards"><div class="card"><small>Budget</small><strong>{money(o['budget_cents'])}</strong></div><div class="card"><small>Actual</small><strong>{money(o['actual_cents'])}</strong></div><div class="card"><small>Net variance · actual minus budget</small><strong>{money(o['delta_cents'])}</strong></div><div class="card"><small>Gross evidence coverage</small><strong>{report['gross_evidence_coverage']:.0%}</strong></div></div>
<section><h2>Evidence-supported drivers</h2><p>Amounts are calculated by Python. Reasons are reproduced from validated fixture evidence; they are not independently established causal facts.</p><div class="scroll"><table><thead><tr><th>Vendor</th><th>Movement</th><th>Documented explanation</th><th>Sources</th></tr></thead><tbody>{drivers or '<tr><td colspan="4">No supported drivers established.</td></tr>'}</tbody></table></div></section>
<section><h2>Open questions</h2><p>Net unexplained: <strong>{money(report['net_unexplained_cents'])}</strong> · Gross unexplained: <strong>{money(report['gross_unexplained_cents'])}</strong></p><ul>{unresolved or '<li>All vendor movements have matching fixture evidence. Human review is still required.</li>'}</ul><p>Gross amounts expose offsetting movements that a net total can conceal.</p></section>
<section><h2>Source evidence</h2>{sources or '<p>No source documents were retrieved.</p>'}</section><section><h2>Investigation trace</h2><p>Mode: <strong>{e(report['mode'])}</strong>. Offline mode uses deterministic rules, not an AI model.</p>{audit}</section>
<footer>Case {e(report['case_id'])} · Created {e(report['created_at'])}<br>Data SHA-256: {e(report['data_sha256'])}<br>Educational prototype. No ERP integration, journal posting, or production approval controls.</footer></main></html>'''
