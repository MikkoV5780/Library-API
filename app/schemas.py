from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import date

class BookBase(BaseModel):
    title: str
    author: str

class BookCreate(BookBase):
    serial_number: int = Field(..., ge=100000, le=999999, description="6-cyfrowy numer seryjny")
    
    @validator('serial_number')
    def serial_number_must_be_six_digits(cls, v):
        if not (100000 <= v <= 999999):
            raise ValueError('Numer seryjny musi być 6-cyfrową liczbą')
        return v

class BookUpdate(BaseModel):
    is_borrowed: Optional[bool] = None
    borrowed_date: Optional[date] = None
    borrower_id: Optional[int] = Field(None, ge=100000, le=999999, description="6-cyfrowe ID wypożyczającego")

    @validator('borrower_id')
    def borrower_id_must_be_six_digits_if_provided(cls, v):
        if v is not None and not (100000 <= v <= 999999):
            raise ValueError('ID wypożyczającego musi być 6-cyfrową liczbą')
        return v
    
    @validator('borrowed_date')
    def borrowed_date_validation(cls, v, values):
        # Jeśli is_borrowed jest False, borrowed_date powinno być None
        if 'is_borrowed' in values and values['is_borrowed'] is False and v is not None:
            raise ValueError('Data wypożyczenia musi być None, gdy książka nie jest wypożyczona')
        return v

class Book(BookBase):
    serial_number: int
    is_borrowed: bool
    borrowed_date: Optional[date] = None
    borrower_id: Optional[int] = None

    class Config:
        orm_mode = True