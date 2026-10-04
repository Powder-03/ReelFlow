# Loom Video Walkthrough Script & Recording Guide

**Target Duration**: 5 to 7 Minutes  
**Title**: Multi-Agent Instagram Growth Brain (ReelFlow) Architecture & Live Demo

---

## Video Outline & Screen Flow

```text
[0:00 - 1:00] Introduction & Problem Statement
[1:00 - 2:30] Architecture Walkthrough (LangGraph, Why Multi-Agent, Deterministic Guardrails)
[2:30 - 3:45] Tree of Thoughts (ToT) in Strategy & Writer Agents
[3:45 - 4:45] Calibrated G-Eval Scoring (DeepEval) & Rewrite Loop
[4:45 - 5:45] Live Demo: End-to-End Execution & LangSmith Tracing
[5:45 - 6:45] Live Demo: Dynamic Feedback Loop (How Feedback Changes Next Output)
[6:45 - 7:15] Automated Test Suite & Conclusion
```

---

## Detailed Script & Talking Points

### 1. Introduction (0:00 - 1:00)
* **On Screen**: Open `README.md` or Swagger UI (`http://127.0.0.1:8000/docs`).
* **What to Say**:
  > *"Hello! Today I'm excited to present the prototype for the Multi-Agent Instagram Growth Brain — an autonomous system designed to analyze an Instagram account, identify content opportunities, formulate high-conviction strategies, generate viral Hinglish reel scripts, self-critique using calibrated G-Eval metrics, and continuously learn from audience feedback.*
  >
  > *In this demo, our test account is `@upsc_insider`, an educational creator in the high-stakes UPSC exam preparation niche."*

### 2. Multi-Agent Architecture & Deterministic Guardrails (1:00 - 2:30)
* **On Screen**: Show the Mermaid Architecture Diagram in `README.md` and [`app/agents/graph.py`](file:///c:/Users/risha/Desktop/Insta_help/app/agents/graph.py).
* **What to Say**:
  > *"Why does this problem require a Multi-Agent architecture?*
  > *A single LLM prompt trying to handle strategy, humor, niche nuance, pacing, and evaluation simultaneously suffers from cognitive overload and self-serving bias — an LLM writing a script cannot objectively grade its own work.*
  >
  > *We orchestrated the system using **LangGraph** across 6 specialized agents:*
  > *1. **Intelligence Agent**: Reads upcoming events, trends, and competitor signals.*
  > *2. **Memory Agent**: Analyzes historical top-performing reels and fatigued topics.*
  > *3. **Strategy Agent**: Formulates high-conviction content decisions.*
  > *4. **Writer Agent**: Produces structured 5-part Hinglish scripts with strict pacing.*
  > *5. **Critic Agent**: Employs DeepEval G-Eval metrics with a strict 8.5/10 pass bar.*
  > *6. **Feedback Agent**: Logs performance data and updates memory.*
  >
  > *Crucially, we separate **stochastic LLM reasoning** from **deterministic code**:*
  > *Word counts, cooldown timers, topic fatigue checking, and bounded retry loops are implemented purely in deterministic Python guardrails (`app/guardrails/engine.py`). If the Strategy Agent fails guardrails twice, the system deterministically auto-picks the historically best-performing combination from memory, guaranteeing zero infinite loops and zero wasted tokens."*

### 3. Tree of Thoughts (ToT) Innovation (2:30 - 3:45)
* **On Screen**: Show [`app/agents/strategy.py`](file:///c:/Users/risha/Desktop/Insta_help/app/agents/strategy.py) and [`app/agents/writer.py`](file:///c:/Users/risha/Desktop/Insta_help/app/agents/writer.py).
* **What to Say**:
  > *"To achieve state-of-the-art script quality, we implemented **Tree of Thoughts (ToT)** instead of basic Chain-of-Thought:*
  > *- In the **Strategy Agent**, it branches into 3 divergent hypotheses simultaneously: a high-utility study hack, an emotional reality check, and a high-urgency current affairs debate. Guardrails prune the weaker thoughts and pick the champion.*
  > *- In the **Writer Agent**, it generates 3 competing hooks exploring different psychological triggers (question, shock-stat, personal story). It scores their scroll-stopping power, prunes the weak ones, expands the winning hook into a 5-part body arc, and backtracks any segment that drifts outside the strict 18–23 words limit."*

### 4. Calibrated G-Eval Scoring (3:45 - 4:45)
* **On Screen**: Show [`app/evaluation/scorer.py`](file:///c:/Users/risha/Desktop/Insta_help/app/evaluation/scorer.py) and [`examples/critic_scores_and_revision_history.md`](file:///c:/Users/risha/Desktop/Insta_help/examples/critic_scores_and_revision_history.md).
* **What to Say**:
  > *"Our Critic Agent evaluates scripts across 5 independent quality dimensions: Hook Strength (25%), Emotional Arc (20%), Pacing (20%), Originality (15%), and Strategic Alignment (20%).*
  >
  > *Instead of naive prompts that suffer from marks drift, we use **DeepEval's G-Eval** with locked Chain-of-Thought evaluation steps and token probability scoring.*
  > *All 5 metrics run concurrently in parallel via `asyncio.gather()`, cutting evaluation time from 15 seconds to under 4 seconds.*
  > *Any script scoring below 8.5/10 is automatically sent back to the Writer with surgical critique for up to 3 rewrite rounds."*

### 5. Live Demo: End-to-End Run & LangSmith Tracing (4:45 - 5:45)
* **On Screen**: Terminal running `python run_tot_demo.py`, then switch to **LangSmith Dashboard**.
* **What to Say**:
  > *"Let's run the full end-to-end pipeline live:*
  > *`python run_tot_demo.py`.*
  > *[Wait or show previous output]: Notice how the Strategy Agent selected 'COP31: India's Climate Dilemma', the Writer produced 5 segments with every segment strictly verified in the 18–23 words range, and the Critic scored it an 8.7/10!*
  >
  > *Now look at **LangSmith**: In the Traces tab, notice that instead of fragmented, unparented runs, the entire pipeline is tracked as **ONE unified trace**! Expanding it reveals the full nested waterfall tree — from the LangGraph orchestrator down to each agent and individual Gemini 2.5 Flash LLM call. Under the **Threads** tab, the state is neatly checkpointed under a single persistent conversation thread."*

### 6. Live Demo: Dynamic Feedback Loop (5:45 - 6:45)
* **On Screen**: Terminal running `python demo_feedback_learning.py`.
* **What to Say**:
  > *"A critical requirement of the specification is showing how feedback dynamically changes the next output.*
  > *Let's run `python demo_feedback_learning.py`:*
  > *In Cycle 1, the Strategy Agent proposes a topic based on current trends.*
  > *Then, real-world underperformance feedback is ingested into memory, marking the topic as fatigued in `fatigue_registry.json`.*
  > *In Cycle 2, when the Strategy Agent runs again, it automatically inspects the memory, reads the updated fatigue registry, puts that topic on the strict avoid list, and pivots to a fresh winning topic!*
  > *This demonstrates true closed-loop continuous learning."*

### 7. Automated Tests & Wrap-Up (6:45 - 7:15)
* **On Screen**: Terminal running `pytest tests/ -v`.
* **What to Say**:
  > *"Finally, let's run our test suite: `pytest tests/ -v`.*
  > *All 33 unit and integration tests pass cleanly — covering deterministic guardrails, bounded fallbacks, G-Eval weight calibration, and Tree of Thoughts pruning.*
  >
  > *Thank you for watching, and all code and documentation are ready in the repository!"*
