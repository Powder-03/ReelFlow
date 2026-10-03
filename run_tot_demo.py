import sys
import asyncio

# Ensure UTF-8 output on Windows terminal
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from app.agents.state import AgentState
from app.agents.intelligence import intelligence_node
from app.agents.memory import memory_node
from app.agents.strategy import strategy_node
from app.agents.guardrails_node import guardrails_node
from app.agents.writer import writer_node

async def run_tot_demo():
    print("=" * 65)
    print("      TREE OF THOUGHTS (ToT) MULTI-AGENT EXECUTION DEMO        ")
    print("=" * 65)
    state: AgentState = {
        "account_handle": "@upsc_insider",
        "content_request": "Prelims CSAT Maths vs Reading Comprehension strategy",
        "guardrail_retry_count": 0,
        "rewrite_count": 0,
        "needs_human_review": False,
    }
    
    print("[Step 1] Running Intelligence Agent...")
    state.update(await intelligence_node(state))

    print("[Step 2] Running Memory Agent...")
    state.update(await memory_node(state))

    print("[Step 3] Running Strategy Agent (ToT: 3 Hypotheses Exploration & Pruning)...")
    state.update(await strategy_node(state))
    strat = state["strategy"]
    print(f"  * Selected Champion Topic: {strat['topic']}")
    print(f"  * Content Bucket: {strat['content_bucket']} | Hook Style: {strat['hook_style']}")
    print(f"  * Rationale: {strat['reasoning'][:120]}...")

    print("\n[Step 4] Running Guardrails Check...")
    state.update(await guardrails_node(state))
    print(f"  * Guardrail Passed: {state['guardrail_result']['passed']}")

    print("\n[Step 5] Running Writer Agent (ToT: Hook Tree -> Pruning -> Arc Expansion -> Backtrack)...")
    state.update(await writer_node(state))
    script = state["current_script"]
    print(f"  * Script Title: {script['title']}")
    print(f"  * Champion Hook: \"{script['hook']}\" ({len(script['hook'].split())} words)")
    print("\n  Script Segments Breakdown:")
    for seg in script["segments"]:
        words = len(seg["text"].split())
        print(f"     [{seg['type'].upper()}] ({words} words): {seg['text']}")
        print(f"         Visual: {seg['visual_cue']}")

    print("\n" + "=" * 65)
    print("  [SUCCESS] Tree of Thoughts generated high-discipline reel script!")
    print("=" * 65)

if __name__ == "__main__":
    asyncio.run(run_tot_demo())
