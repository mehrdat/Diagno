# ClaudeMed

An AI multi-specialist medical consultation system. A panel of physician agents debates a patient case, challenges each other's hypotheses, and converges on a ranked differential diagnosis with calibrated confidence scores.

It is **not** a replacement for a real doctor. It is a rigorous thinking tool that helps you understand what may be happening, what questions to ask your physician, and what tests to pursue.

---

## How it works

ClaudeMed simulates a clinical case conference. When you submit a case:

1. **A router selects 5–15 specialists** relevant to the presenting complaint from a panel of 35+ physician personas.
2. **Each specialist independently argues** from their domain — producing hypotheses, citing evidence, and critiquing other specialists' reasoning from the previous round.
3. **A supervisor proposes a primary diagnosis** based on the round's arguments.
4. **Each specialist votes** — agree, disagree, or abstain — with a confidence score.
5. If panel agreement is below the threshold (default 0.8), the debate continues for another round.
6. Once consensus is reached (or the round limit hit), a **final report** is generated with a ranked differential, recommended workup, red flags, and treatment notes.

```
[case + evidence]
        │
        ▼
   ROUTER → selects specialists
        │
        ▼
   ROUND r ──────────────────────────────────────────────────┐
   Each specialist: hypotheses + monologue + critiques        │
        │                                                     │
        ▼                                                     │
   SUPERVISOR → proposes primary diagnosis                    │
        │                                                     │
        ▼                                                     │
   Each specialist VOTES (agree / disagree / abstain)         │
        │                                                     │
   agreement ≥ 0.8? ──── no ──────────────────────────────── ┘
        │
       yes
        ▼
   FINAL REPORT (deterministic, panel-endorsed)
```

If the panel never converges within `MAX_DEBATE_ROUNDS`, the supervisor still produces a final report but records dissenting opinions and a lower agreement score.

---

## Two ways to run

ClaudeMed has two interfaces that work independently:

| Interface | Best for |
|-----------|----------|
| **Claude Code skill** (`/claudemed`) | Conversational consults, case tracking, literature review, follow-up management — all inside Claude Code |
| **Python app** (`app.py` / `cli.py`) | Standalone Streamlit UI or scripted batch runs, works with any LLM backend |

---

## Specialist panel

35+ physician personas across all major specialties:

Internal Medicine, Cardiology, Neurology, Pulmonology, Gastroenterology, Endocrinology, Hematology, Oncology, Infectious Disease, Rheumatology, Psychiatry, Urology, Nephrology, Gynecology, Dermatology, Orthopedics, ENT, Ophthalmology, Allergy/Immunology, Toxicology, Geriatrics, Sports Medicine, Pain Medicine, Sleep Medicine, Autonomic Neurology, Emergency Medicine, Vascular Surgery, Radiology, Nuclear Medicine, Genetic Medicine, Clinical Pharmacology, Nutrition & Metabolic Medicine, Physical Medicine & Rehabilitation, Palliative Care, Occupational Medicine.

---

## Installation

### Prerequisites

