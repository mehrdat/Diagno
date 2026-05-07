import { useState, useRef, useEffect } from "react";

const SPECIALISTS = [
  { id: "internal", name: "Dr. Karimi", specialty: "Internal Medicine", emoji: "🩺", color: "#2563eb" },
  { id: "cardio", name: "Dr. Vasquez", specialty: "Cardiology", emoji: "❤️", color: "#dc2626" },
  { id: "neuro", name: "Dr. Chen", specialty: "Neurology", emoji: "🧠", color: "#7c3aed" },
  { id: "pulmo", name: "Dr. Okafor", specialty: "Pulmonology", emoji: "🫁", color: "#0891b2" },
  { id: "gastro", name: "Dr. Petrov", specialty: "Gastroenterology/Hepatology", emoji: "🔬", color: "#ca8a04" },
  { id: "endo", name: "Dr. Nakamura", specialty: "Endocrinology (Thyroid)", emoji: "🦋", color: "#9333ea" },
  { id: "hema", name: "Dr. Müller", specialty: "Hematology", emoji: "🩸", color: "#e11d48" },
  { id: "onco", name: "Dr. Sharma", specialty: "Oncology", emoji: "🎗️", color: "#f59e0b" },
  { id: "psych", name: "Dr. Johansson", specialty: "Psychiatry", emoji: "🧩", color: "#6366f1" },
  { id: "uro", name: "Dr. Al-Rashid", specialty: "Urology", emoji: "💧", color: "#0d9488" },
  { id: "gyn", name: "Dr. Mensah", specialty: "Gynecology", emoji: "🌸", color: "#ec4899" },
  { id: "derm", name: "Dr. Tanaka", specialty: "Dermatology", emoji: "🧴", color: "#f97316" },
  { id: "ortho", name: "Dr. Kowalski", specialty: "Orthopedics", emoji: "🦴", color: "#64748b" },
  { id: "ent", name: "Dr. Dubois", specialty: "ENT/Otolaryngology", emoji: "👂", color: "#84cc16" },
  { id: "ophth", name: "Dr. Gupta", specialty: "Ophthalmology", emoji: "👁️", color: "#06b6d4" },
];

const ROUTER_PROMPT = `You are a medical triage router. Given patient symptoms, select the 4-6 most relevant medical specialties from this list that should be consulted. Return ONLY a JSON array of specialty IDs, nothing else. No markdown, no explanation.

Available specialties:
${SPECIALISTS.map(s => `- "${s.id}": ${s.specialty}`).join("\n")}

Patient symptoms: `;

const makeSpecialistPrompt = (spec, symptoms, previousOpinions) => {
  let prompt = `You are ${spec.name}, a senior ${spec.specialty} specialist with 25+ years of experience. You are in a medical assembly with other specialists discussing a patient case.

PATIENT SYMPTOMS: ${symptoms}

Your task:
1. Provide your expert analysis from your specialty's perspective (2-3 sentences)
2. Suggest possible diagnoses relevant to your field
3. Recommend specific tests or examinations
4. If other specialists have already spoken, CHALLENGE or SUPPORT their opinions with specific medical reasoning. Be respectfully critical — point out what they might be missing.

IMPORTANT: Be concise. Be specific. Use medical terminology. Disagree when warranted.`;

  if (previousOpinions.length > 0) {
    prompt += `\n\nPREVIOUS SPECIALIST OPINIONS:\n${previousOpinions.map(o => `[${o.specialty}] ${o.name}: ${o.opinion}`).join("\n\n")}

You MUST reference at least one other specialist's opinion — either to challenge it, support it, or add a critical nuance they missed.`;
  }

  return prompt;
};

const CONSENSUS_PROMPT = (symptoms, allOpinions) => `You are the Chief Medical Officer synthesizing a multi-specialty medical assembly discussion.

PATIENT SYMPTOMS: ${symptoms}

SPECIALIST OPINIONS FROM TWO ROUNDS OF DEBATE:
${allOpinions.map(o => `[${o.specialty}] ${o.name} (Round ${o.round}): ${o.opinion}`).join("\n\n")}

Provide a FINAL CONSENSUS in this exact format:

**PRIMARY DIAGNOSIS:** [most likely diagnosis]
**DIFFERENTIAL DIAGNOSES:** [2-3 alternatives]
**RECOMMENDED TESTS:** [specific tests to confirm]
**TREATMENT PLAN:** [medications with dosages, lifestyle changes]
**SPECIALIST REFERRALS:** [which specialists should follow up]
**POINTS OF DISAGREEMENT:** [where specialists disagreed and how it was resolved]

⚠️ DISCLAIMER: This is an AI simulation for educational purposes only. Always consult real healthcare professionals.`;

