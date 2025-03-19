from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date

from ..database import get_db
from ..models import Book as BookModel
from ..schemas import Book, BookCreate, BookUpdate

router = APIRouter()

@router.post("/", response_model=Book, status_code=status.HTTP_201_CREATED)
def create_book(book: BookCreate, db: Session = Depends(get_db)):
    """
    Dodaje nową książkę do systemu bibliotecznego.
    """
    # Sprawdź, czy książka o podanym numerze seryjnym i numerze egzemplarza już istnieje
    db_book = db.query(BookModel).filter(
        BookModel.serial_number == book.serial_number,
        BookModel.copy_number == book.copy_number
    ).first()
    
    if db_book:
        raise HTTPException(
            status_code=400, 
            detail=f"Książka o numerze seryjnym {book.serial_number} i numerze egzemplarza {book.copy_number} już istnieje"
        )
    
    db_book = BookModel(**book.dict())
    db.add(db_book)
    db.commit()
    db.refresh(db_book)
    return db_book

@router.get("/", response_model=List[Book])
def read_books(
    is_borrowed: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """
    Pobiera listę wszystkich książek.
    Opcjonalnie można filtrować po statusie wypożyczenia.
    """
    query = db.query(BookModel)
    
    # Zastosuj filtry, jeśli zostały podane
    if is_borrowed is not None:
        query = query.filter(BookModel.is_borrowed == is_borrowed)
    
    books = query.all()
    return books

@router.get("/{serial_number}/{copy_number}", response_model=Book)
def read_book(
    serial_number: int, 
    copy_number: int = 1,
    db: Session = Depends(get_db)
):
    """
    Pobiera szczegóły konkretnej książki na podstawie numeru seryjnego i numeru egzemplarza.
    """
    db_book = db.query(BookModel).filter(
        BookModel.serial_number == serial_number,
        BookModel.copy_number == copy_number
    ).first()
    
    if db_book is None:
        raise HTTPException(status_code=404, detail="Książka nie znaleziona")
    
    return db_book

@router.delete("/{serial_number}/{copy_number}", status_code=status.HTTP_204_NO_CONTENT)
def delete_book(
    serial_number: int, 
    copy_number: int = 1,
    db: Session = Depends(get_db)
):
    """
    Usuwa książkę o podanym numerze seryjnym i numerze egzemplarza.
    """
    db_book = db.query(BookModel).filter(
        BookModel.serial_number == serial_number,
        BookModel.copy_number == copy_number
    ).first()
    
    if db_book is None:
        raise HTTPException(status_code=404, detail="Książka nie znaleziona")
    
    db.delete(db_book)
    db.commit()
    return None

@router.patch("/{serial_number}/{copy_number}", response_model=Book)
def update_book(
    serial_number: int, 
    book_update: BookUpdate, 
    copy_number: int = 1,
    db: Session = Depends(get_db)
):
    """
    Aktualizuje dane książki, w tym status wypożyczenia.
    """
    db_book = db.query(BookModel).filter(
        BookModel.serial_number == serial_number,
        BookModel.copy_number == copy_number
    ).first()
    
    if db_book is None:
        raise HTTPException(status_code=404, detail="Książka nie znaleziona")
    
    update_data = book_update.dict(exclude_unset=True)
    
    # Obsługa specjalnego przypadku zmiany statusu is_borrowed
    if 'is_borrowed' in update_data:
        if update_data['is_borrowed']:
            # Książka jest oznaczana jako wypożyczona
            
            # Ustaw borrowed_date na dzisiaj, jeśli nie podano
            if 'borrowed_date' not in update_data or update_data['borrowed_date'] is None:
                update_data['borrowed_date'] = date.today()
            
            # Wymagaj borrower_id podczas wypożyczania
            if 'borrower_id' not in update_data or update_data['borrower_id'] is None:
                if db_book.borrower_id is None:  # Brak istniejącego wypożyczającego
                    raise HTTPException(
                        status_code=400, 
                        detail="ID wypożyczającego musi być podane przy oznaczaniu książki jako wypożyczonej"
                    )
                # Zachowaj istniejące borrower_id, jeśli jest już ustawione
                update_data['borrower_id'] = db_book.borrower_id
                
        else:
            # Książka jest oznaczana jako zwrócona
            update_data['borrowed_date'] = None
            update_data['borrower_id'] = None
    
    # Zastosuj aktualizacje
    for key, value in update_data.items():
        setattr(db_book, key, value)
    
    db.commit()
    db.refresh(db_book)
    return db_book