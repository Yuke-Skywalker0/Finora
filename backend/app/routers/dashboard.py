from collections import defaultdict
import math
from datetime import date, datetime
from calendar import monthrange

from fastapi import APIRouter, Depends

from ..db import transactions, accounts, budgets, goals, recurring
from ..security import current_user_id, owner_key
from .transactions import decode
from ..security import decrypt_text

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

def decode_account_balance(doc):
    return decrypt_text(doc["balance_enc"])

def decode_account(doc):
    return decrypt_text(doc["name_enc"])

def decode_account_type(doc):
    return decrypt_text(doc["type_enc"])

MONTHS_IT = ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu", "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]

def decode_module(doc, fields):
    out={"id":str(doc["_id"])}
    for k in fields:
        v=doc.get(k)
        if v is not None:v=decrypt_text(v)
        if k in {"limit","target_amount","current_amount","amount"} and v is not None:v=float(v)
        out[k]=v
    return out

def shift_month(year: int, month: int, delta: int):
    index = year * 12 + (month - 1) + delta
    return index // 12, index % 12 + 1

@router.get("")
def dashboard(user_id: str = Depends(current_user_id)):
    key = owner_key(user_id)
    docs = list(transactions.find({"owner_key": key}).sort("created_at", -1))
    items = [decode(doc) for doc in docs]

    today = date.today()
    current_month = today.month
    current_year = today.year

    month_items = [
        item for item in items
        if (d := date.fromisoformat(item["date"])).month == current_month
        and d.year == current_year
    ]

    income = sum(x["amount"] for x in month_items if x["type"] == "income")
    expenses = sum(x["amount"] for x in month_items if x["type"] == "expense")
    savings = income - expenses

    # Se esistono conti, il saldo disponibile deriva dai saldi iniziali + movimenti collegati.
    # Manteniamo il fallback storico per installazioni che non hanno ancora creato conti.
    account_rows = []
    for account in accounts.find({"owner_key": key}).sort("created_at", 1):
        account_id = str(account["_id"])
        balance = float(decode_account_balance(account))
        for item in items:
            if item.get("account_id") == account_id:
                balance += item["amount"] if item["type"] == "income" else -item["amount"]
        account_rows.append({
            "id": account_id,
            "name": decode_account(account),
            "type": decode_account_type(account),
            "balance": round(balance, 2)
        })
    balance = sum(x["balance"] for x in account_rows) if account_rows else sum(
        x["amount"] if x["type"] == "income" else -x["amount"]
        for x in items
    )

    categories = defaultdict(float)
    for item in month_items:
        if item["type"] == "expense":
            categories[item["category"]] += item["amount"]

    labels, monthly_income, monthly_expenses = [], [], []

    for delta in range(-5, 1):
        year, month = shift_month(current_year, current_month, delta)
        labels.append(f"{MONTHS_IT[month - 1]} {str(year)[2:]}")

        selected = [
            item for item in items
            if (d := date.fromisoformat(item["date"])).year == year
            and d.month == month
        ]

        monthly_income.append(round(sum(x["amount"] for x in selected if x["type"] == "income"), 2))
        monthly_expenses.append(round(sum(x["amount"] for x in selected if x["type"] == "expense"), 2))

    current_ym=f"{current_year:04d}-{current_month:02d}"
    budget_rows=[decode_module(x,["category","month","limit"]) for x in budgets.find({"owner_key":key,"month":current_ym})]
    for b in budget_rows:
        b["spent"]=round(categories.get(b["category"],0),2)
        b["remaining"]=round(b["limit"]-b["spent"],2)
        b["percentage"]=round(min(100,b["spent"]/b["limit"]*100),1)
    goal_rows=[decode_module(x,["name","target_amount","current_amount","deadline"]) for x in goals.find({"owner_key":key}).sort("created_at",1)]
    for g in goal_rows:g["percentage"]=round(min(100,g["current_amount"]/g["target_amount"]*100),1)
    recurring_rows=[decode_module(x,["description","type","amount","category","frequency","next_date","account_id"]) for x in recurring.find({"owner_key":key}).sort("created_at",-1)]
    return {
        "summary": {
            "balance": round(balance, 2),
            "income": round(income, 2),
            "expenses": round(expenses, 2),
            "savings": round(savings, 2),
            "savings_percentage": round((savings / income * 100) if income else 0, 1),
            "accounts": account_rows
        },
        "categories": {k: round(v, 2) for k, v in categories.items()},
        "monthly": {
            "labels": labels,
            "income": monthly_income,
            "expenses": monthly_expenses
        },
        "transactions": items[:20],
        "budgets": budget_rows,
        "goals": goal_rows,
        "recurring": recurring_rows
    }


