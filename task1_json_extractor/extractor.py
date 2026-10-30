import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import ValidationError

from schemas import Invoice
from prompts import SYSTEM_INSTRUCTION, build_prompt

load_dotenv()
client = genai.Client()
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

def extract_invoice(document_text: str, max_retries: int = 2) -> Invoice:
    
    base_prompt = build_prompt(document_text, doc_type="invoice")
    prompt = base_prompt
 
    for attempt in range(1, max_retries + 2):
        response = client.models.generate_content(
            model=MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                response_mime_type="application/json",
                response_schema=Invoice,
                temperature=0,
            ),
        )

        try:
            return Invoice.model_validate_json(response.text or "")
        except ValidationError as err:
            print(f"  Attempt {attempt} rejected:\n  {err}")
            prompt = (
                base_prompt
                + "\n\nYour previous answer was rejected for this reason:\n"
                + str(err)
                + "\nReturn a corrected JSON answer."
            )

        raise RuntimeError("Could not get a valid invoice after all retries.")

