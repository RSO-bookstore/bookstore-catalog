from typing import Optional
from fastapi import FastAPI, Request, HTTPException, Response
from sqlmodel import Field, Session, SQLModel, create_engine, select
import os


class Books(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    author: str
    genre: str
    price: int
    stock_quantity: int


app = FastAPI()

DB_URL = os.getenv('DB_URL', default=None)

if DB_URL == None:
    raise KeyError('No DB URL specified in ENV...')

esql_url = DB_URL
engine = create_engine(esql_url, echo=True)

@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/books")
def read_books():
    with Session(engine) as session:
        books = session.exec(select(Books)).all()
        for book in books:
            print(book)
        return books


@app.post('/books')
async def create_book(request: Request):
    try:
        json = await request.json()
        title = json['title']
        author = json['author']
        genre = json['genre']
        price = int(json['price'])
        stock_quantity = int(json['stock_quantity'])
    
        book = Books(title=title, author=author, genre=genre, price=price, stock_quantity=stock_quantity)
        session = Session(engine)
        session.add(book)
        session.commit()
        session.close()

        return Response(status_code=201, content='Book added.')

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))