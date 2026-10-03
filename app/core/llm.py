from langchain_google_genai import ChatGoogleGenerativeAI
from deepeval.models import GeminiModel
from app.core.config import settings

def get_llm(temperature: float = 0.7) -> ChatGoogleGenerativeAI:
    """LangChain-compatible LLM for agent generation."""
    return ChatGoogleGenerativeAI(
        model=settings.GEMINI_MODEL,
        project=settings.GOOGLE_CLOUD_PROJECT,
        location=settings.GOOGLE_CLOUD_LOCATION,
        temperature=temperature,
    )

def get_eval_model() -> GeminiModel:
    """DeepEval-compatible model for G-Eval scoring.
    Temperature=0 for maximum scoring consistency and reproducibility."""
    return GeminiModel(
        model=settings.GEMINI_MODEL,
        project=settings.GOOGLE_CLOUD_PROJECT,
        location=settings.GOOGLE_CLOUD_LOCATION,
        use_vertexai=True,
        temperature=0.0,
    )