@router.get("/smart")
def smart_finance(user_id: str = Depends(current_user_id)):
    """Rule-based financial insights. No external AI or cross-user data is used."""
    key = owner_key(user_id)
    docs = list(transactions.find({"owner_key": key}).sort("date", 1))
    items = [decode(doc) for doc in docs]
    today = date.today()
    cur_y, cur_m = today.year, today.month
    prev_y, prev_m = shift_month(cur_y, cur_m, -1)

    def rows_for(y, m):
        return [x for x in items if (d := date.fromisoformat(x["date"])).year == y and d.month == m]
    current = rows_for(cur_y, cur_m)
    previous = rows_for(prev_y, prev_m)
    current_exp = sum(x["amount"] for x in current if x["type"] == "expense")
    prev_exp = sum(x["amount"] for x in previous if x["type"] == "expense")
    current_inc = sum(x["amount"] for x in current if x["type"] == "income")

    cat_now, cat_prev = defaultdict(float), defaultdict(float)
    for x in current:
        if x["type"] == "expense": cat_now[x["category"]] += x["amount"]
    for x in previous:
        if x["type"] == "expense": cat_prev[x["category"]] += x["amount"]

    account_balances = []
    for account in accounts.find({"owner_key": key}):
        bal = float(decode_account_balance(account))
        aid = str(account["_id"])
        for x in items:
            if x.get("account_id") == aid:
                bal += x["amount"] if x["type"] == "income" else -x["amount"]
        account_balances.append(bal)
    balance = sum(account_balances) if account_balances else sum(x["amount"] if x["type"] == "income" else -x["amount"] for x in items)

    rec_rows = [decode_module(x,["description","type","amount","category","frequency","next_date","account_id"]) for x in recurring.find({"owner_key":key})]
    horizon = today.fromordinal(today.toordinal() + 30)
    def within_30(r):
        try: d=date.fromisoformat(r["next_date"])
        except Exception: return False
        return today <= d <= horizon
    upcoming = [r for r in rec_rows if within_30(r)]
    rec_income = sum(r["amount"] for r in upcoming if r["type"] == "income")
    rec_expense = sum(r["amount"] for r in upcoming if r["type"] == "expense")

    budgets_rows = [decode_module(x,["category","month","limit"]) for x in budgets.find({"owner_key":key,"month":f"{cur_y:04d}-{cur_m:02d}"})]
    budget_alerts=[]
    for b in budgets_rows:
        spent=cat_now.get(b["category"],0)
        pct=(spent/b["limit"]*100) if b["limit"] else 0
        if pct >= 80:
            budget_alerts.append({"category":b["category"],"percentage":round(pct,1),"remaining":round(b["limit"]-spent,2)})

    insights=[]
    if current_exp == 0 and current_inc == 0:
        insights.append({"kind":"info","title":"Inizia a registrare i movimenti","text":"Con alcune transazioni Finora potrà costruire trend, previsioni e avvisi personalizzati."})
    else:
        if prev_exp > 0 and current_exp > prev_exp * 1.15:
            pct=(current_exp-prev_exp)/prev_exp*100
            insights.append({"kind":"warning","title":"Le uscite stanno crescendo","text":f"Questo mese hai speso {pct:.0f}% in più rispetto al mese scorso."})
        elif prev_exp > 0 and current_exp < prev_exp * 0.85:
            pct=(prev_exp-current_exp)/prev_exp*100
            insights.append({"kind":"positive","title":"Stai contenendo le uscite","text":f"Le uscite sono inferiori del {pct:.0f}% rispetto al mese scorso."})
        top=sorted(cat_now.items(), key=lambda x:x[1], reverse=True)[:1]
        if top:
            insights.append({"kind":"info","title":f"Categoria principale: {top[0][0]}","text":f"Rappresenta {top[0][1]/current_exp*100:.0f}% delle uscite di questo mese."})
        if current_inc > 0:
            rate=(current_inc-current_exp)/current_inc*100
            if rate < 10:
                insights.append({"kind":"warning","title":"Margine di risparmio ridotto","text":f"Il margine attuale è circa del {max(rate,0):.0f}% delle entrate del mese."})
            elif rate >= 30:
                insights.append({"kind":"positive","title":"Buon margine di risparmio","text":f"Il risparmio corrente è circa il {rate:.0f}% delle entrate del mese."})
        for category, amount in sorted(cat_now.items(), key=lambda x:x[1], reverse=True):
            old=cat_prev.get(category,0)
            if old > 0 and amount > old*1.25:
                insights.append({"kind":"warning","title":f"Aumento in {category}","text":f"La spesa è aumentata del {(amount-old)/old*100:.0f}% rispetto al mese scorso."})
                break

    for b in sorted(budget_alerts,key=lambda x:x["percentage"],reverse=True)[:2]:
        insights.append({"kind":"warning" if b["percentage"]<100 else "danger","title":f"Budget {b['category']} quasi esaurito","text":f"Hai utilizzato il {b['percentage']:.0f}% del budget. Restano {money_fmt(b['remaining'])}."})

    goal_data=[]
    for g in goals.find({"owner_key":key}).sort("created_at",1):
        row=decode_module(g,["name","target_amount","current_amount","deadline"])
        remaining=max(0,row["target_amount"]-row["current_amount"])
        days=None
        monthly_needed=None
        if row.get("deadline"):
            try:
                deadline=date.fromisoformat(row["deadline"])
                days=max(1,(deadline-today).days)
                monthly_needed=remaining/(days/30.4375)
            except Exception: pass
        goal_data.append({"name":row["name"],"target":row["target_amount"],"current":row["current_amount"],"remaining":round(remaining,2),"days_to_deadline":days,"monthly_needed":round(monthly_needed,2) if monthly_needed is not None else None})
        if monthly_needed and monthly_needed > max(current_inc-current_exp,0):
            insights.append({"kind":"info","title":f"Obiettivo: {row['name']}","text":f"Per arrivare alla scadenza servirebbero circa {money_fmt(monthly_needed)} al mese."})

    daily_current = current_exp / max(today.day,1)
    base_30 = balance + rec_income - rec_expense
    forecast_30 = base_30 - daily_current * 30
    forecast_90 = balance + rec_income*3 - rec_expense*3 - daily_current*90
    if forecast_30 < 0:
        insights.insert(0,{"kind":"danger","title":"Proiezione sotto zero","text":f"Con l'andamento attuale la proiezione a 30 giorni è {money_fmt(forecast_30)}. Valuta le prossime uscite."})

    return {
        "generated_at": datetime.utcnow().isoformat(),
        "forecast": {"current_balance":round(balance,2),"income_30":round(rec_income,2),"expenses_30":round(rec_expense,2),"estimated_30":round(forecast_30,2),"estimated_90":round(forecast_90,2)},
        "recurring": {"income_30":round(rec_income,2),"expenses_30":round(rec_expense,2),"count":len(upcoming)},
        "budget_alerts": budget_alerts,
        "goals": goal_data,
        "insights": insights[:8]
    }

