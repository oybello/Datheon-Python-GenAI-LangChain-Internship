================================================================================
 STRUCTURED LLM PROMPT PIPELINE & JSON EXTRACTOR
 Datheon Internship | Python + Generative AI & LangChain | Task 1
================================================================================

Author  : Olanrewaju Y. Bello
Task    : Task 1 - Structured LLM Prompt Pipeline & JSON Extractor
Language: Python 3
Model   : Google Gemini (gemini-3.8-flash) via the google-genai SDK
Status  : COMPLETED AND VERIFIED (see Section 9)


--------------------------------------------------------------------------------
TABLE OF CONTENTS
--------------------------------------------------------------------------------
 1. Overview
 2. Problem Statement and How It Was Solved
 3. Project Structure
 4. File-by-File and Module-by-Module Description
 5. The Model Used: gemini-3.8-flash
 6. Setup and Installation
 7. How to Run
 8. Expected Outputs
 9. Evidence That the Problem Is Solved
10. How to Verify the Solution Works
11. Error Handling and Troubleshooting
12. Design Decisions
13. Limitations and Possible Improvements
14. Submitted Files


================================================================================
1. OVERVIEW
================================================================================

This project reads unstructured invoice text (typed tables, informal emails,
mixed date formats, mixed currencies) and converts it into strictly validated
JSON using a Large Language Model (LLM).

The pipeline does four things:

  1. Builds a parameterized prompt that contains rules and few-shot examples.
  2. Sends the prompt to the Google Gemini API and asks for JSON that matches
     a defined schema.
  3. Validates the model's answer with Pydantic, including an arithmetic check
     that the invoice total equals the sum of the line items plus tax.
  4. If validation fails, sends the exact error message back to the model and
     asks for a correction (retry loop). If it still fails, the document is
     reported as FAILED instead of silently saving wrong data.

In plain English: the LLM acts like an intern filling in a strict form, and
Pydantic acts like a manager who checks every form before accepting it.


================================================================================
2. PROBLEM STATEMENT AND HOW IT WAS SOLVED
================================================================================

Task requirement (from the Datheon task pack):
  "Connect Python to Google Gemini or OpenAI API, build parameterized prompt
   templates, and enforce strictly validated JSON outputs for invoice or
   resume analysis."

Suggested approach: Python SDK for the LLM, prompt engineering with few-shot
examples, and Pydantic schema validation.

Expected deliverable:
  "Executable script parsing complex unstructured text documents into
   validated JSON schemas."

