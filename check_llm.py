import os
import sys
import time
import asyncio
from dotenv import load_dotenv

# Ensure UTF-8 output on Windows terminal
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Load local environment variables from .env
load_dotenv()

from app.core.config import settings, is_valid_langsmith_key
from app.core.llm import get_llm, get_eval_model

def print_banner():
    print("=" * 70)
    print("       GEMINI 2.5 FLASH & LANGSMITH OBSERVABILITY TEST         ")
    print("=" * 70)
    print(f"  * GCP Project      : {settings.GOOGLE_CLOUD_PROJECT}")
    print(f"  * Location         : {settings.GOOGLE_CLOUD_LOCATION}")
    print(f"  * Gemini Model     : {settings.GEMINI_MODEL}")
    print(f"  * LangSmith Tracing: {settings.LANGSMITH_TRACING}")
    print(f"  * LangSmith Project: {settings.LANGSMITH_PROJECT}")
    key_status = "Configured" if is_valid_langsmith_key else "Not set (paste into .env)"
    print(f"  * LangSmith API Key: {key_status}")
    print("=" * 70)
    print()

async def test_agent_llm():
    print("[1/3] Testing LangChain Gemini (Used by Generation Agents)...")
    try:
        llm = get_llm(temperature=0.7)
        prompt = (
            "You are testing the Multi-Agent Instagram Brain. "
            "Write a 1-sentence viral hook for a UPSC reel about CSAT in Hinglish."
        )
        
        t0 = time.perf_counter()
        response = await llm.ainvoke(prompt)
        elapsed = (time.perf_counter() - t0) * 1000

        print(f"  [SUCCESS] ({elapsed:.0f} ms)")
        print(f"  Response: \"{response.content.strip()}\"")
        return True
    except Exception as e:
        print(f"  [FAILED]: {e}")
        return False

def test_eval_model():
    print("\n[2/3] Testing DeepEval GeminiModel (Used by G-Eval Critic)...")
    try:
        eval_model = get_eval_model()
        test_prompt = "Say 'Evaluator online' in exactly two words."

        t0 = time.perf_counter()
        res, cost = eval_model.generate(test_prompt)
        elapsed = (time.perf_counter() - t0) * 1000

        print(f"  [SUCCESS] ({elapsed:.0f} ms)")
        print(f"  Response: \"{res.strip()}\"")
        return True
    except Exception as e:
        print(f"  [FAILED]: {e}")
        return False

def test_langsmith_connection():
    print("\n[3/3] Testing LangSmith Project Connection...")
    if not is_valid_langsmith_key:
        print("  [ACTION NEEDED] LANGSMITH_API_KEY is not set in .env yet.")
        print(f"  👉 Open .env and set: LANGSMITH_API_KEY=lsv2_pt_your_actual_key")
        print(f"     Target Project: '{settings.LANGSMITH_PROJECT}'")
        print("     Once added, all LangGraph multi-agent runs will stream traces automatically!")
        return None

    try:
        from langsmith import Client
        client = Client(api_key=settings.LANGSMITH_API_KEY, api_url=settings.LANGSMITH_ENDPOINT)
        
        project_name = settings.LANGSMITH_PROJECT
        try:
            project = client.read_project(project_name=project_name)
            print(f"  [SUCCESS] Connected to LangSmith project: '{project_name}' (ID: {project.id})")
        except Exception:
            project = client.create_project(project_name=project_name)
            print(f"  [SUCCESS] Verified/Created LangSmith project: '{project_name}' (ID: {project.id})")

        print(f"            Dashboard URL: https://smith.langchain.com/o/default/projects/p/{project.id}")
        return True
    except Exception as e:
        print(f"  [FAILED] LangSmith connection error: {e}")
        return False

async def main():
    print_banner()
    agent_ok = await test_agent_llm()
    eval_ok = test_eval_model()
    ls_ok = test_langsmith_connection()

    print("\n" + "=" * 70)
    if agent_ok and eval_ok:
        if ls_ok is True:
            print("  [STATUS] ALL SYSTEMS OPERATIONAL: Gemini & LangSmith 'Reel' are live!")
        elif ls_ok is None:
            print("  [STATUS] Gemini is live! Add your LANGSMITH_API_KEY to .env to view traces.")
        else:
            print("  [STATUS] Gemini is live, but check LangSmith API key.")
    else:
        print("  [STATUS] ATTENTION: Some LLM checks failed.")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(main())
