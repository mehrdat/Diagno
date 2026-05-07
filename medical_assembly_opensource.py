"""
Medical Assembly Agent — Open Source Version
Uses LangGraph + Ollama (or any OpenAI-compatible local server)
Models: BioMistral-7B, Meditron, Qwen2.5-7B, or any local model via Ollama

Setup:
  pip install langgraph langchain-openai pydantic
  ollama pull qwen2.5:7b  (or biomistral, meditron, etc.)

Architecture:
  Router → Specialist Nodes → Debate Loop (2 rounds) → Consensus Node
"""

import json
import operator
from typing import Annotated, TypedDict
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END

# ━━━ CONFIG ━━━
OLLAMA_BASE = "http://localhost:11434/v1"
MODEL = "qwen3:1.7b"  # Change to biomistral, meditron-7b, etc.
DEBATE_ROUNDS = 2

# ━━━ SPECIALISTS ━━━
SPECIALISTS = {
    "internal": {"name": "Dr. Ousghol", "specialty": "Internal Medicine"},
    "cardio": {"name": "Dr. Lashgari", "specialty": "Cardiology"},
    "neuro": {"name": "Dr. Mohammadi", "specialty": "Neurology"},
    "pulmo": {"name": "Dr. Bayat", "specialty": "Pulmonology"},
    "gastro": {"name": "Dr. Daei", "specialty": "Gastroenterology/Hepatology"},
    "endo": {"name": "Dr. Saeedi", "specialty": "Endocrinology (Thyroid)"},
    "hema": {"name": "Dr. Jahangiri", "specialty": "Hematology"},
    "onco": {"name": "Dr. Norouzi", "specialty": "Oncology"},
    "psych": {"name": "Dr. Daei", "specialty": "Psychiatry"},
    "uro": {"name": "Dr. Nasiri", "specialty": "Urology"},
    "gyn": {"name": "Dr. Shombooli", "specialty": "Gynecology"},
    "derm": {"name": "Dr. PoostAndaz", "specialty": "Dermatology"},
    "ortho": {"name": "Dr. ShekasteBand", "specialty": "Orthopedics"},
    "ent": {"name": "Dr. MamGholi", "specialty": "ENT/Otolaryngology"},
    "ophth": {"name": "Dr. EynakSaz", "specialty": "Ophthalmology"},
}


# ━━━ STATE ━━━
class AssemblyState(TypedDict):
    symptoms: str
    selected_specialists: list[str]
    opinions: Annotated[list[dict], operator.add]  # Append-only
    current_round: int
    consensus: str


# ━━━ LLM ━━━
def get_llm(temperature=0.1):
    return ChatOpenAI(
        base_url=OLLAMA_BASE,
        model=MODEL,
        temperature=temperature,
        api_key="ollama",
        timeout=600,
    )



# ━━━ NODES ━━━
def route_specialists(state: AssemblyState) -> AssemblyState:
    """Select relevant specialists based on symptoms."""
    llm = get_llm(temperature=0)
    prompt = f"""You are a medical triage router. Given these symptoms, select the 4-10 most 
            relevant specialty IDs from: {list(SPECIALISTS.keys())}

            Symptoms or data from the patient or just one or more questions \n: {state["symptoms"]}

            Return ONLY a JSON array of IDs like ["internal", "cardio"]. Nothing else."""

    response = llm.invoke(prompt)
    try:
        ids = json.loads(response.content.strip().strip("`").replace("json", ""))
        ids = [i for i in ids if i in SPECIALISTS]
    except Exception:
        ids = ["internal", "cardio", "neuro", "pulmo", "gastro"]

    print(f"\n🏥 Specialists selected: {[SPECIALISTS[i]['name'] for i in ids]}\n")
    return {"selected_specialists": ids, "current_round": 1}


def run_specialist_round(state: AssemblyState) -> AssemblyState:
    """Each specialist gives their opinion, challenging others in round 2+."""
    
    llm = get_llm()
    round_num = state["current_round"]
    new_opinions = []

    prior = [o for o in state["opinions"] if o["round"] < round_num]

    for spec_id in state["selected_specialists"]:
        spec = SPECIALISTS[spec_id]
        prior_text = ""
        if prior:
            prior_text = "\n\nOther specialists said:\n" + "\n".join(
                f"[{o['specialty']}] {o['name']}: {o['opinion']}" for o in prior
            )
            prior_text += "\n\nYou MUST challenge or support at least one colleague's opinion."

        prompt = f"""You are {spec['name']}, a senior {spec['specialty']} specialist.

PATIENT SYMPTOMS: {state['symptoms']}
{prior_text}

Provide your analysis (2-3 sentences), possible diagnoses, and recommended tests.
Be specific. Use medical terminology. Disagree with colleagues when warranted."""

        print(f"  {'🔬' if round_num > 1 else '🩺'} {spec['name']} ({spec['specialty']}) — Round {round_num}...")
        response = llm.invoke(prompt)

        opinion = {
            "id": spec_id,
            "name": spec["name"],
            "specialty": spec["specialty"],
            "opinion": response.content.strip(),
            "round": round_num,
        }
        new_opinions.append(opinion)
        print(f"    └─ {response.content.strip()}\n")

    return {"opinions": new_opinions, "current_round": round_num + 1}


