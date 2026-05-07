"""Streamlit UI — drop files in data/, watch the debate, see graphical results."""
from __future__ import annotations
import json
import os
import queue
import threading
from collections import defaultdict
from urllib.error import URLError
from urllib.request import urlopen

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from core.data_loader import evidence_to_prompt, load_evidence, DATA_DIR
from core.debate import run_debate
from core.llm_backends import make_backend
from core.metrics import summarize
from core.schemas import DebateState
from core.specialists import SPECIALISTS

st.set_page_config(page_title="ClaudeMEd — Multi-Agent Diagnosis", layout="wide", page_icon="🩺")


def _default_backend_kind() -> str:
    env_kind = (os.getenv("LLM_BACKEND") or "").strip().lower()
    if env_kind:
        return env_kind
    if os.getenv("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.getenv("OPENAI_API_KEY"):
        return "openai"
    if os.getenv("GEMINI_API_KEY"):
        return "gemini"
    return "ollama"


def _backend_status(kind: str) -> str:
    if kind == "ollama":
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
        try:
            urlopen(base_url.replace("/v1", "/api/tags"), timeout=2)
            return f"Ollama reachable at {base_url}"
        except Exception:
            return f"Ollama not reachable at {base_url}. Start it with `ollama serve` or choose another backend."
    if kind == "anthropic" and not os.getenv("ANTHROPIC_API_KEY"):
        return "Anthropic selected but ANTHROPIC_API_KEY is not set."
    if kind == "openai" and not os.getenv("OPENAI_API_KEY"):
        return "OpenAI selected but OPENAI_API_KEY is not set."
    if kind == "gemini" and not os.getenv("GEMINI_API_KEY"):
        return "Gemini selected but GEMINI_API_KEY is not set."
    return "Backend configured."

# ─── sidebar: config ───────────────────────────────────────────────────────
with st.sidebar:
    st.title("🩺 ClaudeMEd")
    st.caption("Multi-specialist debate → consensus diagnosis")

    default_backend = _default_backend_kind()
    backend_kind = st.selectbox("Backend", ["anthropic", "openai", "gemini", "ollama"],
                                index=["anthropic", "openai", "gemini", "ollama"].index(default_backend))
    default_models = {
        "anthropic": os.getenv("ANTHROPIC_MODEL", "claude-opus-4-7"),
        "openai":    os.getenv("OPENAI_MODEL", "gpt-4.1"),
        "gemini":    os.getenv("GEMINI_MODEL", "gemini-2.5-pro"),
        "ollama":    os.getenv("OLLAMA_MODEL", "qwen3:0.6b"),
    }
    model = st.text_input("Model", value=default_models[backend_kind])
    temperature = st.slider("Temperature", 0.0, 1.0, 0.3, 0.05)
    st.caption(_backend_status(backend_kind))

    st.divider()
    st.subheader("📁 Data folder")
    st.code(str(DATA_DIR))
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted([p.name for p in DATA_DIR.iterdir() if p.is_file() and not p.name.startswith(".")])
    st.write(f"**{len(files)} file(s):**")
    for f in files:
        st.write(f"• `{f}`")

    uploads = st.file_uploader("Add files", accept_multiple_files=True,
                            type=["txt", "md", "csv", "pdf", "json", "png", "jpg", "jpeg"])
    if uploads:
        for u in uploads:
            (DATA_DIR / u.name).write_bytes(u.getbuffer())
        st.cache_data.clear()
        st.success(f"Saved {len(uploads)} file(s). Refresh.")

    st.divider()
    st.caption("Debate parameters via env: MIN_SPECIALISTS, MAX_SPECIALISTS, MAX_DEBATE_ROUNDS, SATISFACTION_THRESHOLD")


# ─── main ──────────────────────────────────────────────────────────────────
st.title("Medical Multi-Agent Diagnosis")

with st.form("case_form", clear_on_submit=False):
    case_summary = st.text_area(
        "Case summary (one paragraph — the patient's chief complaint and key context)",
        value=st.session_state.get("case_summary", ""),
        height=120,
        placeholder="e.g. 47-year-old woman, 3 months progressive fatigue, 8 kg unintentional weight loss, "
                    "night sweats, palpable cervical lymphadenopathy. Non-smoker. No travel.",
    ) or ""

    col_a, col_b = st.columns([1, 4])
    run_btn = col_a.form_submit_button("▶ Run debate", type="primary")
    truth = col_b.text_input("(optional) Ground-truth diagnosis for calibration", "")


# ─── run state ─────────────────────────────────────────────────────────────
if "events" not in st.session_state:
    st.session_state.events = []
if "state" not in st.session_state:
    st.session_state.state = None


def _get_backend(backend_kind, model, temperature, on_call=None):
    return make_backend(backend_kind, model=model, temperature=temperature, on_call=on_call)


@st.cache_data(show_spinner=False)
def _get_evidence(data_dir: str | None = None):
    return load_evidence(data_dir)


def _run(backend_kind, model, temperature, case_summary, q):
    try:
        def on_llm_call(backend_name, model_name, system, user, response):
            q.put({"kind": "llm_trace", "backend": backend_name, "model": model_name, "system": system, "user": user, "response": response})

        backend = _get_backend(backend_kind, model, temperature, on_call=on_llm_call)
        evidence = _get_evidence()
        evidence_text = evidence_to_prompt(evidence)

        def on_event(e):
            q.put(e)

        state = run_debate(backend, case_summary, evidence, evidence_text, on_event=on_event)
        q.put({"kind": "_final_state", "state": state.model_dump()})
    except URLError as ex:
        q.put({"kind": "_error", "message": f"Connection error reaching backend: {ex}. Check the selected backend and server URL."})
    except Exception as ex:
        message = str(ex)
        if backend_kind == "ollama" and ("connection" in message.lower() or "refused" in message.lower()):
            message = (
                f"Connection error reaching Ollama at {os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434/v1')}. "
                "Start Ollama (`ollama serve`) or switch to a cloud backend with valid API keys."
            )
        elif backend_kind in {"anthropic", "openai", "gemini"} and "api key" in message.lower():
            message = (
                f"{backend_kind.title()} is selected but its API key is missing. "
                "Set the key in .env or switch to Ollama."
            )
        q.put({"kind": "_error", "message": message})
    finally:
        q.put({"kind": "_eof"})


def _render_event_log(events: list[dict]):
    if not events:
        st.info("No completed run yet. Enter a case summary and click **Run debate**.")
        return

    st.subheader("Latest debate transcript")
    live_lines: list[str] = []
    for e in events:
        if e["kind"] == "specialists_selected":
            live_lines.append(f"🏥 **Panel:** {', '.join(e['names'])}")
        elif e["kind"] == "round_start":
            live_lines.append(f"\n### ━━━ Round {e['round']} ━━━")
        elif e["kind"] == "speaker_start":
            live_lines.append(f"🩺 {e['name']} speaking…")
        elif e["kind"] == "opinion":
            o = e["opinion"]
            preview = (o.get("monologue") or "")[:500]
            live_lines.append(f"  💬 **{o['name']}** ({o['specialty']}): {preview}…")
        elif e["kind"] == "vote_result":
            live_lines.append(f"📊 Round {e['round']} agreement: **{e['score']:.0%}**")
        elif e["kind"] == "converged":
            live_lines.append(f"✅ **Converged** at round {e['round']} ({e['score']:.0%})")
        elif e["kind"] == "status":
            live_lines.append(f"… {e['message']}")
        elif e["kind"] == "done":
            live_lines.append("🏁 Final report ready.")

    st.markdown("\n\n".join(live_lines[-120:]))


if run_btn:
    st.session_state.events = []
    st.session_state.state = None
    st.session_state.case_summary = case_summary

    q: queue.Queue = queue.Queue()
    t = threading.Thread(target=_run, args=(backend_kind, model, temperature, case_summary, q), daemon=True)
    t.start()

    progress = st.progress(0, text="Starting…")
    log_placeholder = st.empty()
    live_lines: list[str] = []
    rounds_done = 0

    while True:
        try:
            e = q.get(timeout=1200)
        except queue.Empty:
            st.error("Timed out waiting for backend.")
            break

        if e["kind"] == "_eof":
            break
        if e["kind"] == "_error":
            st.error(f"Error: {e['message']}")
            break
        if e["kind"] == "_final_state":
            st.session_state.state = e["state"]
            continue

        st.session_state.events.append(e)

        if e["kind"] == "specialists_selected":
            live_lines.append(f"🏥 **Panel:** {', '.join(e['names'])}")
        elif e["kind"] == "round_start":
            live_lines.append(f"\n### ━━━ Round {e['round']} ━━━")
        elif e["kind"] == "speaker_start":
            live_lines.append(f"🩺 {e['name']} speaking…")
        elif e["kind"] == "opinion":
            o = e["opinion"]
            preview = (o.get("monologue") or "")[:300]
            live_lines.append(f"  💬 **{o['name']}** ({o['specialty']}): {preview}…")
        elif e["kind"] == "vote_result":
            live_lines.append(f"📊 Round {e['round']} agreement: **{e['score']:.0%}**")
            rounds_done = e["round"]
            progress.progress(min(1.0, rounds_done / int(os.getenv("MAX_DEBATE_ROUNDS", "4"))),
                              text=f"Round {rounds_done} done — agreement {e['score']:.0%}")
        elif e["kind"] == "converged":
            live_lines.append(f"✅ **Converged** at round {e['round']} ({e['score']:.0%})")
        elif e["kind"] == "status":
            live_lines.append(f"… {e['message']}")
        elif e["kind"] == "done":
            live_lines.append("🏁 Final report ready.")

        log_placeholder.markdown("\n\n".join(live_lines[-80:]))

    progress.progress(1.0, text="Complete")


# ─── results ───────────────────────────────────────────────────────────────
state = st.session_state.state
if not state:
    st.caption("Drop files in data/ (lab results as .txt/.csv, MRI/CT reports as .txt, PDFs supported).")
    _render_event_log(st.session_state.events)
    st.stop()


# Reconstruct light objects
events = st.session_state.events
opinions = state.get("opinions", [])
votes = state.get("votes", [])
report = state.get("final_report") or {}
selected = state.get("selected_specialists", [])

tab_debate, tab_hyp, tab_diag, tab_meds, tab_metrics, tab_traces = st.tabs(
    ["🗣 Debate", "📈 Hypotheses", "🎯 Diagnosis", "💊 Treatment", "📊 Metrics", "💻 Raw LLM"]
)


# ─── Tab 1: Debate ─────────────────────────────────────────────────────────
with tab_debate:
    st.subheader(f"Panel: {', '.join(SPECIALISTS[i]['name'] for i in selected if i in SPECIALISTS)}")

    # Speaker network graph (who critiqued whom)
    edges = []
    name_to_id = {SPECIALISTS[i]["name"]: i for i in selected if i in SPECIALISTS}
    for o in opinions:
        for crit in o.get("critiques", []):
            for nm, sid in name_to_id.items():
                if nm in crit and o["specialist_id"] != sid:
                    edges.append((o["name"], nm))
    show_graph = st.checkbox("Show critique network", value=False)
    if show_graph and edges:
        try:
            import networkx as nx
            G = nx.DiGraph()
            for n in name_to_id.keys():
                G.add_node(n)
            for a, b in edges:
                G.add_edge(a, b)
            pos = nx.spring_layout(G, seed=42)
            edge_x, edge_y = [], []
            for a, b in G.edges():
                x0, y0 = pos[a]
                x1, y1 = pos[b]
                edge_x += [x0, x1, None]
                edge_y += [y0, y1, None]
            node_x = [pos[n][0] for n in G.nodes()]
            node_y = [pos[n][1] for n in G.nodes()]
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=edge_x, y=edge_y, mode="lines",
                                     line=dict(width=1, color="#888"), hoverinfo="none"))
            fig.add_trace(go.Scatter(x=node_x, y=node_y, mode="markers+text",
                                     text=list(G.nodes()), textposition="top center",
                                     marker=dict(size=24, color="#4C9AFF")))
            fig.update_layout(showlegend=False, height=400, margin=dict(l=10, r=10, t=30, b=10),
                              title="Critique network (who challenged whom)",
                              xaxis=dict(visible=False), yaxis=dict(visible=False))
            st.plotly_chart(fig, use_container_width=True)
        except Exception:
            pass

    # Round-by-round transcript
    by_round = defaultdict(list)
    for o in opinions:
        by_round[o["round"]].append(o)
    for rnum in sorted(by_round.keys()):
        st.markdown(f"### Round {rnum}")
        for o in by_round[rnum]:
            with st.expander(f"💬 {o['name']} — {o['specialty']}", expanded=(rnum == 1)):
                st.markdown(f"**Monologue:** {o.get('monologue','')}")
                if o.get("hypotheses"):
                    df = pd.DataFrame([{
                        "Diagnosis": h["name"],
                        "p": h["probability"],
                        "Supports": " · ".join(h.get("supporting_evidence", [])[:3]),
                        "Contradicts": " · ".join(h.get("contradicting_evidence", [])[:3]),
                    } for h in o["hypotheses"]])
                    st.dataframe(df, hide_index=True, use_container_width=True)
                if o.get("recommended_tests"):
                    st.markdown("**Recommended tests:** " + " · ".join(o["recommended_tests"]))
                if o.get("critiques"):
                    st.markdown("**Critiques:**")
                    for c in o["critiques"]:
                        st.markdown(f"- {c}")
        # vote bar
        if rnum - 1 < len(votes):
            rv = votes[rnum - 1]
            counts = {"agree": 0, "disagree": 0, "abstain": 0}
            for v in rv:
                counts[v["vote"]] = counts.get(v["vote"], 0) + 1
            st.markdown("**Satisfaction vote:**")
            cols = st.columns(3)
            cols[0].metric("Agree", counts["agree"])
            cols[1].metric("Disagree", counts["disagree"])
            cols[2].metric("Abstain", counts["abstain"])
            for v in rv:
                emoji = {"agree": "✅", "disagree": "❌", "abstain": "🤷"}.get(v["vote"], "·")
                st.markdown(f"{emoji} **{v['name']}** (conf {v['confidence']:.2f}): {v['reason']}")


