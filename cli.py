"""CLI runner: reads data/, runs debate, prints final report + metrics, saves JSON."""
from __future__ import annotations
import argparse
import json
from datetime import datetime
from pathlib import Path

from core.data_loader import evidence_to_prompt, load_evidence
from core.debate import run_debate
from core.llm_backends import make_backend
from core.metrics import summarize


def main():
    p = argparse.ArgumentParser(description="Medical Assembly multi-agent diagnosis")
    p.add_argument("--backend", default=None,
                   help="anthropic | openai | gemini | ollama (default: env LLM_BACKEND)")
    p.add_argument("--model", default=None, help="override model name")
    p.add_argument("--summary", default=None,
                   help="One-line case summary (otherwise read data/case.txt or prompt)")
    p.add_argument("--truth", default=None, help="ground-truth diagnosis (for calibration)")
    p.add_argument("--data-dir", default=None)
    args = p.parse_args()

    backend = make_backend(args.backend, model=args.model) if args.model else make_backend(args.backend)
    print(f"\n[backend={backend.name}  model={backend.model}]\n")

    evidence = load_evidence(args.data_dir)
    evidence_text = evidence_to_prompt(evidence)
    print(f"Loaded {len(evidence['files_read'])} files: {evidence['files_read']}\n")

    if args.summary:
        case_summary = args.summary
    else:
        case_file = Path(args.data_dir or "data") / "case.txt"
        if case_file.exists():
            case_summary = case_file.read_text(encoding="utf-8").strip()
        else:
            case_summary = input("Case summary (one line): ").strip() \
                or "Patient presents for evaluation; see attached evidence."

    def on_event(e: dict):
        kind = e["kind"]
        if kind == "specialists_selected":
            print(f"🏥 Panel: {', '.join(e['names'])}")
        elif kind == "round_start":
            print(f"\n━━━ Round {e['round']} ━━━")
        elif kind == "speaker_start":
            print(f"  🩺 {e['name']}…")
        elif kind == "vote_result":
            print(f"  📊 Round {e['round']} agreement: {e['score']:.0%}")
        elif kind == "converged":
            print(f"  ✅ Converged at round {e['round']} ({e['score']:.0%})")
        elif kind == "status":
            print(f"  … {e['message']}")

    state = run_debate(backend, case_summary, evidence, evidence_text, on_event=on_event)
    metrics = summarize(state, true_diagnosis=args.truth)

    out_dir = Path("reports")
    out_dir.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"report_{stamp}.json"
    out_path.write_text(json.dumps({
        "case_summary": state.case_summary,
        "selected_specialists": state.selected_specialists,
        "rounds_completed": state.rounds_completed,
        "converged": state.converged,
        "opinions": [o.model_dump() for o in state.opinions],
        "votes": [[v.model_dump() for v in rv] for rv in state.votes],
        "final_report": state.final_report.model_dump() if state.final_report else None,
        "metrics": metrics,
    }, indent=2))
    print(f"\n💾 Saved {out_path}")

    if state.final_report:
        r = state.final_report
        print("\n" + "=" * 70)
        print(f"PRIMARY DIAGNOSIS: {r.primary_diagnosis.name}  (p={r.primary_diagnosis.probability:.2f})")
        print("=" * 70)
        print(f"\nWHY: {r.why_it_happened}\n")
        print("WHAT TO DO:")
        for a in r.what_user_should_do:
            print(f"  • {a}")
        print("\nMEDICATIONS:")
        for m in r.medications:
            print(f"  • {m.name} — {m.dosage} × {m.duration}")
            print(f"      side effects: {', '.join(m.common_side_effects[:5])}")
        print(f"\nAgreement: {r.agreement_score:.0%}")
        print(f"\n{r.disclaimer}")


if __name__ == "__main__":
    main()
