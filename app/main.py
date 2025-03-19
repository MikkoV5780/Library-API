from fastapi import FastAPI, Request, Depends, Form, status, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional
import time
import sqlalchemy.exc
from datetime import date
import uvicorn

from .database import engine, Base, get_db
from .api import books
from .models import Book as BookModel
from .schemas import BookCreate, BookUpdate

# Próbuj połączyć się z bazą danych z ponowną próbą
max_retries = 30
for i in range(max_retries):
    try:
        # Utworzenie połączenia testowego
        with engine.connect() as connection:
            # Jeśli dotarliśmy tutaj, połączenie powiodło się
            break
    except sqlalchemy.exc.OperationalError as e:
        # Jeśli to ostatnia próba, podnieś wyjątek
        if i == max_retries - 1:
            raise
        # W przeciwnym razie poczekaj i spróbuj ponownie
        print(f"Nie można połączyć się z bazą danych. Ponowna próba za 1 sekundę... ({i+1}/{max_retries})")
        time.sleep(1)

# Tworzenie tabel
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="System Biblioteczny API",
    description="API do zarządzania książkami w bibliotece",
    version="1.0.0"
)

# Montowanie plików statycznych
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Konfiguracja szablonów
templates = Jinja2Templates(directory="app/templates")

# Dodanie routera API
app.include_router(books.router, prefix="/api/books", tags=["api"])

# UI Routes

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse(
        "index.html", 
        {"request": request, "active_page": "home"}
    )

@app.get("/books", response_class=HTMLResponse)
async def list_books(
    request: Request, 
    is_borrowed: Optional[str] = Query(None), 
    message: Optional[str] = None, 
    message_type: Optional[str] = "success",
    db: Session = Depends(get_db)
):
    query = db.query(BookModel)
    
    # Konwertuj parametr is_borrowed z string na boolean tylko jeśli nie jest pusty
    is_borrowed_bool = None
    if is_borrowed == "true":
        is_borrowed_bool = True
    elif is_borrowed == "false":
        is_borrowed_bool = False
    
    # Filtruj tylko wtedy, gdy mamy konkretną wartość boolean
    if is_borrowed_bool is not None:
        query = query.filter(BookModel.is_borrowed == is_borrowed_bool)
        
    books = query.all()
    
    return templates.TemplateResponse(
        "books.html", 
        {
            "request": request, 
            "books": books, 
            "is_borrowed": is_borrowed,  # Przekazujemy oryginalną wartość string
            "active_page": "books",
            "message": message,
            "message_type": message_type
        }
    )

@app.get("/books/add", response_class=HTMLResponse)
async def add_book_form(request: Request):
    return templates.TemplateResponse(
        "add_book.html", 
        {"request": request, "active_page": "add_book"}
    )

