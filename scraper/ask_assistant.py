import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

STORE_NAME_FILE = "store_name.txt"

SYSTEM_PROMPT = """You are OptiBot, the customer-support bot for OptiSigns.com.
- Tone: helpful, factual, concise.
- Only answer using the uploaded docs.
- Max 5 bullet points; else link to the doc.
- Cite up to 3 "Article URL:" lines per reply."""

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

with open(STORE_NAME_FILE, "r") as f:
    store_name = f.read().strip()

def ask(question):
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=question,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            tools=[
                types.Tool(
                    file_search=types.FileSearch(file_search_store_names=[store_name])
                )
            ],
        ),
    )
    return response.text

if __name__ == "__main__":
    question = "How do I add a YouTube video?"
    answer = ask(question)
    print(f"Question: {question}\n")
    print(f"Answer:\n{answer}")