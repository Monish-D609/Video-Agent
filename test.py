from dotenv import load_dotenv
load_dotenv()   # MUST be before any core/ imports
from utils.audio_processor import process_input
from core.transcriber import transcribe_all

source = "https://www.youtube.com/watch?v=E6LvUJ5EUuc"
language = "hinglish"

chunks = process_input(source)
transcript = transcribe_all(chunks, language=language)

print("\n== TRANSCRIPT ==\n")
print(transcript)
