"""Read everything from data/ and produce a structured evidence dict.

Supports: .txt .md .csv .pdf .png .jpg .jpeg .json
For images, we record the filename and let the user describe them in a sidecar
.txt with the same stem (e.g., chest_xray.png + chest_xray.txt). For PDFs we
extract text. We do NOT attempt OCR or vision here to keep the pipeline simple
and backend-agnostic; vision is a v2 add-on.
"""
from __future__ import annotations
import csv
import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

TEXT_EXT = {".txt", ".md"}
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp"}


def _read_pdf(p: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        return f"[pypdf not installed — cannot read {p.name}]"
    try:
        reader = PdfReader(str(p))
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    except Exception as e:
        return f"[failed to read {p.name}: {e}]"

def _read_csv(p: Path) -> str:
    try:
        with p.open(newline="", encoding="utf-8", errors="replace") as f:
            rows = list(csv.reader(f))
        return "\n".join(", ".join(r) for r in rows[:200])
    except Exception as e:
        return f"[failed to read {p.name}: {e}]"


def load_evidence(data_dir: Path | str | None = None) -> dict:
    d = Path(data_dir) if data_dir else DATA_DIR
    d.mkdir(parents=True, exist_ok=True)

    evidence: dict = {
        "patient_notes": "",
        "lab_results": [],
        "imaging_reports": [],
        "images": [],
        "other_documents": [],
        "files_read": [],
    }

    for p in sorted(d.rglob('*')):
        if p.is_dir() or p.name.startswith("."):
            continue
        ext = p.suffix.lower()
        evidence["files_read"].append(p.name)

        if ext in TEXT_EXT:
            content = p.read_text(encoding="utf-8", errors="replace")
            stem = p.stem.lower()
            if "note" in stem or "history" in stem or "complaint" in stem \
                    or stem in {"patient", "case", "summary"}:
                evidence["patient_notes"] += f"\n\n--- {p.name} ---\n{content}"
            elif "lab" in stem or "blood" in stem or "test" in stem:
                evidence["lab_results"].append({"file": p.name, "content": content})
            elif "mri" in stem or "ct" in stem or "xray" in stem or "x-ray" in stem \
                    or "ultrasound" in stem or "imaging" in stem or "scan" in stem:
                evidence["imaging_reports"].append({"file": p.name, "content": content})
            else:
                evidence["other_documents"].append({"file": p.name, "content": content})

        elif ext == ".pdf":
            text = _read_pdf(p)
            evidence["other_documents"].append({"file": p.name, "content": text})

        elif ext == ".csv":
            text = _read_csv(p)
            evidence["lab_results"].append({"file": p.name, "content": text})

        elif ext == ".json":
            try:
                obj = json.loads(p.read_text(encoding="utf-8", errors="replace"))
                evidence["other_documents"].append({"file": p.name, "content": json.dumps(obj, indent=2)})
            except Exception as e:
                evidence["other_documents"].append({"file": p.name, "content": f"[invalid JSON: {e}]"})

        elif ext in IMAGE_EXT:
            sidecar = p.with_suffix(".txt")
            desc = sidecar.read_text(encoding="utf-8", errors="replace") if sidecar.exists() else ""
            evidence["images"].append({"file": p.name, "description": desc})

    return evidence


def evidence_to_prompt(evidence: dict) -> str:
    """Serialize evidence into a compact, model-readable block."""
    parts = []
    if evidence.get("patient_notes"):
        parts.append("=== PATIENT NOTES / HISTORY ===\n" + evidence["patient_notes"].strip())
    if evidence.get("lab_results"):
        parts.append("=== LAB RESULTS ===")
        for lab in evidence["lab_results"]:
            parts.append(f"-- {lab['file']} --\n{lab['content']}")
    if evidence.get("imaging_reports"):
        parts.append("=== IMAGING REPORTS ===")
        for img in evidence["imaging_reports"]:
            parts.append(f"-- {img['file']} --\n{img['content']}")
    if evidence.get("images"):
        parts.append("=== IMAGE FILES (descriptions only) ===")
        for img in evidence["images"]:
            parts.append(f"- {img['file']}: {img['description'] or '(no description provided)'}")
    if evidence.get("other_documents"):
        parts.append("=== OTHER DOCUMENTS ===")
        for doc in evidence["other_documents"]:
            parts.append(f"-- {doc['file']} --\n{doc['content']}")
    if not parts:
        return "(no evidence found in data/ folder)"
    return "\n\n".join(parts)