# ─── Tab 2: Hypothesis evolution ───────────────────────────────────────────
with tab_hyp:
    st.subheader("How hypotheses evolved across rounds")
    # Reconstruct from opinions list
    rows = []
    for o in opinions:
        for h in o.get("hypotheses", []):
            rows.append({"round": o["round"], "diagnosis": h["name"].strip().lower(),
                         "probability": h["probability"], "specialist": o["name"]})
    if rows:
        df = pd.DataFrame(rows)
        avg = df.groupby(["round", "diagnosis"])["probability"].mean().reset_index()
        # keep top-8 diagnoses by max prob
        top = list(avg.groupby(by="diagnosis")["probability"].max().nlargest(8).index)
        avg = avg[avg["diagnosis"].isin(top)]
        fig = px.line(avg, x="round", y="probability", color="diagnosis", markers=True,
                      title="Mean probability per diagnosis (top 8)")
        fig.update_layout(height=420)
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("All hypotheses (raw)")
        st.dataframe(df.sort_values(["round", "probability"], ascending=[True, False]),
                     hide_index=True, use_container_width=True)
    else:
        st.info("No hypotheses captured.")


# ─── Tab 3: Diagnosis ──────────────────────────────────────────────────────
with tab_diag:
    if not report:
        st.warning("No final report.")
    else:
        primary = report.get("primary_diagnosis", {})
        c1, c2 = st.columns([2, 1])
        with c1:
            st.subheader(f"🎯 {primary.get('name', '—')}")
            if primary.get("icd10"):
                st.caption(f"ICD-10: {primary['icd10']}")
            st.metric("Probability", f"{primary.get('probability', 0):.0%}")
            st.markdown(f"**Why this happened:** {report.get('why_it_happened','')}")

            if primary.get("supporting_evidence"):
                st.markdown("**Supporting evidence:**")
                for s in primary["supporting_evidence"]:
                    st.markdown(f"- ✅ {s}")
            if primary.get("contradicting_evidence"):
                st.markdown("**Contradicting evidence:**")
                for s in primary["contradicting_evidence"]:
                    st.markdown(f"- ⚠️ {s}")
        with c2:
            score = report.get("agreement_score", 0)
            fig = go.Figure(go.Indicator(
                mode="gauge+number",
                value=score * 100,
                title={"text": "Panel agreement"},
                gauge={"axis": {"range": [0, 100]},
                       "bar": {"color": "#4CAF50" if score >= 0.8 else "#FFC107" if score >= 0.5 else "#F44336"}},
            ))
            fig.update_layout(height=260, margin=dict(l=10, r=10, t=30, b=10))
            st.plotly_chart(fig, use_container_width=True)

        st.divider()
        st.subheader("Differential diagnoses")
        diffs = report.get("differential_diagnoses", [])
        if diffs:
            ddf = pd.DataFrame([{
                "Diagnosis": d["name"], "Probability": d["probability"],
                "Reasoning": d.get("reasoning", "")[:200],
            } for d in diffs])
            fig2 = px.bar(ddf, x="Probability", y="Diagnosis", orientation="h",
                          range_x=[0, 1], title="Differential probabilities")
            fig2.update_layout(height=320, yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig2, use_container_width=True)
            st.dataframe(ddf, hide_index=True, use_container_width=True)

        st.divider()
        c3, c4 = st.columns(2)
        with c3:
            st.subheader("✅ What you should do")
            for a in report.get("what_user_should_do", []):
                st.markdown(f"- {a}")
            st.subheader("🌱 Lifestyle")
            for a in report.get("lifestyle_recommendations", []):
                st.markdown(f"- {a}")
        with c4:
            st.subheader("🚨 Red flags — go to ER")
            for a in report.get("red_flags", []):
                st.markdown(f"- 🚨 {a}")
            st.subheader("👥 Specialist referrals")
            for a in report.get("specialist_referrals", []):
                st.markdown(f"- {a}")
            st.subheader("🧪 Follow-up tests")
            for a in report.get("follow_up_tests", []):
                st.markdown(f"- {a}")

        if report.get("dissenting_opinions"):
            st.divider()
            st.subheader("Dissenting voices")
            for d in report["dissenting_opinions"]:
                st.markdown(f"- 🔸 {d}")

        st.caption(report.get("disclaimer", ""))


