from sqlmodel import SQLModel, Field, create_engine, Session, select
from typing import Optional
from config import CONFIG

class Books(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    author: str
    genre: str
    description: str
    price: int
    stock_quantity: int

if CONFIG.db_url == None:
    raise KeyError('No DB URL specified in ENV...')

engine = create_engine(CONFIG.db_url, echo=True)

def get_all_books():
    with Session(engine) as session:
        books = session.exec(select(Books)).all()
        for book in books:
            print(book)
        return books

def get_one_book(id: int):
    with Session(engine) as session:
        book = session.exec(select(Books).where(Books.id == id))
        for b in book:
            return b
    return None