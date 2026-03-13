"""One-shot registry maintenance. Run on VM to fix bad labels."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.database import get_connection, init_db
from src.registry_manager import maintain_registry

init_db()
conn = get_connection()
stats = maintain_registry(conn)
print(stats, flush=True)
conn.close()