# ─── Tab 4: Treatment ──────────────────────────────────────────────────────
with tab_meds:
    meds = report.get("medications", [])
    if not meds:
        st.info("No medications recommended.")
    else:
        st.subheader("Recommended medications")
        for m in meds:
            with st.container(border=True):
                top = st.columns([3, 2, 2])
                top[0].markdown(f"### 💊 {m['name']}")
                if m.get("generic_name"):
                    top[0].caption(f"Generic: {m['generic_name']}")
                top[1].markdown(f"**Dosage:** {m.get('dosage','')}")
                top[2].markdown(f"**Duration:** {m.get('duration','')}")
                st.markdown(f"**Indication:** {m.get('indication','')}")

                cse = m.get("common_side_effects", [])
                sse = m.get("serious_side_effects", [])
                ci = m.get("contraindications", [])
                ix = m.get("interactions", [])

                cols = st.columns(2)
                with cols[0]:
                    st.markdown("**Common side effects**")
                    for s in cse:
                        st.markdown(f"- {s}")
                with cols[1]:
                    st.markdown("**Serious side effects** ⚠️")
                    for s in sse:
                        st.markdown(f"- 🚩 {s}")
                if ci:
                    st.markdown(f"**Contraindications:** {' · '.join(ci)}")
                if ix:
                    st.markdown(f"**Interactions:** {' · '.join(ix)}")

        # side-effect heatmap
        rows = []
        for m in meds:
            for s in m.get("common_side_effects", []):
                rows.append({"Med": m["name"], "Side effect": s, "Severity": "common"})
            for s in m.get("serious_side_effects", []):
                rows.append({"Med": m["name"], "Side effect": s, "Severity": "serious"})
        if rows:
            df = pd.DataFrame(rows)
            st.subheader("Side-effect map")
            fig = px.scatter(df, x="Side effect", y="Med", color="Severity",
                             color_discrete_map={"common": "#4C9AFF", "serious": "#E53935"},
                             size_max=20)
            fig.update_traces(marker=dict(size=18))
            fig.update_layout(height=360, xaxis_tickangle=-30)
            st.plotly_chart(fig, use_container_width=True)


