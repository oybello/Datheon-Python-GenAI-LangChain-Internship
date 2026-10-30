from pydantic import ValidationError
from schemas import Invoice

good = {
    "invoice_number": "INV-204",
    "vendor": "Acme Ltd",
    "invoice_date": "2026-03-03",
    "currency": "NGN",
    "items": [{"description": "Laptop", "quantity": 2, "unit_price": 450000}],
    "tax": 67500,
    "total": 967500,
}

print("GOOD invoice accepted:")
print(Invoice(**good))
 
bad = dict(good, total=950000)       # same data, wrong total
try:
    Invoice(**bad)
except ValidationError as err:
    print("\nBAD invoice rejected, as expected:")
    print(err)
