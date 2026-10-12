from typing import Dict, Any
import config


def calculate_risk_score(credit_score: float, monthly_income: float, monthly_debt: float) -> float:
    credit_risk = max(0, (700 - credit_score) / 7)
    
    income_risk = 0
    if monthly_income > 0:
        if monthly_income < config.MIN_INCOME:
            income_risk = 50
        elif monthly_income < config.MIN_INCOME * 1.5:
            income_risk = 25
    
    debt_risk = 0
    if monthly_income > 0:
        dti = monthly_debt / monthly_income
        if dti > 0.5:
            debt_risk = 40
        elif dti > 0.4:
            debt_risk = 25
        elif dti > 0.3:
            debt_risk = 10
    
    behavioral_risk = 15
    
    total_score = (
        credit_risk * config.RISK_WEIGHTS['credit'] +
        income_risk * config.RISK_WEIGHTS['income'] +
        debt_risk * config.RISK_WEIGHTS['debt'] +
        behavioral_risk * config.RISK_WEIGHTS['behavioral']
    )
    
    return min(100, max(0, total_score))


def get_risk_level(risk_score: float) -> str:
    if risk_score <= 40:
        return "LOW"
    elif risk_score <= 60:
        return "MEDIUM"
    else:
        return "HIGH"


def assess_risk(application: Dict[str, Any]) -> Dict[str, Any]:
    credit_score = application.get('credit_score', 600)
    monthly_income = application.get('monthly_income', 0)
    monthly_debt = application.get('monthly_debt_payments', 0)
    
    risk_score = calculate_risk_score(credit_score, monthly_income, monthly_debt)
    risk_level = get_risk_level(risk_score)
    
    is_credit_acceptable = credit_score >= config.MIN_CREDIT_SCORE
    
    return {
        'risk_score': round(risk_score, 2),
        'risk_level': risk_level,
        'is_credit_acceptable': is_credit_acceptable,
        'is_risky': risk_score > config.RISK_SCORE_THRESHOLD
    }