"""Self-contained HTML. Untrusted text never becomes markup or executable content."""
from html import escape


def render(state, verdict, coverage, findings):
    def text(value):
        return escape(str(value), quote=True)

    def refs(items):
        return ' '.join(f'<a href="{text(x["path"])}">{text(x["sha256"][:12])}</a>' for x in items) or '—'

    sections = ['<!doctype html><html lang="en"><head><meta charset="utf-8">',
                '<meta name="viewport" content="width=device-width,initial-scale=1">',
                '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'">',
                '<title>Code Audit</title><style>',
                ':root{color-scheme:light}body{margin:0;background:#f1f5f9;color:#172033;font:16px/1.6 system-ui}',
                'main{max-width:1100px;margin:2rem auto;padding:2rem;background:white;border-radius:12px}',
                'h1{font-size:2.1rem;margin:0}h2{border-bottom:1px solid #cbd5e1;padding-top:1rem}h3{margin-bottom:.4rem}',
                'a{color:#174fa6}nav a{margin-right:1.3rem}code{font-size:.85em;overflow-wrap:anywhere}',
                'table{border-collapse:collapse;width:100%;font-size:.9rem}td,th{text-align:left;padding:.7rem;border-bottom:1px solid #e2e8f0}',
                'th{background:#f8fafc}article{border-left:4px solid #64748b;padding:0 1.2rem;margin:2rem 0}',
                '.status{display:inline-block;font-weight:750;padding:.3rem .8rem;border-radius:6px;background:#e2e8f0}',
                '.READY{background:#dcfce7;color:#14532d}.INCOMPLETE{background:#fef3c7;color:#78350f}',
                '.CHANGES_REQUIRED{background:#fee2e2;color:#7f1d1d}.muted{color:#475569}.wrap{overflow-x:auto}',
                'dt{font-weight:650}dd{margin:0 0 .6rem;overflow-wrap:anywhere}.prose{white-space:pre-wrap;overflow-wrap:anywhere}',
                '@media(max-width:700px){main{margin:0;padding:1rem;border-radius:0}table{font-size:.8rem}}',
                '</style></head><body><main><header><p class="muted">EVIDENCE-BACKED CHANGESET REVIEW</p>',
                '<h1>Code Audit</h1>', f'<p><span class="status {text(verdict["verdict"])}">{text(verdict["verdict"])}</span></p>',
                f'<p>Coverage: <b>{text(verdict["completion"])}</b> · Freshness: <b>{text(verdict["freshness"])}</b></p>',
                f'<p class="muted">Run {text(state["run_id"])} · Generated {text(verdict["generated"])}</p>',
                '<nav><a href="#decision">Decision</a><a href="#coverage">Coverage</a><a href="#findings">Findings</a><a href="#process">Process</a></nav>',
                '</header><section id="decision"><h2>Decision and scope</h2><dl>']
    for key, label in [('H', 'Reviewed head'), ('B', 'Target tip'), ('M', 'Merge base'), ('A', 'Comparison base'), ('I', 'Integration source')]:
        sections.append(f'<dt>{label} ({key})</dt><dd><code>{text(verdict["scope"][key])}</code></dd>')
    sections.append('</dl><p>Committed source and introduced history are in scope. Unrelated local edits are excluded.</p>')
    sections.append('<p>Intent: ' + ('supplied.' if state['inputs']['intent_available'] else 'not supplied; requirements must not be invented.') + '</p>')
    if verdict['blocking_ids']:
        sections.append('<p><b>Blocking:</b> ' + text(', '.join(verdict['blocking_ids'])) + '</p>')
    if verdict['missing']:
        sections.append('<ul>' + ''.join('<li>' + text(x) + '</li>' for x in verdict['missing']) + '</ul>')
    else:
        sections.append('<p>All required checks and reviews completed.</p>')
    sections.append('</section><section id="coverage"><h2>Review coverage</h2><div class="wrap"><table><thead><tr><th>Task</th><th>Required</th><th>State</th><th>Evidence hashes</th></tr></thead><tbody>')
    for entry in coverage:
        results = state['results'].get(entry['id'], [])
        outputs = results[-1]['outputs'] if results else []
        sections.append(f'<tr><td>{text(entry["id"])}</td><td>{text(entry["required"])}</td><td>{text(entry["state"])}</td><td>{refs(outputs)}</td></tr>')
    sections.append('</tbody></table></div></section><section id="findings"><h2>Findings and investigations</h2>')
    if not findings:
        sections.append('<p>No validated review findings recorded. This does not imply completed coverage.</p>')
    for f in findings:
        sections += ['<article>', f'<h3>{text(f["id"])} · {text(f["priority"])} · {text(f["category"])}</h3>',
                     f'<p class="muted">{text(f["evidence_status"])} · {text(f["attribution"])} · {text(f["disposition"])}</p><dl>']
        for key, label in [('trigger', 'Trigger'), ('impact', 'Impact'), ('reasoning', 'Evidence and inference'), ('remediation', 'Remediation')]:
            sections.append(f'<dt>{label}</dt><dd class="prose">{text(f[key])}</dd>')
        sections.append('</dl><ul>')
        for loc in f['locations']:
            sections.append('<li><code>' + text(f'{loc["snapshot"]}:{loc["path"]}:{loc["start_line"]}-{loc["end_line"]}') + '</code></li>')
        sections.append('</ul><p>Evidence: ' + refs(f['contributing_evidence']) + '</p>')
        if f.get('verification'):
            sections.append('<p class="prose"><b>Verification:</b> ' + text(f['verification']['challenge']) + '</p>')
        if f.get('consolidation'):
            sections.append('<details><summary>Behavioral consolidation comparison</summary><dl>')
            for key, value in f['consolidation'].items():
                sections.append('<dt>' + text(key.replace('_', ' ')) + '</dt><dd class="prose">' + text(value) + '</dd>')
            sections.append('</dl></details>')
        sections.append('</article>')
    sections.append('</section><section id="process"><h2>Process and hypotheses</h2>')
    status = state['process_reviews'][-1]['status'] if state['process_reviews'] else 'unavailable'
    sections.append('<p>Process review: <b>' + text(status) + '</b>. Missing logs do not satisfy or block product coverage.</p>')
    sections.append('<p><a href="hypotheses/index.json">Hypothesis bundle index</a></p></section>')
    sections.append('<footer><h2>Limits of this decision</h2><p>A clean audit is not proof of defect absence. Runtime evidence covers only the inspected scenarios. Recheck freshness before consuming readiness.</p><p>Job lifetime belongs to the existing host. No cross-run cache is used. Source, logs and hypotheses are private evidence; publishing or changing product code requires its own instruction.</p></footer></main></body></html>')
    return ''.join(sections)
