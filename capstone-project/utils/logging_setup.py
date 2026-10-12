import logging
from pathlib import Path
import config

def setup_logging():
    log_path = Path(config.LOG_FILE_PATH)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format=config.LOG_FORMAT,
        handlers=[
            logging.FileHandler(log_path),
            logging.StreamHandler()
        ]
    )

def log_agent_decision(agent_name, decision, confidence):
    logger = logging.getLogger(agent_name)
    logger.info(f"Decision: {decision}, Confidence: {confidence}")

def log_workflow_step(step_name, status):
    logger = logging.getLogger("workflow")
    logger.info(f"Step: {step_name}, Status: {status}")

def log_error_with_context(error, context):
    logger = logging.getLogger("error")
    logger.error(f"Error: {error}, Context: {context}")