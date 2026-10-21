"""Synthetic customer financial data. Profiles are weighted so a batch produces a realistic spread of outcomes."""
import random

from .schemas import LoanApplication

FIRST = ["Aarav", "Maya", "Liam", "Sofia", "Noah", "Priya", "Ethan", "Chloe", "Rohan", "Emma", "Lucas", "Ananya",
         "Mateo", "Zoe", "Daniel", "Isha", "Oliver", "Grace", "Kabir", "Hannah", "Samuel", "Leila", "Victor", "Nina"]
LAST = ["Mehta", "Carter", "Nguyen", "Rossi", "Patel", "Kim", "Okafor", "Bennett", "Sharma", "Hughes", "Moreau",
        "Fernandez", "Tanaka", "Walker", "Iyer", "Schmidt", "Brooks", "Haddad", "Reddy", "Foster", "Lindqvist", "Diaz"]

PERSONAL_PURPOSES = ["Debt consolidation", "Medical expenses", "Renovation and repairs", "Wedding expenses", "Travel", "Education expenses"]
AUTO_PURPOSES = ["New car purchase", "Used vehicle purchase"]

# weight, score, utilization %, delinquency choices, tenure yrs, debt/income, savings (months of income),
# personal amount / income, collateral LTV
PROFILES = {
    "strong":    dict(w=0.30, score=(745, 820), util=(5, 28),  delinq=[0],             tenure=(3, 15),   debt=(0.00, 0.10), savings=(4, 18),    pl=(0.10, 0.35), ltv=(0.60, 0.78)),
    "average":   dict(w=0.30, score=(690, 760), util=(15, 50), delinq=[0, 0, 0, 1],    tenure=(2, 10),   debt=(0.05, 0.20), savings=(1.5, 6),   pl=(0.15, 0.40), ltv=(0.72, 0.80)),
    "stretched": dict(w=0.25, score=(640, 710), util=(35, 75), delinq=[0, 1, 1, 2],    tenure=(0.8, 5),  debt=(0.15, 0.30), savings=(0.3, 2),   pl=(0.25, 0.60), ltv=(0.78, 0.90)),
    "weak":      dict(w=0.15, score=(570, 660), util=(60, 95), delinq=[1, 2, 3, 4],    tenure=(0.3, 3),  debt=(0.20, 0.38), savings=(0.05, 0.6), pl=(0.30, 0.70), ltv=(0.82, 0.93)),
}
LOAN_TERMS = {"personal": [24, 36, 48, 60], "home": [180, 240, 300, 360], "auto": [36, 48, 60, 72]}
LOAN_LABEL = {"personal": "Personal Loan", "home": "Home Loan", "auto": "Auto Loan"}


def _roundto(value: float, step: int) -> float:
    return float(round(value / step) * step)


def generate_applications(count: int, start_index: int = 1001, seed: int | None = None) -> list[LoanApplication]:
    rng = random.Random(seed)
    out: list[LoanApplication] = []
    for i in range(count):
        n = start_index + i
        prof = PROFILES[rng.choices(list(PROFILES), weights=[p["w"] for p in PROFILES.values()])[0]]
        loan_type = rng.choices(["personal", "home", "auto"], weights=[0.4, 0.3, 0.3])[0]

        income = _roundto(rng.uniform(52_000, 170_000) if loan_type == "home" else rng.uniform(34_000, 150_000), 500)
        monthly = income / 12
        self_employed = rng.random() < 0.25
        age = rng.randint(24, 60)
        if prof is PROFILES["weak"] and rng.random() < 0.06:
            age = rng.choice([19, 20, 66, 68])

        asset_value = None
        if loan_type == "personal":
            amount = min(max(_roundto(income * rng.uniform(*prof["pl"]), 500), 2_500), 75_000)
            purpose = rng.choice(PERSONAL_PURPOSES)
        elif loan_type == "home":
            asset_value = _roundto(income * rng.uniform(3.0, 4.8), 1_000)
            amount = min(max(_roundto(asset_value * rng.uniform(*prof["ltv"]), 1_000), 50_000), 1_000_000)
            purpose = "Home purchase"
        else:
            asset_value = max(_roundto(income * rng.uniform(0.22, 0.55), 500), 7_000)
            amount = max(_roundto(asset_value * rng.uniform(*prof["ltv"]), 500), 5_000)
            purpose = rng.choice(AUTO_PURPOSES)

        out.append(LoanApplication(
            application_id=f"APP-{n}",
            customer_id=f"CUST-{n}",
            full_name=f"{rng.choice(FIRST)} {rng.choice(LAST)}",
            age=age,
            employment_type="Self-employed" if self_employed else "Salaried",
            years_employed=round(rng.uniform(*prof["tenure"]), 1),
            annual_income=income,
            monthly_debt_payments=_roundto(monthly * rng.uniform(*prof["debt"]), 10),
            savings_balance=_roundto(monthly * rng.uniform(*prof["savings"]), 100),
            credit_score=rng.randint(*prof["score"]),
            credit_utilization=float(rng.randint(*prof["util"])),
            delinquencies_24m=rng.choice(prof["delinq"]),
            loan_type=LOAN_LABEL[loan_type],
            loan_amount=amount,
            term_months=rng.choice(LOAN_TERMS[loan_type]),
            purpose=purpose,
            asset_value=asset_value,
        ))
    return out
