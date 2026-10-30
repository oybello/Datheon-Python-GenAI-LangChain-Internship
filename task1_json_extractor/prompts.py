import json

SYSTEM_INSTRUCTION = """You are a precise data-extraction assistant.
Read the document and return ONLY data that fits the required schema.
Rules:
- Never invent values. If something is truly missing, use "" for text and 0 for numbers.
- Dates must be in YYYY-MM-DD format.
- Currency must be a 3-letter ISO code (NGN, USD, EUR, ...).
- Numbers must be plain numbers: no currency symbols, no thousands separators.
- unit_price is the price of ONE unit, not the line total.
"""

FEW_SHOT_EXAMPLES = [
    {
        "input": (
            "INVOICE No. INV-204\n"
            "From: Acme Ltd\n"
            "Date: 3 March 2026\n"
            "2 x Laptop @ NGN 450,000\n"
            "VAT (7.5%): NGN 67,500\n"
            "Total due: NGN 967,500"
        ),
        "output": {
            "invoice_number": "INV-204",
            "vendor": "Acme Ltd",
            "invoice_date": "2026-03-03",
            "currency": "NGN",
            "items": [
                {"description": "Laptop", "quantity": 2, "unit_price": 450000}
            ],
            "tax": 67500,
            "total": 967500,
        },
    },
    {
        "input": (
            "Bill from Bright Ink Co., ref #8831, issued 12/11/2025 (DD/MM/YYYY).\n"
            "Notebook x10 at $3.50 each; Pens (box) x2 at $12.00.\n"
            "No tax. Amount payable: $59.00"
        ),
        "output": {
            "invoice_number": "8831",
            "vendor": "Bright Ink Co.",
            "invoice_date": "2025-11-12",
            "currency": "USD",
            "items": [
                {"description": "Notebook", "quantity": 10, "unit_price": 3.5},
                {"description": "Pens (box)", "quantity": 2, "unit_price": 12.0},
            ],
            "tax": 0,
            "total": 59.0,
        },
    },
]

PROMPT_TEMPLATE = """Extract the {doc_type} data from the document below.
{extra_rules}
{examples}
NOW EXTRACT FROM THIS DOCUMENT:
{document_text}
"""



def build_prompt(document_text: str, doc_type: str = "invoice", extra_rules: str = "") -> str:
    examples = ""
    for ex in FEW_SHOT_EXAMPLES:
        examples += (
            f"EXAMPLE INPUT:\n{ex['input']}\n"
            f"EXAMPLE OUTPUT:\n{json.dumps(ex['output'], indent=2)}\n\n"
        )
    return PROMPT_TEMPLATE.format(
        doc_type=doc_type,
        extra_rules=extra_rules,
        examples=examples,
        document_text=document_text,
    )