const callClaude = async (systemPrompt, userMessage) => {
  try {
    const response = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model: "claude-sonnet-4-20250514",
        max_tokens: 1000,
        system: systemPrompt,
        messages: [{ role: "user", content: userMessage }],
      }),
    });
    const data = await response.json();
    return data.content?.map(b => b.text || "").join("") || "No response";
  } catch (err) {
    return `Error: ${err.message}`;
  }
};

export default function MedicalAssembly() {
  const [symptoms, setSymptoms] = useState("");
  const [messages, setMessages] = useState([]);
  const [phase, setPhase] = useState("idle"); // idle, routing, round1, round2, consensus, done
  const [activeSpecs, setActiveSpecs] = useState([]);
  const [isRunning, setIsRunning] = useState(false);
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages]);

  const addMessage = (msg) => setMessages(prev => [...prev, msg]);

  const runAssembly = async () => {
    if (!symptoms.trim() || isRunning) return;
    setIsRunning(true);
    setMessages([]);
    setPhase("routing");

    addMessage({ type: "system", text: "🏥 Medical Assembly convened. Routing to relevant specialists..." });

    // Route
    const routeResult = await callClaude("You are a medical router.", ROUTER_PROMPT + symptoms);
    let selectedIds;
    try {
      const cleaned = routeResult.replace(/```json|```/g, "").trim();
      selectedIds = JSON.parse(cleaned);
    } catch {
      selectedIds = ["internal", "cardio", "neuro", "pulmo", "gastro"];
    }

    const selected = SPECIALISTS.filter(s => selectedIds.includes(s.id));
    setActiveSpecs(selected);
    addMessage({
      type: "system",
      text: `📋 Specialists called: ${selected.map(s => `${s.emoji} ${s.name} (${s.specialty})`).join(", ")}`,
    });

    const allOpinions = [];

    // Round 1
    setPhase("round1");
    addMessage({ type: "phase", text: "━━━ ROUND 1: Initial Assessments ━━━" });

    for (const spec of selected) {
      addMessage({ type: "thinking", specialist: spec, text: `${spec.name} is analyzing...` });
      const opinion = await callClaude(
        `You are ${spec.name}, ${spec.specialty} specialist.`,
        makeSpecialistPrompt(spec, symptoms, [])
      );
      const entry = { ...spec, opinion, round: 1 };
      allOpinions.push(entry);
      setMessages(prev => prev.filter(m => m.type !== "thinking" || m.specialist?.id !== spec.id));
      addMessage({ type: "opinion", specialist: spec, text: opinion, round: 1 });
    }

    // Round 2 — Debate
    setPhase("round2");
    addMessage({ type: "phase", text: "━━━ ROUND 2: Challenges & Debate ━━━" });

    for (const spec of selected) {
      addMessage({ type: "thinking", specialist: spec, text: `${spec.name} is reviewing colleagues' opinions...` });
      const prevOps = allOpinions
        .filter(o => o.id !== spec.id && o.round === 1)
        .map(o => ({ specialty: o.specialty, name: o.name, opinion: o.opinion }));

      const opinion = await callClaude(
        `You are ${spec.name}, ${spec.specialty} specialist. This is round 2 — you must challenge or build on others' opinions.`,
        makeSpecialistPrompt(spec, symptoms, prevOps)
      );
      const entry = { ...spec, opinion, round: 2 };
      allOpinions.push(entry);
      setMessages(prev => prev.filter(m => m.type !== "thinking" || m.specialist?.id !== spec.id));
      addMessage({ type: "opinion", specialist: spec, text: opinion, round: 2 });
    }

    // Consensus
    setPhase("consensus");
    addMessage({ type: "phase", text: "━━━ FINAL CONSENSUS ━━━" });
    addMessage({ type: "system", text: "⚖️ Chief Medical Officer synthesizing all opinions..." });

    const consensus = await callClaude(
      "You are the Chief Medical Officer of a hospital.",
      CONSENSUS_PROMPT(symptoms, allOpinions)
    );
    addMessage({ type: "consensus", text: consensus });

    setPhase("done");
    setIsRunning(false);
  };

  return (
    <div style={{
      minHeight: "100vh",
      background: "#0a0f1a",
      color: "#e2e8f0",
      fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
    }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;600;700&family=Playfair+Display:wght@700;900&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: #1a1f2e; }
        ::-webkit-scrollbar-thumb { background: #334155; border-radius: 3px; }
        @keyframes pulse { 0%,100% { opacity: 0.4; } 50% { opacity: 1; } }
        @keyframes slideIn { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }
        .msg-enter { animation: slideIn 0.3s ease-out; }
      `}</style>

      {/* Header */}
      <div style={{
        padding: "24px 32px",
        borderBottom: "1px solid #1e293b",
        background: "linear-gradient(135deg, #0a0f1a 0%, #1a1033 100%)",
      }}>
        <h1 style={{
          fontFamily: "'Playfair Display', serif",
          fontSize: "28px",
          fontWeight: 900,
          background: "linear-gradient(135deg, #60a5fa, #a78bfa, #f472b6)",
          WebkitBackgroundClip: "text",
          WebkitTextFillColor: "transparent",
          letterSpacing: "-0.5px",
        }}>
          Medical Assembly AI
        </h1>
        <p style={{ color: "#64748b", fontSize: "12px", marginTop: "4px", letterSpacing: "2px", textTransform: "uppercase" }}>
          Multi-Specialist Diagnostic Panel • Powered by Claude
        </p>
      </div>

      <div style={{ display: "flex", height: "calc(100vh - 90px)" }}>
        {/* Sidebar — Active Specialists */}
        <div style={{
          width: "220px",
          borderRight: "1px solid #1e293b",
          padding: "16px",
          overflowY: "auto",
          flexShrink: 0,
        }}>
          <p style={{ fontSize: "10px", color: "#64748b", letterSpacing: "2px", textTransform: "uppercase", marginBottom: "12px" }}>
            {activeSpecs.length > 0 ? "Active Panel" : "All Specialties"}
          </p>
          {(activeSpecs.length > 0 ? activeSpecs : SPECIALISTS).map(s => (
            <div key={s.id} style={{
              padding: "8px 10px",
              marginBottom: "4px",
              borderRadius: "6px",
              background: activeSpecs.find(a => a.id === s.id) ? `${s.color}15` : "transparent",
              borderLeft: `3px solid ${activeSpecs.find(a => a.id === s.id) ? s.color : "transparent"}`,
              transition: "all 0.2s",
            }}>
              <span style={{ fontSize: "13px" }}>{s.emoji} {s.name}</span>
              <p style={{ fontSize: "10px", color: "#64748b", marginTop: "2px" }}>{s.specialty}</p>
            </div>
          ))}
        </div>

        {/* Main Panel */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column" }}>
          {/* Messages */}
          <div ref={scrollRef} style={{ flex: 1, overflowY: "auto", padding: "20px 24px" }}>
            {messages.length === 0 && (
              <div style={{ textAlign: "center", marginTop: "120px", color: "#475569" }}>
                <p style={{ fontSize: "48px", marginBottom: "16px" }}>🏥</p>
                <p style={{ fontSize: "14px" }}>Describe your symptoms to convene the medical assembly</p>
                <p style={{ fontSize: "11px", marginTop: "8px", color: "#334155" }}>
                  Specialists will debate, challenge each other, and reach a consensus diagnosis
                </p>
              </div>
            )}

            {messages.map((msg, i) => (
              <div key={i} className="msg-enter" style={{ marginBottom: "12px" }}>
                {msg.type === "system" && (
                  <div style={{
                    padding: "10px 14px",
                    background: "#1e293b",
                    borderRadius: "8px",
                    fontSize: "13px",
                    color: "#94a3b8",
                    borderLeft: "3px solid #3b82f6",
                  }}>{msg.text}</div>
                )}
                {msg.type === "phase" && (
                  <div style={{
                    textAlign: "center",
                    padding: "12px",
                    margin: "16px 0",
                    fontSize: "13px",
                    fontWeight: 700,
                    color: "#a78bfa",
                    letterSpacing: "2px",
                  }}>{msg.text}</div>
                )}
                {msg.type === "thinking" && (
                  <div style={{
                    padding: "10px 14px",
                    background: `${msg.specialist.color}10`,
                    borderRadius: "8px",
                    fontSize: "12px",
                    color: msg.specialist.color,
                    animation: "pulse 1.5s infinite",
                    borderLeft: `3px solid ${msg.specialist.color}`,
                  }}>
                    {msg.specialist.emoji} {msg.text}
                  </div>
                )}
                {msg.type === "opinion" && (
                  <div style={{
                    padding: "14px 16px",
                    background: "#111827",
                    borderRadius: "10px",
                    borderLeft: `4px solid ${msg.specialist.color}`,
                  }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                      <span style={{ fontSize: "13px", fontWeight: 700, color: msg.specialist.color }}>
                        {msg.specialist.emoji} {msg.specialist.name} — {msg.specialist.specialty}
                      </span>
                      <span style={{
                        fontSize: "10px",
                        padding: "2px 8px",
                        borderRadius: "10px",
                        background: msg.round === 2 ? "#7c3aed20" : "#1e293b",
                        color: msg.round === 2 ? "#a78bfa" : "#64748b",
                      }}>
                        {msg.round === 1 ? "Assessment" : "Debate"}
                      </span>
                    </div>
                    <p style={{ fontSize: "13px", lineHeight: "1.7", color: "#cbd5e1", whiteSpace: "pre-wrap" }}>{msg.text}</p>
                  </div>
                )}
                {msg.type === "consensus" && (
                  <div style={{
                    padding: "20px",
                    background: "linear-gradient(135deg, #1a1033, #0f172a)",
                    borderRadius: "12px",
                    border: "1px solid #7c3aed40",
                  }}>
                    <p style={{ fontSize: "14px", fontWeight: 700, color: "#a78bfa", marginBottom: "12px" }}>
                      ⚖️ CHIEF MEDICAL OFFICER — FINAL CONSENSUS
                    </p>
                    <p style={{ fontSize: "13px", lineHeight: "1.8", color: "#e2e8f0", whiteSpace: "pre-wrap" }}>{msg.text}</p>
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Input */}
          <div style={{
            padding: "16px 24px",
            borderTop: "1px solid #1e293b",
            background: "#0d1117",
          }}>
            <div style={{ display: "flex", gap: "10px" }}>
              <textarea
                value={symptoms}
                onChange={e => setSymptoms(e.target.value)}
                placeholder="Describe symptoms... (e.g., persistent fatigue, unexplained weight loss, night sweats, enlarged lymph nodes)"
                disabled={isRunning}
                onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); runAssembly(); } }}
                style={{
                  flex: 1,
                  padding: "12px 14px",
                  background: "#1e293b",
                  border: "1px solid #334155",
                  borderRadius: "8px",
                  color: "#e2e8f0",
                  fontSize: "13px",
                  fontFamily: "inherit",
                  resize: "none",
                  height: "48px",
                  outline: "none",
                }}
              />
              <button
                onClick={runAssembly}
                disabled={isRunning || !symptoms.trim()}
                style={{
                  padding: "12px 24px",
                  background: isRunning ? "#334155" : "linear-gradient(135deg, #3b82f6, #7c3aed)",
                  border: "none",
                  borderRadius: "8px",
                  color: "#fff",
                  fontSize: "13px",
                  fontWeight: 700,
                  fontFamily: "inherit",
                  cursor: isRunning ? "not-allowed" : "pointer",
                  whiteSpace: "nowrap",
                  letterSpacing: "1px",
                }}
              >
                {isRunning ? "ASSEMBLING..." : "CONVENE"}
              </button>
            </div>
            <p style={{ fontSize: "10px", color: "#475569", marginTop: "8px", textAlign: "center" }}>
              ⚠️ AI simulation for educational purposes only — not medical advice. Always consult real healthcare professionals.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