def build_consensus(state: AssemblyState) -> AssemblyState:
    """Chief Medical Officer synthesizes all opinions into a final diagnosis."""
    llm = get_llm(temperature=0.2)

    all_opinions = "\n\n".join(
        f"[Round {o['round']}] {o['name']} ({o['specialty']}): {o['opinion']}"
        for o in state["opinions"]
    )

    prompt = f"""You are the Chief Medical Officer. Synthesize this multi-specialty discussion.

SYMPTOMS: {state['symptoms']}

SPECIALIST OPINIONS:
{all_opinions}

Provide your FINAL CONSENSUS:
- PRIMARY DIAGNOSIS
- DIFFERENTIAL DIAGNOSES (2-3)
- RECOMMENDED TESTS
- TREATMENT PLAN (medications + dosages)
- SPECIALIST REFERRALS
- KEY DISAGREEMENTS and how resolved

⚠️ Add disclaimer: AI simulation, not medical advice."""

    print("\n⚖️ Chief Medical Officer building consensus...\n")
    response = llm.invoke(prompt)
    return {"consensus": response.content.strip()}


def should_continue(state: AssemblyState) -> str:
    """Decide: another debate round or go to consensus."""
    if state["current_round"] <= DEBATE_ROUNDS:
        return "debate"
    return "consensus"


# ━━━ BUILD GRAPH ━━━
def build_assembly_graph():
    graph = StateGraph(AssemblyState)

    graph.add_node("route", route_specialists)
    graph.add_node("specialist_round", run_specialist_round)
    graph.add_node("consensus", build_consensus)

    graph.set_entry_point("route")
    graph.add_edge("route", "specialist_round")
    graph.add_conditional_edges(
        "specialist_round",
        should_continue,
        {"debate": "specialist_round", "consensus": "consensus"},
    )
    graph.add_edge("consensus", END)

    return graph.compile()


# ━━━ RUN ━━━
def run_medical_assembly(symptoms: str) -> str:
    app = build_assembly_graph()
    result = app.invoke({
        "symptoms": symptoms,
        "selected_specialists": [],
        "opinions": [],
        "current_round": 0,
        "consensus": "",
    })
    return result["consensus"]


# ━━━ ALTERNATIVE: CrewAI VERSION (even simpler) ━━━
CREWAI_EXAMPLE = """
# pip install crewai crewai-tools
from crewai import Agent, Task, Crew, Process

# Create specialist agents
internist = Agent(
    role="Internal Medicine Specialist",
    goal="Diagnose from an internal medicine perspective",
    backstory="25 years experience in internal medicine...",
    llm="ollama/qwen2.5:7b",  # or any model
    allow_delegation=True,
)

cardiologist = Agent(
    role="Cardiologist", 
    goal="Evaluate cardiac implications",
    backstory="Senior cardiologist, critical thinker...",
    llm="ollama/qwen2.5:7b",
    allow_delegation=True,
)

# ... add more specialists

consensus_officer = Agent(
    role="Chief Medical Officer",
    goal="Build consensus diagnosis from all specialist opinions",
    llm="ollama/qwen2.5:7b",
)

# Create tasks
diagnose = Task(
    description="Analyze symptoms: {symptoms}. Challenge other specialists.",
    expected_output="Diagnosis, tests, medications",
    agent=internist,
)

# Crew with hierarchical process
crew = Crew(
    agents=[internist, cardiologist, consensus_officer],
    tasks=[diagnose],
    process=Process.hierarchical,
    manager_agent=consensus_officer,
)

result = crew.kickoff(inputs={"symptoms": "persistent fatigue, weight loss"})
"""


# ━━━ AUTOGEN ALTERNATIVE ━━━
AUTOGEN_EXAMPLE = """
# pip install autogen-agentchat
import autogen

config = {"model": "qwen2.5:7b", "base_url": "http://localhost:11434/v1", "api_key": "ollama"}

internist = autogen.AssistantAgent("Internist", system_message="You are an internal medicine specialist...", llm_config={"config_list": [config]})
cardiologist = autogen.AssistantAgent("Cardiologist", system_message="You are a cardiologist...", llm_config={"config_list": [config]})
neurologist = autogen.AssistantAgent("Neurologist", system_message="You are a neurologist...", llm_config={"config_list": [config]})

# GroupChat enables multi-agent debate
groupchat = autogen.GroupChat(
    agents=[internist, cardiologist, neurologist],
    messages=[],
    max_round=6,  # 2 rounds x 3 agents
    speaker_selection_method="round_robin",
)

manager = autogen.GroupChatManager(groupchat=groupchat, llm_config={"config_list": [config]})
internist.initiate_chat(manager, message="Patient symptoms: persistent fatigue, weight loss, night sweats")
"""


if __name__ == "__main__":
    print("=" * 60)
    print("  MEDICAL ASSEMBLY — Open Source Multi-Agent System")
    print("=" * 60)

    symptoms = input("\nDescribe symptoms: ").strip()
    if not symptoms:
        symptoms = "Persistent fatigue for 3 months, unexplained weight loss of 8kg, night sweats, enlarged cervical lymph nodes, mild fever"
        print(f"Using example: {symptoms}")

    consensus = run_medical_assembly(symptoms)

    print("\n" + "=" * 60)
    print("  FINAL CONSENSUS")
    print("=" * 60)
    print(consensus)
    print("\n⚠️  This is an AI simulation — not medical advice.")
