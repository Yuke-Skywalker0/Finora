from .finance_modules import make_router
from ..models import RecurringCreate
from ..db import recurring
router=make_router(recurring,"/api/recurring","recurring",["description","type","amount","category","frequency","next_date","account_id"],RecurringCreate)