def money_fmt(value):
    return f"€ {value:,.2f}".replace(",","X").replace(".",",").replace("X",".")


@router.get("/analytics")
def analytics(user_id: str = Depends(current_user_id)):
    key = owner_key(user_id)
    docs = list(transactions.find({"owner_key": key}).sort("date", 1))
    items = [decode(doc) for doc in docs]
    today = date.today()
    cur_y, cur_m = today.year, today.month
    prev_y, prev_m = shift_month(cur_y, cur_m, -1)

    def totals(rows):
        inc = sum(x["amount"] for x in rows if x["type"] == "income")
        exp = sum(x["amount"] for x in rows if x["type"] == "expense")
        return round(inc, 2), round(exp, 2), round(inc-exp, 2)

    current = [x for x in items if (d:=date.fromisoformat(x["date"])).year == cur_y and d.month == cur_m]
    previous = [x for x in items if (d:=date.fromisoformat(x["date"])).year == prev_y and d.month == prev_m]
    ci, ce, cs = totals(current)
    pi, pe, ps = totals(previous)

    days_elapsed = today.day
    days_in_month = monthrange(cur_y, cur_m)[1]
    daily_expense = round(ce / days_elapsed, 2) if days_elapsed else 0
    forecast = round(daily_expense * days_in_month, 2)

    categories = defaultdict(float)
    for x in current:
        if x["type"] == "expense": categories[x["category"]] += x["amount"]
    top_categories = sorted(
        [{"category": k, "amount": round(v, 2), "percentage": round(v/ce*100, 1) if ce else 0} for k,v in categories.items()],
        key=lambda x: x["amount"], reverse=True
    )[:8]

    annual = []
    for delta in range(-11, 1):
        y, m = shift_month(cur_y, cur_m, delta)
        rows = [x for x in items if (d:=date.fromisoformat(x["date"])).year == y and d.month == m]
        inc, exp, sav = totals(rows)
        annual.append({"label": f"{MONTHS_IT[m-1]} {str(y)[2:]}", "year": y, "month": m, "income": inc, "expenses": exp, "savings": sav})

    avg_monthly_expense = round(sum(x["expenses"] for x in annual)/len(annual), 2) if annual else 0
    avg_monthly_income = round(sum(x["income"] for x in annual)/len(annual), 2) if annual else 0
    annual_income = round(sum(x["amount"] for x in items if x["type"] == "income" and date.fromisoformat(x["date"]).year == cur_y),2)
    annual_expenses = round(sum(x["amount"] for x in items if x["type"] == "expense" and date.fromisoformat(x["date"]).year == cur_y),2)

    account_rows=[]
    for account in accounts.find({"owner_key":key}):
        bal=float(decode_account_balance(account))
        aid=str(account["_id"])
        for x in items:
            if x.get("account_id")==aid: bal += x["amount"] if x["type"]=="income" else -x["amount"]
        account_rows.append(bal)
    net_worth=round(sum(account_rows),2) if account_rows else round(sum(x["amount"] if x["type"]=="income" else -x["amount"] for x in items),2)

    return {
        "period": {"year": cur_y, "month": cur_m, "days_elapsed": days_elapsed, "days_in_month": days_in_month},
        "current": {"income": ci, "expenses": ce, "savings": cs},
        "previous": {"income": pi, "expenses": pe, "savings": ps},
        "changes": {
            "income": round(ci-pi,2), "expenses": round(ce-pe,2), "savings": round(cs-ps,2),
            "income_percentage": round((ci-pi)/pi*100,1) if pi else None,
            "expenses_percentage": round((ce-pe)/pe*100,1) if pe else None
        },
        "forecast": {"daily_expense": daily_expense, "end_of_month_expenses": forecast},
        "averages": {"monthly_income": avg_monthly_income, "monthly_expenses": avg_monthly_expense, "monthly_savings": round(avg_monthly_income-avg_monthly_expense,2)},
        "year": {"income": annual_income, "expenses": annual_expenses, "savings": round(annual_income-annual_expenses,2)},
        "net_worth": net_worth,
        "top_categories": top_categories,
        "monthly": annual,
    }