How each requirement was met:

  Requirement                          | Where it is implemented
  -------------------------------------+---------------------------------------
  Connect Python to Gemini API         | extractor.py (google-genai Client)
  Parameterized prompt templates       | prompts.py (build_prompt function)
  Few-shot examples                    | prompts.py (FEW_SHOT_EXAMPLES)
  Strictly validated JSON output       | schemas.py (Pydantic models and rules)
  Invoice analysis                     | Whole pipeline, run by main.py
  Executable script                    | main.py (python main.py)
  Unstructured text input              | samples/*.txt (three styles of invoice)
  Validated JSON schema output         | outputs/*.json


================================================================================
3. PROJECT STRUCTURE
================================================================================

task1_json_extractor/
|-- .env                  Secret API key and model name (NOT to be shared)
|-- .gitignore            Keeps .env and venv out of version control
|-- requirements.txt      Exact package versions used
|-- schemas.py            Pydantic "form" and validation rules
|-- prompts.py            System instruction, few-shot examples, prompt builder
|-- extractor.py          Calls Gemini, validates the answer, retries on error
|-- main.py               Entry point: processes every document in samples/
|-- test_schema.py        Offline test of the validation rules (no API needed)
|-- samples/
|   |-- invoice_1.txt     Clean table-style invoice (NGN, with VAT)
|   |-- invoice_2.txt     Informal email-style invoice (USD, DD/MM/YYYY date)
|   |-- invoice_3.txt     Deliberately inconsistent invoice (wrong total)
|-- outputs/
|   |-- invoice_1.json    Validated result for invoice_1.txt
|   |-- invoice_2.json    Validated result for invoice_2.txt
|-- venv/                 Virtual environment (not submitted)
|-- __pycache__/          Python cache (not submitted)

Note: there is intentionally no invoice_3.json. That document contains an
arithmetic error and is correctly rejected (see Section 8.3).


================================================================================
4. FILE-BY-FILE AND MODULE-BY-MODULE DESCRIPTION
================================================================================

--------------------------------------------------------------------------
4.1  schemas.py  -  The strict form and the validation rules
--------------------------------------------------------------------------
Purpose:
  Defines exactly what a valid invoice looks like, using Pydantic.

Classes:

  LineItem
    Fields : description (text), quantity (number), unit_price (number)
    Rule   : quantity must be greater than 0.

  Invoice
    Fields : invoice_number (text), vendor (text), invoice_date (text,
             YYYY-MM-DD), currency (3-letter code), items (list of LineItem),
             tax (number), total (number)
    Rules  :
      - invoice_date must be a real calendar date. "2026-02-30" is rejected.
      - currency must be exactly 3 letters (NGN, USD, EUR). It is converted to
        upper case. "Naira" is rejected.
      - items must contain at least one line item.
      - total must equal the sum of (quantity x unit_price) for all items,
        plus tax, within a tolerance of 0.01.

Worked example of the arithmetic rule (invoice_1):
  (20 x 4,500) + (5 x 3,200) + (12 x 800) = 90,000 + 16,000 + 9,600 = 115,600
  115,600 + tax 8,670 = 124,270 = stated total   ->  ACCEPTED

Why it matters:
  The schema tells the model what shape to produce. The validators guarantee
  the answer is actually correct. The Gemini SDK does not run Pydantic
  validators by itself, so extractor.py calls model_validate_json() directly.

--------------------------------------------------------------------------
4.2  prompts.py  -  The parameterized prompt template
--------------------------------------------------------------------------
Purpose:
  Builds the text sent to the model. Contains all prompt engineering.

Contents:

  SYSTEM_INSTRUCTION
    Permanent rules sent as the model's "job description": never invent
    values, dates in YYYY-MM-DD, ISO currency codes, plain numbers without
    symbols or commas, unit_price means the price of ONE unit.

  FEW_SHOT_EXAMPLES
    Two worked examples (input text and expected JSON output):
      Example 1: naira invoice with 7.5% VAT, "3 March 2026".
      Example 2: dollar invoice, no tax, date "12/11/2025 (DD/MM/YYYY)" which
                 must become 2025-11-12.
    Both examples have correct arithmetic. Their different styles teach the
    model to handle varied real-world input.

  PROMPT_TEMPLATE
    Text with four blanks: {doc_type}, {extra_rules}, {examples},
    {document_text}.

  build_prompt(document_text, doc_type="invoice", extra_rules="")
    Fills the blanks and returns the final prompt. Because doc_type and
    extra_rules are parameters, the same template can be reused for other
    document types (for example resumes) without rewriting it. This is what
    makes the template "parameterized".

--------------------------------------------------------------------------
4.3  extractor.py  -  The engine (API call, validation, retry)
--------------------------------------------------------------------------
Purpose:
  Sends the prompt to Gemini, validates the response, and retries with
  feedback if validation fails.

Main function:

  extract_invoice(document_text, max_retries=...)
    1. Builds the prompt with build_prompt().
    2. Calls client.models.generate_content() with a configuration that sets:
         system_instruction  -> the permanent rules
         response_mime_type  -> "application/json" (JSON only, no extra text)
         response_schema     -> the Invoice class (the required shape)
         temperature         -> 0 (repeatable, non-creative output)
    3. Validates the reply with Invoice.model_validate_json(). This runs every
       rule in schemas.py.
    4. On success, returns a validated Invoice object.
    5. On failure (pydantic ValidationError), prints the rejection reason and
       can send that exact reason back to the model asking for a corrected
       answer, up to the configured number of retries (max_retries in
       extractor.py).
    6. If no valid answer is obtained, raises RuntimeError("Could not get a
       valid invoice after all retries.").

Configuration:
  The API key (GEMINI_API_KEY) and model name (GEMINI_MODEL) are read from the
  .env file using python-dotenv, so no secrets or model names are hard-coded.

--------------------------------------------------------------------------
4.4  main.py  -  The entry point
--------------------------------------------------------------------------
Purpose:
  Runs the whole pipeline over a folder of documents.

What it does:
  1. Finds every .txt file in the samples/ folder (sorted alphabetically).
  2. Reads each file as UTF-8 text.
  3. Calls extract_invoice() on the text.
  4. On success, saves the validated result to outputs/<name>.json with
     indentation for readability.
  5. On failure, prints "FAILED" for that document and continues with the
     next one, so one bad document never crashes the whole batch.

Run with:  python main.py

--------------------------------------------------------------------------
4.5  test_schema.py  -  Offline test of the validation rules
--------------------------------------------------------------------------
Purpose:
  Tests schemas.py without calling the API (free, instant, no internet).

What it does:
  - Builds a correct invoice (INV-204: 2 x 450,000 + 67,500 tax = 967,500) and
    confirms it is accepted.
  - Changes the total to 950,000 and confirms Pydantic rejects it with a
    clear "Total mismatch" message.

Run with:  python test_schema.py

--------------------------------------------------------------------------
4.6  samples/  -  Input documents
--------------------------------------------------------------------------
  invoice_1.txt  Clean table. Lagos Office Supplies Ltd, NGN, 3 items, VAT.
  invoice_2.txt  Informal email. SolarBright Energy, USD, date written as
                 02/10/2026 (day/month/year), no tax.
  invoice_3.txt  Kemi's Tailoring. The stated total (130,000) does not equal
                 the items (2 x 60,000 + 5,000 = 125,000). It exists to prove
                 the validator catches inconsistent documents.

--------------------------------------------------------------------------
4.7  outputs/  -  Validated JSON results
--------------------------------------------------------------------------
  invoice_1.json and invoice_2.json, produced by main.py (see Section 8).

--------------------------------------------------------------------------
4.8  Configuration and support files
--------------------------------------------------------------------------
  .env              GEMINI_API_KEY=<your key> and GEMINI_MODEL=gemini-3.8-flash
                    (never upload this file; remove the real key before
                    sharing the project).
  .gitignore        Lists .env, venv/ and __pycache__/ so they are not
                    committed to GitHub.
  requirements.txt  Packages installed: google-genai, pydantic, python-dotenv
                    (plus their dependencies), for reproducible setup.


================================================================================
5. THE MODEL USED: gemini-3.8-flash
================================================================================

5.1 What it is
  gemini-3.8-flash is a model from Google's Gemini family, accessed through the
  Gemini API. According to Google's published model page, it is described as
  their most intelligent "Flash" model, designed for long-horizon software
  engineering, autonomous agents and complex enterprise workflows, while
  keeping the speed and cost efficiency of the Flash line. It is listed as
  generally available (stable model code: gemini-3.8-flash), with its latest
  update in September 2026.

5.2 Why a Flash model for this task
  Invoice extraction is a high-volume, well-defined task: read text, fill
  fields. It does not need the slowest, most expensive model. Flash models
  are built for fast, low-cost responses, which suits batch document
  processing.

5.3 Why this model fits this project (capabilities from Google's model page)
  - Structured outputs: SUPPORTED. This is the key feature used here, because
    the pipeline requests JSON that follows a schema.
  - Input types: text, image, video, audio and PDF (this project uses text;
    PDF and image invoices are a natural future extension).
  - Context window: input limit of 1,048,576 tokens and output limit of 65,536
    tokens, far more than any invoice needs.
  - Thinking: supported at low, medium and high levels, with medium as the
    default. The minimal level is NOT supported and returns an error, so do
    not set it.
  - Also supported: function calling, caching, code execution, batch API.

5.4 Change from the originally suggested model
  The build guide suggested gemini-2.5-flash as a default. This project
  instead uses gemini-3.8-flash, a newer Flash model. No code change was
  needed, because the model name is stored in the .env file (GEMINI_MODEL) and
  read at run time.

5.5 SDK used
  google-genai (import: "from google import genai"), Google's current official
  Python SDK. The task pack mentions google-generativeai, which is the older
  library; the newer SDK was chosen because it is the one currently
  maintained and it supports passing a Pydantic class directly as the
  response schema.

5.6 Settings and why
  temperature = 0
      Extraction must be repeatable. The same invoice should give the same
      JSON every time.
  response_mime_type = "application/json"
      The model returns JSON only, with no explanations around it.
  response_schema = Invoice
      Gives the model the exact fields and types to produce.
  system_instruction = SYSTEM_INSTRUCTION
      Keeps permanent rules separate from the document text.

5.7 Cost and limits
  Pricing and rate limits change. Check Google's current pricing page and your
  API quota in Google AI Studio before processing large batches.


================================================================================
6. SETUP AND INSTALLATION
================================================================================

Requirements: Python 3.10 or newer, a Google Gemini API key (Google AI Studio).

Step 1  Open a terminal in the project folder.

Step 2  Create the virtual environment:
          python -m venv venv

Step 3  Activate it (you should see "(venv)" at the start of the prompt):
          Windows PowerShell : venv\Scripts\Activate.ps1
          Windows cmd        : venv\Scripts\activate.bat
          Mac / Linux        : source venv/bin/activate

        If PowerShell says "running scripts is disabled", run:
          Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
        then activate again (or use cmd).

Step 4  Install the packages:
          pip install -r requirements.txt
        (or: pip install google-genai pydantic python-dotenv)

Step 5  Create a file named .env in the project folder containing:
          GEMINI_API_KEY=your_real_key_here
          GEMINI_MODEL=gemini-3.8-flash
        No quotes and no spaces around the = sign.


================================================================================
7. HOW TO RUN
================================================================================

  1. Put the documents to process (.txt files) in the samples/ folder.
  2. With the virtual environment active, run:

         python main.py

  3. Read the progress messages in the terminal.
  4. Open the outputs/ folder to find one .json file per successfully
     processed document.

Optional offline test of the rules (no API key or internet needed):

         python test_schema.py


================================================================================
8. EXPECTED OUTPUTS
================================================================================

8.1 Terminal output of a successful run
-----------------------------------------
  Processing invoice_1.txt ...
    Saved outputs\invoice_1.json

  Processing invoice_2.txt ...
    Saved outputs\invoice_2.json

  Processing invoice_3.txt ...
    Attempt 1 rejected:
    1 validation error for Invoice
    Value error, Total mismatch: items add to 125000.0 plus tax 0.0 =
    125000.0, but the invoice total is 130000.0 [type=value_error, ...]
      For further information visit https://errors.pydantic.dev/...
    FAILED: Could not get a valid invoice after all retries.

This is the correct and intended behaviour: two valid documents are saved and
the inconsistent one is rejected.

8.2 Validated result: outputs/invoice_1.json
-----------------------------------------
{
  "invoice_number": "LOS/2026/0097",
  "vendor": "Lagos Office Supplies Ltd",
  "invoice_date": "2026-09-14",
  "currency": "NGN",
  "items": [
    {"description": "A4 Paper (ream)",    "quantity": 20.0, "unit_price": 4500.0},
    {"description": "Stapler",            "quantity": 5.0,  "unit_price": 3200.0},
    {"description": "Whiteboard markers", "quantity": 12.0, "unit_price": 800.0}
  ],
  "tax": 8670.0,
  "total": 124270.0
}

(The saved file lists each field on its own line; it is compressed here only
to save space.)

Arithmetic check:
  20 x 4,500 = 90,000
   5 x 3,200 = 16,000
  12 x   800 =  9,600
  Subtotal   = 115,600
  Tax        =   8,670
  Total      = 124,270   -> matches "total": 124270.0

What this proves: the model correctly read a table, converted "14th September
2026" to 2026-09-14, wrote the currency as the code NGN, and returned plain
numbers with no symbols or commas.

8.3 Validated result: outputs/invoice_2.json
-----------------------------------------
{
  "invoice_number": "SB-5521",
  "vendor": "SolarBright Energy",
  "invoice_date": "2026-10-02",
  "currency": "USD",
  "items": [
    {"description": "solar panels", "quantity": 3.0, "unit_price": 280.0},
    {"description": "inverter",     "quantity": 1.0, "unit_price": 450.0}
  ],
  "tax": 0.0,
  "total": 1290.0
}

Arithmetic check:
  3 x 280 = 840
  1 x 450 = 450
  Total   = 1,290 (no tax)  -> matches "total": 1290.0

What this proves: the model extracted structured data from an informal email,
correctly read the date "02/10/2026 (day/month/year)" as 2 October 2026 (not
10 February), converted "$" to USD, and set tax to 0 because the email said
"No tax applies".

8.4 Expected rejection: invoice_3.txt (no JSON file is produced)
-----------------------------------------
  Items: (2 x 60,000) + (1 x 5,000) = 125,000
  Document claims a total of 130,000
  Difference: 5,000

The validator rejects it with the message:
  "Total mismatch: items add to 125000.0 plus tax 0.0 = 125000.0, but the
   invoice total is 130000.0"

This is deliberate. Financial data that does not add up must be flagged for
human review, never silently corrected or accepted.

8.5 Quick reference table of expected values
-----------------------------------------
  File          | Number        | Date       | Cur | Items | Tax    | Total
  --------------+---------------+------------+-----+-------+--------+---------
  invoice_1     | LOS/2026/0097 | 2026-09-14 | NGN |   3   | 8670   | 124270
  invoice_2     | SB-5521       | 2026-10-02 | USD |   2   | 0      | 1290
  invoice_3     | (rejected)    |     -      |  -  |   -   |   -    | mismatch


================================================================================
9. EVIDENCE THAT THE PROBLEM IS SOLVED
================================================================================

The deliverable was: "Executable script parsing complex unstructured text
documents into validated JSON schemas." Each part is demonstrated:

  [x] Executable script
        "python main.py" runs end to end without crashing.

  [x] Connected to the Gemini API
        Run with gemini-3.8-flash through the google-genai SDK.

  [x] Parameterized prompt templates
        build_prompt(document_text, doc_type, extra_rules) in prompts.py.

  [x] Few-shot prompt engineering
        Two worked examples with different currencies, tax cases and date
        formats.

  [x] Complex, unstructured input handled
        A formatted table (invoice_1) and a casual email with an ambiguous
        date format (invoice_2) both produced correct output.

  [x] Strictly validated JSON schema
        Pydantic enforces types, a real calendar date, a 3-letter currency,
        at least one item, and total = items + tax.

  [x] Correct results
        invoice_1.json and invoice_2.json match the source text exactly, and
        the totals reconcile arithmetically.

  [x] Bad data is rejected, not accepted
        invoice_3.txt was refused because 125,000 does not equal 130,000.
        The terminal shows the rejection and "FAILED", and no JSON file is
        written for it.

  [x] Evidence attached
        The submitted files include outputs/invoice_1.json,
        outputs/invoice_2.json and a screenshot of the terminal output.


================================================================================
10. HOW TO VERIFY THE SOLUTION WORKS
================================================================================

Anyone can confirm the solution in about five minutes.

Check 1 - Offline rules test (no API needed)
  Run:  python test_schema.py
  Expect:
    - The INV-204 invoice is printed as accepted.
    - A second invoice with total 950,000 is rejected with the message
      "Total mismatch: items add to 900000.0 plus tax 67500.0 = 967500.0, but
      the invoice total is 950000.0".

Check 2 - Full pipeline run
  Run:  python main.py
  Expect: "Saved outputs\invoice_1.json", "Saved outputs\invoice_2.json", and
          "FAILED" for invoice_3.txt.

Check 3 - Compare against the expected values
  Open outputs/invoice_1.json and outputs/invoice_2.json and compare them with
  the table in Section 8.5 and the source files in samples/.

Check 4 - Re-validate the saved files independently
  This re-runs every Pydantic rule on the JSON files on disk. Run this single
  line from the project folder:

    python -c "from pathlib import Path; from schemas import Invoice; [print(f.name, 'VALID, total =', Invoice.model_validate_json(f.read_text(encoding='utf-8')).total) for f in sorted(Path('outputs').glob('*.json'))]"

  Expected output:
    invoice_1.json VALID, total = 124270.0
    invoice_2.json VALID, total = 1290.0

Check 5 - Hand-check the arithmetic
  Invoice 1: 90,000 + 16,000 + 9,600 + 8,670 = 124,270
  Invoice 2: 840 + 450 = 1,290

Check 6 - Prove the rejection works on any document
  Edit a copy of samples/invoice_1.txt and change the stated total to a wrong
  number, then run python main.py. The edited copy must be reported as FAILED.
  This shows the check is real and not a coincidence.

Check 7 - Repeatability
  Run python main.py again. Because temperature is 0, the results should be
  the same or nearly identical.


================================================================================
11. ERROR HANDLING AND TROUBLESHOOTING
================================================================================

11.1 Setup errors
-----------------
Problem : "python is not recognized"
Cause   : Python is not on PATH.
Fix     : Try "py" instead of "python". Otherwise reinstall Python from
          python.org and tick "Add python.exe to PATH". Restart VS Code.

Problem : PowerShell: "running scripts is disabled on this system"
Fix     : Run: Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy
          RemoteSigned   (answer Y), then activate again. Or use Command
          Prompt and venv\Scripts\activate.bat.

Problem : "(venv)" is missing from the prompt
Fix     : The virtual environment is not active. Run the activation command
          again. In VS Code: Ctrl+Shift+P > "Python: Select Interpreter" and
          choose the interpreter inside the venv folder.

Problem : ModuleNotFoundError: No module named 'google' / 'pydantic' /
          'dotenv'
Cause   : Packages not installed in the active environment.
Fix     : Activate the venv, then run pip install google-genai pydantic
          python-dotenv.

Problem : ModuleNotFoundError: No module named 'schemas'
Cause   : The file is misspelled or the import does not match the file name,
          or you are running from the wrong folder.
Fix     : Make sure the file is named exactly schemas.py, that imports read
          "from schemas import Invoice", and that you run commands from inside
          the project folder.

Problem : A script behaves strangely right after you create a file
Cause   : A file was named google.py, pydantic.py or dotenv.py, which hides the
          real package.
Fix     : Rename it.

11.2 API and model errors
-------------------------
Problem : Error about a missing or invalid API key (for example 400 or 403)
Fix     : Check .env: the file must be named exactly ".env" (not ".env.txt"),
          must be in the folder you run from, and must read
          GEMINI_API_KEY=yourkey with no quotes or spaces. Generate a fresh
          key in Google AI Studio if needed.

Problem : 404 / "model not found"
Cause   : The model name in .env is misspelled or no longer available.
Fix     : Set GEMINI_MODEL=gemini-3.8-flash (or another current model name
          copied from Google's models page). No code change is needed.

Problem : Error mentioning an unsupported thinking level
Cause   : "minimal" thinking is not supported by gemini-3.8-flash.
Fix     : Use low, medium or high, or leave the default (medium).

Problem : 429 / "quota exceeded" / rate limit
Cause   : Too many requests in a short time, or the quota is used up.
Fix     : Wait a minute and run again. For large batches add "import time" and
          "time.sleep(2)" between documents in main.py.

Problem : 500 / 503 / temporary server errors
Fix     : These are temporary. Run the script again after a short wait.

Problem : response.text is None or empty
Cause   : The response was blocked or cut off.
Fix     : Print the full response object to inspect it. Try a shorter
          document or run again.

Problem : Connection or timeout errors
Fix     : Check your internet connection or VPN and try again.

11.3 Validation errors (these are the pipeline working as designed)
-------------------------------------------------------------------
Problem : "Total mismatch: items add to X plus tax Y = Z, but the invoice total
          is W"
Meaning : The numbers on the document do not add up (or the model misread a
          figure).
Fix     : Open the source .txt. If the document itself is wrong (as with
          invoice_3), no code fix is needed: it should be flagged for human
          review. If the document is right, check that the model read the
          quantity, unit price and tax correctly, and consider adding fields
          for discounts or shipping if the invoice has them.

Problem : "invoice_date 'X' is not a valid YYYY-MM-DD date"
Fix     : Add a few-shot example that shows the date format used in your
          documents, or pass a hint through the extra_rules parameter of
          build_prompt(), for example "Dates in this batch are DD/MM/YYYY".

Problem : "currency 'X' must be a 3-letter code"
Fix     : Strengthen the currency rule in SYSTEM_INSTRUCTION, for example
          "Convert N or Naira to NGN, $ to USD".

Problem : "quantity must be greater than 0"
Fix     : Check the source text for missing quantities. Decide how to treat
          services billed without a quantity (for example, use 1).

Problem : "invoice must have at least one line item"
Fix     : The model returned an empty list. Check that the document really
          contains items and that the text was read correctly.

Problem : "FAILED: Could not get a valid invoice after all retries."
Meaning : All attempts were rejected. The document is reported and the batch
          continues with the next file.
Fix     : Read the printed validation message above it and follow the matching
          entry in this section.

11.4 File and encoding errors
-----------------------------
Problem : UnicodeDecodeError when reading a sample
Fix     : Save the file as UTF-8 (Notepad: Save As > Encoding UTF-8).

Problem : No output files appear
Cause   : No .txt files in samples/, or every document failed validation.
Fix     : Confirm the samples/ folder exists next to main.py and contains
          .txt files. Read the terminal messages.


================================================================================
12. DESIGN DECISIONS
================================================================================

  1. Two layers of strictness.
     The schema (shape) goes to the model. The validators (rules) run in
     Python afterwards. The model can be wrong, so its output is never trusted
     without checking.

  2. Arithmetic validation.
     Checking that items plus tax equal the total catches misread numbers and
     inconsistent source documents.

  3. Retry with feedback.
     Giving the model the exact error lets it correct itself, a technique more
     reliable than blind retries.

  4. Fail safe, not silent.
     A document that cannot be validated is reported as FAILED. For financial
     data, flagging for human review is better than guessing.

  5. Temperature 0.
     Extraction should be consistent and repeatable.

  6. Secrets and configuration outside the code.
     The API key and model name live in .env, so changing models needs no code
     edit and keys are never uploaded.

  7. One bad file never stops the batch.
     main.py catches the failure and continues.

  8. Simple schema for the model, strict rules in Python.
     Keeping the schema sent to the API simple avoids unsupported schema
     features, while all strict constraints are enforced by Pydantic validators.


================================================================================
13. LIMITATIONS AND POSSIBLE IMPROVEMENTS
================================================================================

Limitations
  - Only plain text (.txt) input is processed. Scanned or image invoices need
    OCR or the model's image/PDF input.
  - The schema has a single tax field. Invoices with discounts, shipping fees,
    multiple tax lines or rounding adjustments would need extra fields, or the
    total check would wrongly reject them.
  - Model output can occasionally vary; validation reduces this risk but does
    not remove it.
  - The few-shot examples cover two formats. Unusual layouts may need extra
    examples.

Possible improvements
  - Add a resume schema and reuse build_prompt with doc_type="resume".
  - Add a command-line option (argparse), for example python main.py --type
    resume.
  - Log every attempt (file, attempt number, error) to a log file.
  - Add PDF and image input using the model's multimodal support.
  - Add discount, shipping and multi-tax fields.
  - Add automated tests (pytest) for the validators and a mocked API call.
  - Move the same logic into LangChain with structured output as a next step
    toward later tasks in the program.


================================================================================
14. SUBMITTED FILES
================================================================================

  README.txt                  This document
  schemas.py                  Pydantic models and validation rules
  prompts.py                  Prompt template and few-shot examples
  extractor.py                Gemini API call, validation and retry logic
  main.py                     Entry point
  test_schema.py              Offline validation test
  requirements.txt            Package list
  samples/invoice_1.txt       Input document 1
  samples/invoice_2.txt       Input document 2
  samples/invoice_3.txt       Input document 3 (intentionally inconsistent)
  outputs/invoice_1.json      Validated output 1
  outputs/invoice_2.json      Validated output 2
  Screenshot of terminal run  Evidence of execution

NOT submitted: .env (contains your secret key), venv/, __pycache__/.

================================================================================
 END OF README
================================================================================
