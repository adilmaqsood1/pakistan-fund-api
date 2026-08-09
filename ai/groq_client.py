import os
import logging
import httpx
from dotenv import load_dotenv
from fastapi import HTTPException

load_dotenv()

logger = logging.getLogger("groq_client")

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.3-70b-versatile"

async def ask_groq(system: str, user: str, temperature: float = 0.3) -> str:
    """
    Executes real LLM completion request to Groq API using llama-3.3-70b-versatile.
    """
    key = os.getenv("GROQ_API_KEY")
    
    if not key or key.startswith("gsk_xxx") or len(key) < 10:
        raise HTTPException(
            status_code=400,
            detail="GROQ_API_KEY environment variable is not configured. Please set a valid GROQ_API_KEY in .env file to enable real AI endpoints."
        )

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                GROQ_URL,
                headers={"Authorization": f"Bearer {key}"},
                json={
                    "model": MODEL,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user}
                    ],
                    "max_tokens": 512,
                    "temperature": temperature
                }
            )
            if resp.status_code == 200:
                data = resp.json()
                return data["choices"][0]["message"]["content"]
            else:
                logger.error(f"Groq API returned status {resp.status_code}: {resp.text}")
                raise HTTPException(
                    status_code=502,
                    detail=f"Groq API error (HTTP {resp.status_code}): {resp.text}"
                )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to connect to Groq API: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to connect to Groq API: {str(e)}"
        )
