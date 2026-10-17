"""
Single place that builds the LLM client, so summarize.py and extractor.py
stay provider-agnostic. Uses Cloudflare Workers AI through its
OpenAI-compatible endpoint, so all existing LangChain (LCEL) chains work unchanged.

Env vars:
  CLOUDFLARE_ACCOUNT_ID   your Cloudflare account id
  CLOUDFLARE_API_TOKEN    API token with "Workers AI" permission
  CLOUDFLARE_MODEL        optional, default below
"""
import os
from langchain_openai import ChatOpenAI

DEFAULT_MODEL = "@cf/meta/llama-3.1-8b-instruct"


def get_llm(temperature: float = 0.2) -> ChatOpenAI:
    account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID")
    token = os.getenv("CLOUDFLARE_API_TOKEN")
    if not account_id or not token:
        raise RuntimeError(
            "CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN must be set in environment / .env"
        )

    return ChatOpenAI(
        model=os.getenv("CLOUDFLARE_MODEL", DEFAULT_MODEL),
        api_key=token,
        base_url=f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1",
        temperature=temperature,
        max_tokens=int(os.getenv("CLOUDFLARE_MAX_TOKENS", "1024")),
        max_retries=3,
        timeout=120,
    )