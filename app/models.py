from sqlalchemy import Boolean, Column, String, Integer, Date, CheckConstraint
from .database import Base
from datetime import date

class Book(Base):
    __tablename__ = "books"

    serial_number = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    author = Column(String, nullable=False)
    is_borrowed = Column(Boolean, default=False)
    borrowed_date = Column(Date, nullable=True)
    borrower_id = Column(Integer, nullable=True)
    
    # Dodajemy ograniczenia, aby upewnić się, że serial_number i borrower_id są 6-cyfrowymi liczbami
    __table_args__ = (
        CheckConstraint('serial_number >= 100000 AND serial_number <= 999999', name='check_serial_number_length'),
        CheckConstraint('borrower_id IS NULL OR (borrower_id >= 100000 AND borrower_id <= 999999)', name='check_borrower_id_length'),
    )