@app.post("/books/add")
async def add_book(
    serial_number: int = Form(...),
    title: str = Form(...),
    author: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        # Sprawdź, czy książka o podanym numerze seryjnym już istnieje
        db_book = db.query(BookModel).filter(BookModel.serial_number == serial_number).first()
        if db_book:
            return RedirectResponse(
                url=f"/books?message=Książka o numerze {serial_number} już istnieje&message_type=danger",
                status_code=status.HTTP_303_SEE_OTHER
            )
        
        # Utwórz nową książkę
        book_data = BookCreate(serial_number=serial_number, title=title, author=author)
        db_book = BookModel(**book_data.dict())
        db.add(db_book)
        db.commit()
        
        return RedirectResponse(
            url=f"/books?message=Książka '{title}' została pomyślnie dodana&message_type=success",
            status_code=status.HTTP_303_SEE_OTHER
        )
    except Exception as e:
        return RedirectResponse(
            url=f"/books?message=Błąd podczas dodawania książki: {str(e)}&message_type=danger",
            status_code=status.HTTP_303_SEE_OTHER
        )

@app.get("/books/{serial_number}/borrow", response_class=HTMLResponse)
async def borrow_book_form(
    request: Request,
    serial_number: int,
    db: Session = Depends(get_db)
):
    book = db.query(BookModel).filter(BookModel.serial_number == serial_number).first()
    if not book:
        return RedirectResponse(
            url=f"/books?message=Książka o numerze {serial_number} nie istnieje&message_type=danger",
            status_code=status.HTTP_303_SEE_OTHER
        )
        
    if book.is_borrowed:
        return RedirectResponse(
            url=f"/books?message=Książka jest już wypożyczona&message_type=danger",
            status_code=status.HTTP_303_SEE_OTHER
        )
        
    return templates.TemplateResponse(
        "borrow_book.html", 
        {"request": request, "book": book, "active_page": "books"}
    )

@app.post("/books/{serial_number}/borrow")
async def borrow_book(
    serial_number: int,
    borrower_id: int = Form(...),
    db: Session = Depends(get_db)
):
    book = db.query(BookModel).filter(BookModel.serial_number == serial_number).first()
    if not book:
        return RedirectResponse(
            url=f"/books?message=Książka o numerze {serial_number} nie istnieje&message_type=danger",
            status_code=status.HTTP_303_SEE_OTHER
        )
        
    if book.is_borrowed:
        return RedirectResponse(
            url=f"/books?message=Książka jest już wypożyczona&message_type=danger",
            status_code=status.HTTP_303_SEE_OTHER
        )
    
    try:
        # Aktualizuj status książki
        book_update_data = BookUpdate(
            is_borrowed=True,
            borrowed_date=date.today(),
            borrower_id=borrower_id
        )
        
        # Zastosuj aktualizacje
        for key, value in book_update_data.dict(exclude_unset=True).items():
            setattr(book, key, value)
        
        db.commit()
        
        return RedirectResponse(
            url=f"/books?message=Książka została wypożyczona&message_type=success",
            status_code=status.HTTP_303_SEE_OTHER
        )
    except Exception as e:
        return RedirectResponse(
            url=f"/books?message=Błąd podczas wypożyczania książki: {str(e)}&message_type=danger",
            status_code=status.HTTP_303_SEE_OTHER
        )

@app.post("/books/{serial_number}/return")
async def return_book(
    serial_number: int,
    db: Session = Depends(get_db)
):
    book = db.query(BookModel).filter(BookModel.serial_number == serial_number).first()
    if not book:
        return RedirectResponse(
            url=f"/books?message=Książka o numerze {serial_number} nie istnieje&message_type=danger",
            status_code=status.HTTP_303_SEE_OTHER
        )
        
    if not book.is_borrowed:
        return RedirectResponse(
            url=f"/books?message=Książka nie jest wypożyczona&message_type=danger",
            status_code=status.HTTP_303_SEE_OTHER
        )
    
    try:
        # Aktualizuj status książki
        book_update_data = BookUpdate(
            is_borrowed=False,
            borrowed_date=None,
            borrower_id=None
        )
        
        # Zastosuj aktualizacje
        for key, value in book_update_data.dict(exclude_unset=True).items():
            setattr(book, key, value)
        
        db.commit()
        
        return RedirectResponse(
            url=f"/books?message=Książka została zwrócona&message_type=success",
            status_code=status.HTTP_303_SEE_OTHER
        )
    except Exception as e:
        return RedirectResponse(
            url=f"/books?message=Błąd podczas zwracania książki: {str(e)}&message_type=danger",
            status_code=status.HTTP_303_SEE_OTHER
        )

@app.post("/books/{serial_number}/delete")
async def delete_book(
    serial_number: int,
    db: Session = Depends(get_db)
):
    book = db.query(BookModel).filter(BookModel.serial_number == serial_number).first()
    if not book:
        return RedirectResponse(
            url=f"/books?message=Książka o numerze {serial_number} nie istnieje&message_type=danger",
            status_code=status.HTTP_303_SEE_OTHER
        )
    
    try:
        db.delete(book)
        db.commit()
        
        return RedirectResponse(
            url=f"/books?message=Książka została usunięta&message_type=success",
            status_code=status.HTTP_303_SEE_OTHER
        )
    except Exception as e:
        return RedirectResponse(
            url=f"/books?message=Błąd podczas usuwania książki: {str(e)}&message_type=danger",
            status_code=status.HTTP_303_SEE_OTHER
        )

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)