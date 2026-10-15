from langchain_mistralai import ChatMistralAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.runnables import RunnablePassthrough, RunnableLambda

import os

def get_llm():
    return ChatMistralAI(model = "mistral-small-latest", mistral_api_key = os.getenv("MISTRAL_API_KEY"), temperature=0.3)

def split_transcript(transcript: str) -> list:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size = 3000,
        chunk_overlap = 200,
    )

    return splitter.split_text(transcript)

def summarize(transcript: str)-> str:
    llm = get_llm()
    map_prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert at summarizing spoken content. You will receive ONE \
    segment of a transcript from an audio or video recording. The recording could be \
    anything: a lecture, tutorial, Q&A session, interview, podcast, talk, webinar, \
    meeting, discussion, or something else. Write a faithful, information-dense summary \
    of this segment only.

    About the transcript:
    - It was produced by automatic speech recognition and may contain typos, \
    mis-heard words, filler words, repetitions, and missing punctuation.
    - Parts may have been machine-translated from Hindi to English, so phrasing can be \
    awkward. Infer the intended meaning, but never invent facts.
    - There are usually no speaker labels. Only attribute statements to a person if \
    the text clearly names them.
    - This is a segment from a longer recording. It may start or end mid-sentence, and \
    earlier context is not available.

    Rules:
    1. Use ONLY information present in the segment. Do not guess, add outside \
    knowledge, or correct the speaker's claims.
    2. Preserve exact specifics: names, dates, numbers, formulas, terms, definitions, \
    and examples.
    3. Remove filler, repetition, greetings, sponsor reads, and off-topic chatter.
    4. Adapt to the content type. Capture what matters most for that kind of content \
    (for example: concepts and explanations for a lecture, questions and their \
    answers for a Q&A, steps for a tutorial, decisions and tasks for a meeting).
    5. Write in neutral third person.
    6. If the segment has no substantive content (silence, intro music, noise), say so \
    in one line instead of padding.

    Output in this format:

    CONTENT TYPE: <one or two words, e.g. lecture, Q&A, tutorial, interview, meeting>

    SUMMARY:
    <2-5 sentences covering the main ideas of this segment>

    KEY POINTS:
    - <important idea, fact, argument, or step>
    - <...>

    Include the following sections ONLY if this segment actually contains that \
    material. Omit a section entirely otherwise:

    DEFINITIONS & CONCEPTS:
    - <term>: <explanation as given>

    EXAMPLES & DEMOS:
    - <notable example, case study, or demonstration>

    QUESTIONS & ANSWERS:
    - Q: <question asked> | A: <answer given, or "Not answered in this segment">

    DECISIONS:
    - <anything explicitly agreed or decided>

    ACTION ITEMS:
    - <task> | Owner: <name or "Not specified"> | Deadline: <date or "Not specified">

    RESOURCES MENTIONED:
    - <books, tools, links, papers, or people referenced>"""),
    ("human", "Transcription segment:\n\n{text}"),
    ]
    )

    map_chain = map_prompt | llm | StrOutputParser()

    chunks = split_transcript(transcript)

    chunk_summaries = [map_chain.invoke({"text": chunk}) for chunk in chunks]

    combined = "\n\n---\n\n".join(
    f"[Segment {i + 1}]\n{s}" for i, s in enumerate(chunk_summaries)
    )

    #Add this if you don't want a second API call just for generating a title
    #TITLE: <short descriptive title inferred from the content>
    combined_prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert editor. You will receive structured summaries of \
    consecutive segments of ONE recording (a lecture, tutorial, Q&A session, interview, \
    podcast, talk, meeting, or similar). The segments were cut with overlap, so \
    neighbouring summaries often repeat the same points, sometimes in different words. \
    Merge them into ONE clean, structured summary of the whole recording.

    How to merge:
    1. Segments are in chronological order. Preserve that order of ideas.
    2. Remove duplicates. If the same point, definition, example, question, decision, \
    or action item appears in multiple segments (even reworded), keep it once, using \
    the most complete version.
    3. Combine partial mentions. If a point is split across two segments, merge them \
    into one complete statement.
    4. Keep the meaning identical to the source. Use ONLY information present in the \
    segment summaries. Do not add outside knowledge, opinions, or new conclusions.
    5. Preserve exact specifics: names, dates, numbers, formulas, terms, and examples.
    6. Resolve conflicts: if segments contradict each other, keep the later version \
    and note the discrepancy briefly.
    7. Ignore segments marked as having no substantive content.
    8. Do not mention segments, chunks, or the merging process in your output. It \
    must read as one coherent summary of the original recording.

    Adapt the layout to the CONTENT TYPE reported by the segments:
    - Lecture / tutorial: overview, then topics in the order taught, with definitions \
    and examples.
    - Q&A / interview: overview, then the main questions with their answers.
    - Meeting / discussion: overview, then discussion topics, decisions, and action items.
    - Other: use the sections that fit best.

    Output in this format:

    CONTENT TYPE: <lecture, Q&A, tutorial, meeting, etc.>

    OVERVIEW:
    <3-6 sentences describing what the whole recording is about and its main takeaways>

    MAIN TOPICS:
    ### <Topic or section heading>
    - <key points, in logical order>

    Include the following sections ONLY if they have content after merging. Omit a \
    section entirely otherwise:

    KEY DEFINITIONS & CONCEPTS:
    - <term>: <explanation>

    EXAMPLES & DEMOS:
    - <notable example or demonstration>

    QUESTIONS & ANSWERS:
    - Q: <question> | A: <answer>

    DECISIONS:
    - <decision>

    ACTION ITEMS:
    - <task> | Owner: <name or "Not specified"> | Deadline: <date or "Not specified">

    OPEN QUESTIONS:
    - <unresolved question or follow-up>

    RESOURCES MENTIONED:
    - <books, tools, links, papers, or people>"""),
        ("human", "{text}")
        ])

    combined_chain = (
        RunnablePassthrough() | RunnableLambda(lambda x:{"text":x}) | combined_prompt | llm | StrOutputParser()
    )

    return combined_chain.invoke(combined)
def sample(t, n=1000):
    if len(t) <= 3 * n:
        return t
    mid = len(t) // 2
    return f"{t[:n]}\n...\n{t[mid - n//2: mid + n//2]}\n...\n{t[-n:]}"

def generate_title(transcript: str) -> str:
    if not transcript.strip():
        return "Untitled"

    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "Based on the transcript excerpts, write a short, suitable title "
         "(max 8 words) in English. Return only the title."),
        ("human", "{text}"),
    ])
    chain = prompt | get_llm() | StrOutputParser()

    title = chain.invoke({"text": sample(transcript)})
    return title.strip().strip('"\'').removeprefix("Title:").strip()