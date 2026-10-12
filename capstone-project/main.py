import sys
from orchestrator import LoanProcessingOrchestrator
from data.synthetic_data_generator import load_sample_applications
from utils.logging_setup import setup_logging

setup_logging()

def show_result(result):
    print("\n" + "="*60)
    print(f"Applicant: {result.get('applicant_name')}")
    print(f"Decision: {result.get('decision')}")
    print(f"Confidence: {result.get('confidence_score'):.1%}")
    print(f"DTI: {result.get('financial_analysis', {}).get('dti_percentage', 0):.1f}%")
    print(f"Risk Score: {result.get('risk_analysis', {}).get('overall_score', 0)}/100")
    print(f"Duration: {result.get('workflow_duration_seconds', 0):.2f}s")
    print("="*60 + "\n")

def process_single():
    print("\n🏦 Processing Single Application...\n")
    apps = load_sample_applications()
    orchestrator = LoanProcessingOrchestrator()
    result = orchestrator.process_application(apps[0])
    show_result(result)

def process_batch(count):
    print(f"\n🏦 Processing {count} Applications...\n")
    apps = load_sample_applications()[:count]
    orchestrator = LoanProcessingOrchestrator()
    results = []
    
    for app in apps:
        result = orchestrator.process_application(app)
        results.append(result)
        show_result(result)
    
    print("="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Total: {len(results)}")
    print(f"Approved: {sum(1 for r in results if r.get('decision') == 'APPROVE')}")
    print(f"Rejected: {sum(1 for r in results if r.get('decision') == 'REJECT')}")
    print(f"Review: {sum(1 for r in results if r.get('decision') in ['REVIEW', 'ESCALATE'])}")
    print("="*60 + "\n")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "single":
            process_single()
        elif sys.argv[1] == "batch":
            count = int(sys.argv[2]) if len(sys.argv) > 2 else 10
            process_batch(count)
    else:
        process_single()