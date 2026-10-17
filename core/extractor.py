# Actionable items, decisions, questions

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda, RunnablePassthrough

import os

def get_llm():
    # Cloudflare Workers AI via its OpenAI-compatible endpoint
    return ChatOpenAI(
        model=os.getenv("CLOUDFLARE_MODEL", "@cf/meta/llama-3.1-8b-instruct-fp8"),
        api_key=os.getenv("CLOUDFLARE_API_TOKEN"),
        base_url=f"https://api.cloudflare.com/client/v4/accounts/{os.getenv('CLOUDFLARE_ACCOUNT_ID')}/ai/v1",
        temperature=0.2,
        max_tokens=int(os.getenv("CLOUDFLARE_MAX_TOKENS", "1024")),
        max_retries=3,
        timeout=120,
    )


def build_chain(system_prompt : str):
    llm = get_llm()
    return (
        RunnablePassthrough() | RunnableLambda(lambda x : {"text":x}) | ChatPromptTemplate.from_messages([
        ("system" , system_prompt),
        ("human", "{text}"),
    ]) | llm | StrOutputParser()
    )

def extract_action_items(transcript : str) -> str:
    chain = build_chain(
        """You are an expert meeting analyst. You extract action items from a transcript of a recording (meeting, lecture, Q&A, interview, or similar).
        An action item is a specific task that someone commits to, is assigned, or is explicitly told to do after the recording. Do not include general topics, opinions, or things that were merely discussed.

        The transcript is machine-generated (and may be machine-translated from Hindi), so it can contain errors and has no speaker labels. Rules:
        1. Use ONLY what the transcript says. Never invent tasks, owners, or deadlines.
        2. Only name an owner if the text clearly states one; otherwise write "Not specified".
        3. Only give a deadline if one is stated; otherwise write "Not specified".
        4. Merge duplicates and keep each task once, in chronological order.
        5. If there are no action items, output exactly: No action items found

        Output format, one line per item:
        - <task, starting with a verb> | Owner: <name or Not specified> | Deadline: <date or Not specified>"""
    )

    return chain.invoke(transcript)

def extract_key_decisions(transcript: str) -> str:
    chain = build_chain(
        "You are an expert meeting analyst. From the meeting transcript, "
        "extract all key decisions made. Format as a numbered list. "
        "If none found say 'No key decisions found.'"
    )
    return chain.invoke(transcript)


def extract_questions(transcript: str) -> str:
    chain = build_chain(
        "From the meeting transcript, extract all unresolved questions "
        "or topics needing follow-up. Format as a numbered list. "
        "If none found say 'No open questions found.'"
    )
    return chain.invoke(transcript)