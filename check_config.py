from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os

# Create base directory for SQLite database
BASE_DIR = os.path.expanduser("~/Documents/match-invoices")
DATABASE_URL = f'sqlite:///{os.path.join(BASE_DIR, "match_invoices.db")}'

# Create engine and session
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

# Query email config
result = session.execute(text("SELECT * FROM email_config"))
rows = result.fetchall()

print("Email Configurations:")
if not rows:
    print("No email configurations found!")
else:
    for row in rows:
        print(f"Host: {row.host}")
        print(f"Port: {row.port}")
        print(f"Username: {row.username}")
        print("Password: ********")
        print("---")

# Query path config
result = session.execute(text("SELECT * FROM path_config"))
rows = result.fetchall()

print("\nPath Configurations:")
if not rows:
    print("No path configurations found!")
else:
    for row in rows:
        print(f"Statements Path: {row.statements_path}")
        print(f"Invoices Path: {row.invoices_path}")
        print("---")

session.close()
