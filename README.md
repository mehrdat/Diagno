# ClaudeMEd — Multi-Agent Medical Diagnosis

A supervised panel of specialist AI agents that **debate** a patient case and reach a deterministic
consensus diagnosis with calibrated probabilities, evidence-based medication recommendations
(with side-effects), and a metrics dashboard.

Two backend modes:
- **Cloud**: Anthropic, OpenAI, or Gemini
- **Local**: Ollama (or any OpenAI-compatible local server)

## Quick start

```bash
pip install -r requirements.txt
cp .env.example .env       # fill in API keys, choose backend / model
```

Drop your patient data into `data/`:

```
data/
├── case.txt                  # case summary (one paragraph)
├── patient_notes.txt         # history, complaint
├── blood_test.csv            # or .txt, lab panels
├── mri_report.txt            # MRI/CT/US written reports
├── chest_xray.png            # image (paste radiologist's reading in chest_xray.txt)
└── any.pdf                   # text-extractable PDFs
```

File naming convention (the loader uses these stems):
- `*note*`, `*history*`, `*complaint*`, `patient.*` → patient history
- `*lab*`, `*blood*`, `*test*`, any `.csv` → lab results
- `*mri*`, `*ct*`, `*xray*`, `*ultrasound*`, `*scan*`, `*imaging*` → imaging reports
- images: drop a sidecar `.txt` with the radiologist reading (same filename stem)

### Streamlit UI (recommended)

```bash
streamlit run app.py
```

Tabs:
1. **🗣 Debate** — full transcript per round, critique-network graph, satisfaction votes.
2. **📈 Hypotheses** — line chart of how each diagnosis probability evolved across rounds.
3. **🎯 Diagnosis** — primary diagnosis, agreement gauge, differentials bar chart, what-to-do, red flags.
4. **💊 Treatment** — medication cards with dosage, common + serious side effects, contraindications, interactions; side-effect heatmap.
5. **📊 Metrics** — agreement-per-round, hypothesis stability (Jaccard), evidence citation rate, specialist engagement, optional ground-truth calibration.

### CLI

```bash
python cli.py --backend anthropic --summary "47F, 3-mo fatigue, 8kg loss, night sweats, cervical LAD"
python cli.py --backend ollama  --model qwen2.5:14b
python cli.py --truth "Hodgkin lymphoma"   # adds calibration metrics
```

Reports saved to `reports/report_<timestamp>.json`.

## How the debate works

```
                  ┌────────────────────────────────────┐
[case+evidence] → │ ROUTER  → picks 5–8 specialists    │
                  └────────────────────────────────────┘
                              │
            ┌─────────────────▼──────────────────┐
            │  ROUND r:                          │
            │   each specialist independently    │
            │   produces hypotheses + monologue  │
            │   + critiques of round r-1         │
            └─────────────────┬──────────────────┘
                              │
                  ┌───────────▼────────────┐
                  │ SUPERVISOR drafts a    │
                  │ proposed primary dx    │
                  └───────────┬────────────┘
                              │
                  ┌───────────▼────────────┐
                  │ Each specialist VOTES  │
                  │ agree / disagree /     │
                  │ abstain (with conf.)   │
                  └───────────┬────────────┘
                              │
        agreement ≥ 0.8?  ────┴──── no ──► back to ROUND r+1 (≤ MAX_ROUNDS)
                              │
                              yes
                              ▼
                   FINAL REPORT (deterministic)
```

The **satisfaction vote** is what guarantees a deterministic, panel-endorsed conclusion.
If the panel never converges within `MAX_DEBATE_ROUNDS`, the supervisor still produces a
final report but explicitly records dissenting opinions and a lower agreement score.

## Specialists

20+ personas across Internal Medicine, Cardiology, Neurology, Pulmonology, GI/Hepatology,
Endocrinology, Hematology, Oncology, Infectious Diseases, Rheumatology, Psychiatry, Urology,
Nephrology, Gynecology, Dermatology, Orthopedics, ENT, Ophthalmology, Allergy/Immunology,
Toxicology, Geriatrics. (`core/specialists.py`)

## Metrics

- **Agreement per round** — % of weighted-confidence "agree" votes.
- **Hypothesis stability** — Jaccard of top-3 diagnoses between consecutive rounds.
- **Evidence citation rate** — fraction of hypotheses that cite specific evidence.
- **Specialist engagement** — words spoken, critiques made, hypotheses produced per specialist.
- **Calibration vs truth** (optional) — top-1 / top-3 / Brier when `--truth` is provided.

## Tuning

Env vars in `.env`:

```
MIN_SPECIALISTS=5
MAX_SPECIALISTS=8
MAX_DEBATE_ROUNDS=4
SATISFACTION_THRESHOLD=0.8
TEMPERATURE=0.3
```

Lower `TEMPERATURE` and a strong model (Opus, GPT-4.1, Gemini 2.5 Pro) for high-stakes runs.
For local Ollama, prefer `qwen2.5:14b` or larger over 7B for better JSON adherence.

## ⚠️ Disclaimer

This is an **AI multi-agent simulation for educational purposes**.
It is **NOT medical advice**. Consult a licensed physician for any health concern.
