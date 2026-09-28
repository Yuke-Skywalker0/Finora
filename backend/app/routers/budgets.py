from .finance_modules import make_router
from ..models import BudgetCreate
from ..db import budgets
router=make_router(budgets,"/api/budgets","budgets",["category","month","limit"],BudgetCreate)