- Python 3.11+
- At least one of: an Anthropic, OpenAI, or Gemini API key — or [Ollama](https://ollama.com) running locally
- [Claude Code](https://claude.ai/code) (for the `/claudemed` skill interface)

### 1. Clone and install dependencies

```bash
git clone https://github.com/mehrdat/diagno.git
cd diagno
pip install -r requirements.txt
```

### 2. Configure your environment

```bash
cp .env.example .env
```

Open `.env` and fill in your API key and choose a backend:

```env
# Choose one: anthropic | openai | gemini | ollama
LLM_BACKEND=anthropic

ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-opus-4-6

# OPENAI_API_KEY=sk-...
# OPENAI_MODEL=gpt-4.1

# GEMINI_API_KEY=...
# GEMINI_MODEL=gemini-2.5-pro

# For local Ollama:
# LLM_BACKEND=ollama
# OLLAMA_BASE_URL=http://localhost:11434/v1
# OLLAMA_MODEL=qwen2.5:14b
```

### 3. Set up your patient profile

```bash
cp config/patient.example.yml config/patient.yml
```

Edit `config/patient.yml` with your (or the patient's) age, sex, conditions, medications, and allergies. This file is gitignored — it never leaves your machine.

Also create `modes/_profile.md` from the template:

```bash
cp modes/_profile.template.md modes/_profile.md
```

Fill in your medical history. Again, gitignored.

---

## Running the Python app

### Streamlit UI (recommended)

```bash
streamlit run app.py
```

The UI has five tabs:

| Tab | What you see |
|-----|-------------|
| **Debate** | Full transcript per round, critique-network graph, satisfaction votes |
| **Hypotheses** | Line chart of how each diagnosis probability evolved across rounds |
| **Diagnosis** | Primary diagnosis, agreement gauge, differentials bar chart, red flags, recommended workup |
| **Treatment** | Medication cards with dosage, side effects, contraindications, interactions; side-effect heatmap |
| **Metrics** | Agreement per round, hypothesis stability (Jaccard), evidence citation rate, specialist engagement |

### CLI

```bash
# Quick case from a summary string
python cli.py --backend anthropic --summary "47F, 3-month fatigue, 8kg weight loss, night sweats, cervical lymphadenopathy"

# Use a local model
python cli.py --backend ollama --model qwen2.5:14b

# Add ground-truth for calibration metrics
python cli.py --summary "..." --truth "Hodgkin lymphoma"
```

Reports are saved to `reports/report_<timestamp>.json`.

### Dropping in patient data

Place files in `data/intake/`. The loader picks them up by filename stem:

```
data/intake/
├── case.txt               # free-text case summary
├── patient_notes.txt      # history, complaint, timeline
├── blood_test.csv         # lab panels (CSV or plain text)
├── mri_report.txt         # imaging written reports
└── any_file.pdf           # text-extractable PDFs
```

Naming conventions the loader recognises:
- `*note*`, `*history*`, `*complaint*`, `patient.*` → patient history
- `*lab*`, `*blood*`, `*test*`, any `.csv` → lab results
- `*mri*`, `*ct*`, `*xray*`, `*ultrasound*`, `*scan*`, `*imaging*` → imaging reports

---

## Running via Claude Code (`/claudemed`)

If you use [Claude Code](https://claude.ai/code), the skill is already wired up via `CLAUDE.md`. Open the repo in Claude Code and use these commands in the chat:

| Command | What it does |
|---------|-------------|
| `/claudemed <symptoms or file>` | Full consult: specialist debate → differential → report → case tracker |
| `/claudemed diagnosis` | Single-pass evaluation (no multi-round debate) |
| `/claudemed specialist <name>` | Consult one specific specialist |
| `/claudemed differential` | Ranked differential from current data |
| `/claudemed literature` | Search recent medical literature for a condition |
| `/claudemed second-opinion` | Re-evaluate latest case with adversarial counter-arguments |
| `/claudemed tracker` | View full case history and statuses |
| `/claudemed pipeline` | Process queued cases from `data/pipeline.md` |
| `/claudemed batch` | Parallel processing of multiple pending cases |
| `/claudemed patterns` | Pattern analysis across all tracked cases |
| `/claudemed followup` | List pending follow-ups and unresolved cases |
| `/claudemed profile` | View or update patient profile |

On first run, Claude Code will walk you through onboarding if `config/patient.yml` or `modes/_profile.md` are missing.

---

## Configuration / tuning

All debate parameters are set in `.env`:

| Variable | Default | Effect |
|----------|---------|--------|
| `MIN_SPECIALISTS` | 5 | Minimum specialists selected per case |
| `MAX_SPECIALISTS` | 15 | Maximum specialists selected per case |
| `MAX_DEBATE_ROUNDS` | 10 | Maximum rounds before forcing a final report |
| `SATISFACTION_THRESHOLD` | 0.8 | Weighted agreement needed to stop early |
| `TEMPERATURE` | 0.1 | LLM temperature (lower = more deterministic) |

**Tips:**
- For high-stakes or complex cases: use a strong model (Claude Opus, GPT-4.1, Gemini 2.5 Pro) and `TEMPERATURE=0.1`.
- For local Ollama: prefer `qwen2.5:14b` or larger — smaller models struggle with structured JSON output.
- Raise `SATISFACTION_THRESHOLD` to 0.9 if you want more debate before convergence.

---

## Metrics

ClaudeMed tracks the quality of the debate itself:

- **Agreement per round** — weighted fraction of "agree" votes across specialists.
- **Hypothesis stability** — Jaccard similarity of the top-3 diagnoses between consecutive rounds. High stability means the panel has stopped changing its mind.
- **Evidence citation rate** — fraction of specialist arguments that cite specific evidence from the case data.
- **Specialist engagement** — words spoken, critiques made, and hypotheses produced per specialist.
- **Calibration vs. ground truth** — top-1 / top-3 / Brier score when `--truth` is provided via CLI.

---

## Safety

ClaudeMed flags **URGENT** and instructs you to seek emergency care immediately for:

- Chest pain with radiation or diaphoresis
- Stroke symptoms (Face, Arms, Speech, Time)
- Suicidal ideation
- Anaphylaxis
- Severe breathing difficulty
- Neurological emergencies
- Signs of sepsis

On URGENT cases the emergency instruction always appears first, before any analysis.

---

## Data privacy

Your patient data stays local. The `.gitignore` excludes:

- `config/patient.yml` — your patient config
- `modes/_profile.md` — your medical profile
- `data/cases.md`, `data/pipeline.md` — your case history
- `data/intake/*` — all uploaded medical documents
- `reports/*.md` — all generated diagnosis reports
- `.env` — your API keys

Only system files (code, prompts, templates) are tracked in git.

---

## License

MIT — see [LICENSE](LICENSE).

---

> **Disclaimer:** ClaudeMed is an AI simulation for educational and research purposes. It is not a medical device and does not constitute medical advice, diagnosis, or treatment. Always consult a licensed physician for any health concern.
