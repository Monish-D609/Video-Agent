import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from core.vector_store import build_vector_store, load_vector_store, get_retriever

def get_llm():
    return ChatOpenAI(
        model=os.getenv("CLOUDFLARE_MODEL", "@cf/meta/llama-3.1-8b-instruct-fp8"),
        api_key=os.getenv("CLOUDFLARE_API_TOKEN"),
        base_url=f"https://api.cloudflare.com/client/v4/accounts/{os.getenv('CLOUDFLARE_ACCOUNT_ID')}/ai/v1",
        temperature=0.2,
        max_tokens=int(os.getenv("CLOUDFLARE_MAX_TOKENS", "1024")),
        max_retries=3,
        timeout=120,
    )

def format_docs(docs):
    return "\n\n".join([doc.page_content for doc in docs])

def build_rag_chain(transcript: str, key: str = "default"):

    vector_store = build_vector_store(transcript, key=key)

    retriever = get_retriever(vector_store, k=4)

    llm = get_llm()

    prompt = ChatPromptTemplate.from_messages(

        [(
            "system",
            """You are an expert video/audio content assistant. Answer the user's question
based ONLY on the transcript context provided below.

If the answer is not found in the context, say:
"I could not find this information in the recording transcription."

Always be concise and precise. If quoting someone, mention it clearly.

Context from transcript:
{context}""",
        ),
        ("human", "{question}"),
    ]
    )

    # full LCEL RAG pipeline
    rag_chain = (
        {"context": retriever | RunnableLambda(format_docs),
         "question": RunnablePassthrough(),
         }
        | prompt | llm | StrOutputParser()
    )

    return rag_chain


def load_rag_chain(key: str = "default"):
    vector_store = load_vector_store(key=key)
    retriever = get_retriever(vector_store, k=4)

    llm = get_llm()
    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            """You are an expert video/audio content assistant. Answer the user's question
based ONLY on the transcript context provided below.

If the answer is not found in the context, say:
"I could not find this information in the recording transcription."

Always be concise and precise. If quoting someone, mention it clearly.

Context from transcript:
{context}""",
        ),
        ("human", "{question}"),
    ])

    rag_chain = (
        {
            "context": retriever | RunnableLambda(format_docs),
            "question": RunnablePassthrough(),
        }
        | prompt
        | llm
        | StrOutputParser()
    )

    return rag_chain


def ask_question(rag_chain, question:str) -> str:
    print(f"Question : {question}")
    answer = rag_chain.invoke(question)
    print(f"answer :{answer}")
    return answer