from sqlalchemy import inspect
from database import engine, Base
from models import Book

# Sprawdź strukturę tabeli w bazie danych
inspector = inspect(engine)
print("==== STRUKTURA TABELI W BAZIE DANYCH ====")
for table_name in inspector.get_table_names():
    print(f"Tabela: {table_name}")
    for column in inspector.get_columns(table_name):
        print(f"  - {column['name']}: {column['type']}")