# ─── Tab 5: Metrics ────────────────────────────────────────────────────────
with tab_metrics:
    # Rebuild a DebateState-shaped object from the dump just enough for summarize()
    try:
        ds = DebateState.model_validate(state)
        m = summarize(ds, true_diagnosis=truth or None)
    except Exception as e:
        st.error(f"Could not compute metrics: {e}")
        m = {}

    if m:
        c = st.columns(4)
        c[0].metric("Rounds", m["rounds_completed"])
        c[1].metric("Converged", "✅" if m["converged"] else "❌")
        c[2].metric("Hypothesis stability (Jaccard)", f"{m['hypothesis_stability_jaccard']:.2f}")
        c[3].metric("Evidence citation rate", f"{m['evidence_citation_rate']:.0%}")

        if m.get("agreement_per_round"):
            ad = pd.DataFrame({"round": list(range(1, len(m["agreement_per_round"]) + 1)),
                               "agreement": m["agreement_per_round"]})
            fig = px.line(ad, x="round", y="agreement", markers=True,
                          range_y=[0, 1], title="Panel agreement per round")
            st.plotly_chart(fig, use_container_width=True)

        if m.get("specialist_engagement"):
            edf = pd.DataFrame([{"Specialist": k, **v} for k, v in m["specialist_engagement"].items()])
            fig = px.bar(edf, x="Specialist", y="words",
                         hover_data=["critiques", "hypotheses", "rounds"],
                         title="Specialist engagement (words spoken)")
            st.plotly_chart(fig, use_container_width=True)

        if "calibration_vs_truth" in m:
            cal = m["calibration_vs_truth"]
            cc = st.columns(3)
            cc[0].metric("Top-1 hit", cal["top1"])
            cc[1].metric("Top-3 hit", cal["top3"])
            cc[2].metric("Brier score", f"{cal['brier']:.3f}")

        st.subheader("Raw metrics JSON")
        st.json(m)

    st.divider()
    st.download_button("⬇ Download full run (JSON)",
                       data=json.dumps(state, indent=2, default=str),
                       file_name="claudemed_run.json", mime="application/json")

with tab_traces:
    st.markdown("### Raw LLM Communications")
    st.caption("Here you can inspect the exact payloads sent to and received from the local Ollama instance or remote API.")
    traces = [e for e in st.session_state.events if e["kind"] == "llm_trace"]
    if not traces:
        st.info("No LLM traces captured yet.")
    else:
        for i, t in enumerate(traces):
            with st.expander(f"📡 Backend call {i+1} : {t['backend']} / {t['model']}"):
                col1, col2, col3 = st.tabs(["System Prompt", "User Prompt", "Response"])
                with col1:
                    st.code(t["system"], language="markdown", wrap_lines=True)
                with col2:
                    st.code(t["user"], language="markdown", wrap_lines=True)
                with col3:
                    st.code(t["response"], language="json" if "{" in t["response"] else "markdown", wrap_lines=True)
