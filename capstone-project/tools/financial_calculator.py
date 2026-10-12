from typing import Dict, Any


def calculate_dti(monthly_income: float, monthly_debt: float) -> float:
    if monthly_income <= 0:
        return 1.0
    return monthly_debt / monthly_income


def calculate_loan_payment(loan_amount: float, annual_rate: float = 0.06, years: int = 30) -> float:
    if loan_amount <= 0:
        return 0.0
    
    monthly_rate = annual_rate / 12
    num_payments = years * 12
    
    if monthly_rate == 0:
        return loan_amount / num_payments
    
    payment = loan_amount * (monthly_rate * (1 + monthly_rate) ** num_payments) / \
              ((1 + monthly_rate) ** num_payments - 1)
    
    return round(payment, 2)


def calculate_financial_metrics(application: Dict[str, Any]) -> Dict[str, Any]:
    monthly_income = application.get('monthly_income', 0)
    monthly_debt = application.get('monthly_debt_payments', 0)
    loan_amount = application.get('loan_amount', 0)
    
    current_dti = calculate_dti(monthly_income, monthly_debt)
    monthly_payment = calculate_loan_payment(loan_amount)
    total_debt_with_loan = monthly_debt + monthly_payment
    dti_with_loan = calculate_dti(monthly_income, total_debt_with_loan)
    
    return {
        'monthly_income': monthly_income,
        'monthly_debt': monthly_debt,
        'current_dti': round(current_dti, 4),
        'monthly_payment': monthly_payment,
        'total_debt_with_loan': round(total_debt_with_loan, 2),
        'dti_with_loan': round(dti_with_loan, 4),
        'affordable': dti_with_loan <= 0.43
    }


def validate_financial_health(application: Dict[str, Any]) -> Dict[str, Any]:
    import config
    
    metrics = calculate_financial_metrics(application)
    
    is_income_sufficient = metrics['monthly_income'] >= config.MIN_INCOME
    is_dti_acceptable = metrics['dti_with_loan'] <= config.MAX_DTI_RATIO
    is_affordable = metrics['affordable']
    
    return {
        'metrics': metrics,
        'is_income_sufficient': is_income_sufficient,
        'is_dti_acceptable': is_dti_acceptable,
        'is_affordable': is_affordable,
        'is_financially_healthy': is_income_sufficient and is_dti_acceptable
    }