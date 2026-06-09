from abc import ABC, abstractmethod
from typing import List, Optional
import httpx

from src.utils.config import settings


class BaseLLMProvider(ABC):
    """
    Abstract Base class for LLM & Embedding provider operations.
    """
    @abstractmethod
    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generates a vector embedding for the given input text.
        """
        pass

    @abstractmethod
    async def generate_response(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        """
        Generates a text completion for the given prompt, applying optional system instructions.
        """
        pass


class GeminiProvider(BaseLLMProvider):
    """
    Concrete implementation using Google Gemini API.
    """
    def __init__(self):
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is not configured in settings.")
        import google.generativeai as genai
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.genai = genai

    async def generate_embedding(self, text: str) -> List[float]:
        # gemini-embedding-2 is the recommended embedding model
        # Using a run_in_executor to avoid blocking the main thread since google-generativeai is synchronous
        import asyncio
        loop = asyncio.get_running_loop()
        
        def _call_embed():
            result = self.genai.embed_content(
                model="models/gemini-embedding-2",
                content=text,
                task_type="retrieval_document"
            )
            return result["embedding"]
            
        return await loop.run_in_executor(None, _call_embed)

    async def generate_response(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        import asyncio
        loop = asyncio.get_running_loop()

        def _call_generate():
            # Using gemini-2.5-flash-lite as default high-speed, cost-effective LLM
            model = self.genai.GenerativeModel(
                model_name="gemini-2.5-flash-lite",
                system_instruction=system_instruction
            )
            config = {"temperature": 0.2}
            result = model.generate_content(prompt, generation_config=config)
            return result.text

        return await loop.run_in_executor(None, _call_generate)


class OpenAIProvider(BaseLLMProvider):
    """
    Concrete implementation using OpenAI API.
    """
    def __init__(self):
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is not configured in settings.")
        from openai import OpenAI
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)

    async def generate_embedding(self, text: str) -> List[float]:
        import asyncio
        loop = asyncio.get_running_loop()

        def _call_embed():
            response = self.client.embeddings.create(
                input=[text],
                model="text-embedding-3-small"
            )
            return response.data[0].embedding

        return await loop.run_in_executor(None, _call_embed)

    async def generate_response(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        import asyncio
        loop = asyncio.get_running_loop()

        def _call_generate():
            messages = []
            if system_instruction:
                messages.append({"role": "system", "content": system_instruction})
            messages.append({"role": "user", "content": prompt})

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.2
            )
            return response.choices[0].message.content or ""

        return await loop.run_in_executor(None, _call_generate)


class OllamaProvider(BaseLLMProvider):
    """
    Concrete implementation using local Ollama instance.
    """
    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL.rstrip('/')
        self.model = settings.OLLAMA_MODEL
        self.embed_model = settings.OLLAMA_EMBED_MODEL

    async def generate_embedding(self, text: str) -> List[float]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/api/embeddings",
                json={
                    "model": self.embed_model,
                    "prompt": text
                }
            )
            response.raise_for_status()
            data = response.json()
            return data["embedding"]

    async def generate_response(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        async with httpx.AsyncClient(timeout=120.0) as client:
            messages = []
            if system_instruction:
                messages.append({"role": "system", "content": system_instruction})
            messages.append({"role": "user", "content": prompt})

            response = await client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "options": {
                        "temperature": 0.2
                    },
                    "stream": False
                }
            )
            response.raise_for_status()
            data = response.json()
            return data["message"]["content"]


def get_provider() -> BaseLLMProvider:
    """
    Factory function resolving LLM provider instance from settings.
    """
    provider_name = settings.LLM_PROVIDER.lower().strip()
    if provider_name == "gemini":
        return GeminiProvider()
    elif provider_name == "openai":
        return OpenAIProvider()
    elif provider_name == "ollama":
        return OllamaProvider()
    else:
        raise ValueError(f"Unsupported LLM provider: {settings.LLM_PROVIDER}")
