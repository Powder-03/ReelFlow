import sys
import uuid
import asyncio
from langsmith import traceable

# Ensure UTF-8 output on Windows terminal
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from app.agents.state import AgentState
from app.agents.graph import build_growth_brain_graph

graph = build_growth_brain_graph()

@traceable(
    name="ReelFlow End-to-End Pipeline (ToT)",
    run_type="chain",
    tags=["tot-demo", "reel-flow", "upsc"],
    metadata={"account_handle": "@upsc_insider", "framework": "langgraph"},
)
async def run_tot_demo():
    print("=" * 70)
    print("    TREE OF THOUGHTS (ToT) END-TO-END MULTI-AGENT EXECUTION DEMO    ")
    print("=" * 70)
    
    thread_id = f"tot-demo-{uuid.uuid4().hex[:8]}"
    print(f"[*] Thread ID: {thread_id} (Tracking in LangSmith Threads)")
    
    state: AgentState = {
        "account_handle": "@upsc_insider",
        "content_request": "Prelims CSAT Maths vs Reading Comprehension strategy",
        "guardrail_retry_count": 0,
        "rewrite_count": 0,
        "max_rewrites": 3,
        "needs_human_review": False,
        "all_evaluations": [],
    }

    config = {
        "configurable": {"thread_id": thread_id},
        "run_name": "ReelFlow Graph Orchestrator",
        "tags": ["reel-flow", "upsc", "@upsc_insider"],
    }

    print("\n[>>] Starting LangGraph multi-agent pipeline...")
    final_state = await graph.ainvoke(state, config=config)

    # 1. Strategy Results
    strat = final_state.get("strategy", {})
    print("\n" + "-" * 70)
    print(" [1] STRATEGY AGENT (ToT Champion Selected)")
    print("-" * 70)
    print(f"  * Topic         : {strat.get('topic')}")
    print(f"  * Content Bucket: {strat.get('content_bucket')} | Hook Style: {strat.get('hook_style')}")
    print(f"  * Tone          : {strat.get('tone')} | Format: {strat.get('format')}")
    print(f"  * Reasoning     : {strat.get('reasoning', '')[:140]}...")

    # 2. Guardrails Results
    gr = final_state.get("guardrail_result", {})
    print("\n" + "-" * 70)
    print(" [2] DETERMINISTIC GUARDRAILS")
    print("-" * 70)
    print(f"  * Guardrail Passed : {gr.get('passed')}")
    print(f"  * Violations       : {gr.get('violations', [])}")
    if gr.get("auto_picked"):
        print(f"  * Auto-Pick Fallback: Activated ({gr.get('auto_pick_reason')})")

    # 3. Writer Results
    script = final_state.get("approved_script") or final_state.get("best_script") or final_state.get("current_script")
    print("\n" + "-" * 70)
    print(" [3] WRITER AGENT (ToT Champion Script)")
    print("-" * 70)
    if script:
        hook_text = script.get("hook", "")
        print(f"  * Title        : {script.get('title')}")
        print(f"  * Champion Hook: \"{hook_text}\" ({len(hook_text.split())} words)")
        print("\n  Segment Breakdown (Target 18-23 words per segment):")
        for seg in script.get("segments", []):
            words = len(seg.get("text", "").split())
            status = "OK" if 18 <= words <= 23 else f"ADJUST ({words} words)"
            print(f"    [{seg.get('type', '').upper():<14}] ({status:<16}): {seg.get('text')}")
            print(f"      Visual: {seg.get('visual_cue')}")
        print(f"  * CTA: {script.get('cta')}")

    # 4. Critic Evaluation Results
    evaluation = final_state.get("evaluation")
    print("\n" + "-" * 70)
    print(" [4] CRITIC EVALUATION (Calibrated G-Eval)")
    print("-" * 70)
    if evaluation:
        overall_10 = evaluation.get("overall_score_10", evaluation.get("overall_score", 0) * 10)
        passed = evaluation.get("pass_threshold", False)
        print(f"  * Calibrated Score : {overall_10:.1f} / 10 (Internal: {evaluation.get('overall_score', 0):.2f})")
        print(f"  * Quality Status   : {'PASSED (>= 8.5/10)' if passed else 'REWRITTEN / REVIEW'}")
        print(f"  * Rewrites Done    : {final_state.get('rewrite_count', 0)}")
        print("  * Metric Breakdown :")
        for m, score in evaluation.get("metrics", {}).items():
            print(f"      - {m:<28}: {score * 10:.1f}/10")
        print(f"  * Reasoning        : {evaluation.get('reasoning', '')[:140]}...")

    print("\n" + "=" * 70)
    print("  [SUCCESS] End-to-end execution completed under unified thread & trace!")
    print(f"  LangSmith Project: Reel | Thread ID: {thread_id}")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(run_tot_demo())
