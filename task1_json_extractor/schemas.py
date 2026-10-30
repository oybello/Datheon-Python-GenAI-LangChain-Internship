from datetime import date
from pydantic import BaseModel, Field, field_validator, model_validator

class LineItem(BaseModel):
    description: str = Field(description="What was bought")
    quantity: float = Field(description="Number of units")
    unit_price: float = Field(description="Price of ONE unit, digits only")

    @field_validator("quantity")
    @classmethod
    def quantity_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError("Quantity must be greater than zero")
        return v

class Invoice(BaseModel):

    invoice_number: str = Field(description="Invoice or reference number")
    vendor: str = Field(description="Company that issued the invoice")
    invoice_date: str = Field(description="Issue date in YYYY-MM-DD format")
    currency: str = Field(description="3-letter ISO code such as NGN, USD, EUR")
    items: list[LineItem]
    tax: float = Field(description="Total tax amount. Use 0 if there is no tax")
    total: float = Field(description="Final amount payable")

    @field_validator("invoice_date")
    @classmethod
    def date_must_be_real(cls, v):
        try:
            date.fromisoformat(v)
        except ValueError:
            raise ValueError(f"invoice_date '{v}' is not a valid YYYY-MM-DD date")
        return v


    @field_validator("currency")
    @classmethod
    def currency_must_be_iso(cls, v):
        v = v.strip().upper()
        if len(v) != 3 or not v.isalpha():
            raise ValueError(f"currency '{v}' must be a 3-letter code")
        return v

    @field_validator("items")
    @classmethod
    def need_at_least_one_item(cls, v):
        if not v:
            raise ValueError("invoice must have at least one line item")
        return v

    @model_validator(mode="after")
    def total_must_add_up(self):
        subtotal = sum(i.quantity * i.unit_price for i in self.items)
        expected = subtotal + self.tax
        if abs(expected - self.total) > 0.01:
            raise ValueError(
                f"Total mismatch: items add to {subtotal} plus tax {self.tax} "
                f"= {expected}, but the invoice total is {self.total}"
            )
        return self
    

