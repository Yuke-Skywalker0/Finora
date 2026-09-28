from datetime import date
from typing import Literal
from pydantic import BaseModel, Field, field_validator

class GoogleLogin(BaseModel):
    credential: str = Field(min_length=20)

class AccountCreate(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    type: Literal["cash", "bank", "card", "wallet"] = "bank"
    initial_balance: float = Field(default=0, ge=-100_000_000, le=100_000_000)

class TransactionCreate(BaseModel):
    type: Literal["income", "expense"]
    amount: float = Field(gt=0, le=100_000_000)
    category: str = Field(min_length=1, max_length=50)
    description: str = Field(min_length=1, max_length=120)
    date: date
    account_id: str | None = None

    @field_validator("description", "category")
    @classmethod
    def clean_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Campo obbligatorio.")
        return value

class TransactionUpdate(TransactionCreate):
    pass

class TransactionOut(BaseModel):
    id: str
    type: Literal["income", "expense"]
    amount: float
    category: str
    description: str
    date: str

class BudgetCreate(BaseModel):
    category: str = Field(min_length=1, max_length=50)
    month: str = Field(pattern=r"^\d{4}-\d{2}$")
    limit: float = Field(gt=0, le=100_000_000)

class GoalCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    target_amount: float = Field(gt=0, le=100_000_000)
    current_amount: float = Field(ge=0, le=100_000_000)
    deadline: date | None = None

class RecurringCreate(BaseModel):
    description: str = Field(min_length=1, max_length=120)
    type: Literal["income", "expense"]
    amount: float = Field(gt=0, le=100_000_000)
    category: str = Field(min_length=1, max_length=50)
    frequency: Literal["weekly", "monthly", "yearly"]
    next_date: date
    account_id: str | None = None
