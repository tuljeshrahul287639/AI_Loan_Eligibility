import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import json
from faker import Faker
from pathlib import Path
import random
import config

fake = Faker()

def generate_synthetic_application():
    """Generate single realistic loan application"""
    income = random.choice([2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000])
    
    return {
        'applicant_id': f"APP-{fake.numerify('######')}",
        'name': fake.name(),
        'monthly_income': income,
        'monthly_expenses': round(income * random.uniform(0.3, 0.7), 2),
        'credit_score': random.randint(500, 800),
        'loan_amount': random.choice([150000, 200000, 250000, 300000, 350000, 400000]),
        'existing_debts': round(random.uniform(500, 2000), 2),
        'years_employed': random.randint(1, 25),
        'employment_type': random.choice(['Full-time', 'Part-time', 'Self-employed']),
        'prior_delinquencies': random.randint(0, 3),
        'bankruptcy_history': random.choice([True, False]),
        'recent_inquiries': random.randint(0, 5)
    }

def generate_and_save_synthetic_data(count=50):
    """Generate and save synthetic applications"""
    applications = [generate_synthetic_application() for _ in range(count)]
    
    file_path = Path(config.SYNTHETIC_DATA_FILE)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(file_path, 'w') as f:
        json.dump(applications, f, indent=2)
    
    print(f"✅ Generated {count} synthetic applications -> {file_path}")
    return applications

def load_sample_applications():
    """Load applications from file"""
    file_path = Path(config.SYNTHETIC_DATA_FILE)
    
    if not file_path.exists():
        return generate_and_save_synthetic_data(config.NUM_SYNTHETIC_APPLICATIONS)
    
    with open(file_path, 'r') as f:
        return json.load(f)

if __name__ == "__main__":
    generate_and_save_synthetic_data(config.NUM_SYNTHETIC_APPLICATIONS)