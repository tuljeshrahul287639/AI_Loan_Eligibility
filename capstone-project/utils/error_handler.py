import time
from functools import wraps
import config

def retry_with_exponential_backoff(max_retries=None, initial_delay=None, exponential_base=None):
    """Decorator for retry with exponential backoff"""
    max_retries = max_retries or config.MAX_RETRIES
    initial_delay = initial_delay or config.RETRY_INITIAL_DELAY
    exponential_base = exponential_base or config.RETRY_EXPONENTIAL_BASE
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    time.sleep(delay)
                    delay *= exponential_base
        return wrapper
    return decorator

def validate_application_data(application):
    """Validate required application fields"""
    required_fields = [
        'applicant_id', 'name', 'monthly_income',
        'monthly_expenses', 'credit_score', 'loan_amount', 'existing_debts'
    ]
    
    for field in required_fields:
        if field not in application or application[field] is None:
            return False
    
    # Validate data types and ranges
    if not isinstance(application['monthly_income'], (int, float)):
        return False
    if not isinstance(application['credit_score'], (int, float)):
        return False
    if application['credit_score'] < 0 or application['credit_score'] > 850:
        return False
    
    return True

def safe_get(obj, key, default=None):
    """Safely get dictionary value"""
    try:
        return obj.get(key, default)
    except:
        return default