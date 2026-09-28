from .finance_modules import make_router
from ..models import GoalCreate
from ..db import goals
router=make_router(goals,"/api/goals","goals",["name","target_amount","current_amount","deadline"],GoalCreate)
