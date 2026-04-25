import sys
import os
from pathlib import Path

# Add the project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

try:
    from backend.agents.workflow import app_workflow
    from backend.agents.coordinator import TransactionCoordinator
    from backend.database import SessionLocal, init_db
    print("Imports successful!")
except Exception as e:
    print(f"Import failed: {e}")
    import traceback
    traceback.print_exc()
