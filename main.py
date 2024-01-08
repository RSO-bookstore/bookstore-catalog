import os
from typing import Optional, List
from fastapi import FastAPI, Request, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi_utils.tasks import repeat_every
from sqlmodel import Field, Session, SQLModel, create_engine, select
import os
from pydantic import BaseModel
from dotenv import dotenv_values
# from prometheus_client import Counter, make_asgi_app
import logging
import time
import uuid
from enum import Enum
from app_metadata import APP_METADATA
import translators as ts
from strawberry.fastapi import GraphQLRouter
from config import CONFIG
from database import engine, Books
from schema import schema
from metrics import metrics_app


logger = logging.getLogger('uvicorn')

# CONFIG = Config()
app = FastAPI(title=APP_METADATA['title'], 
              summary=APP_METADATA['summary'], 
              description=APP_METADATA['description'], 
              contact=APP_METADATA['contact'],
              openapi_tags=APP_METADATA['tags_metadata'],
              root_path="/bookstore-catalog" if CONFIG.catalog_host != 'localhost' else "",
              docs_url='/openapi')

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Add prometheus asgi middleware to route /metrics requests
# metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    rid = None
    try:
        rid = request.headers.get('rid')
    except:
        pass
    idem = uuid.uuid4()
    if rid != None:
        idem = rid
    logger.info(f"method={str.upper(request.method)} rid={idem} app={CONFIG.app_name} version={CONFIG.version} START_REQUEST path={request.url.path}")
    start_time = time.time()
    
    response = await call_next(request)
    
    process_time = (time.time() - start_time) * 1000
    formatted_process_time = '{0:.2f}'.format(process_time)
    logger.info(f"method={str.upper(request.method)} rid={idem} app={CONFIG.app_name} version={CONFIG.version} END_REQUEST completed_in={formatted_process_time}ms status_code={response.status_code}")
    
    return response

class DestinationLanguage(str, Enum):
    en = 'en'
    de = 'de'
    it = 'it'
    ru = 'ru'
    es = 'es'
    pt = 'pt'
    ja = 'ja'
    hr = 'hr'

class Book(BaseModel):
    title: str
    author: str
    genre: str
    description: str
    price: int
    stock_quantity: int


@app.on_event("startup")
@repeat_every(seconds=5)
def reload_config():
    global CONFIG
    logger.info(f"app={CONFIG.app_name} version={CONFIG.version} | Reloading config")

    db_url = None
    app_name = None
    # Read from .env file
    try:
        db_url = dotenv_values('.env')['DB_URL']
        app_name = dotenv_values('.env')['APP_NAME']
    except Exception as e:
        pass
    # Read from ENV
    db_url = os.getenv('DB_URL', default=db_url)
    app_name = os.getenv('APP_NAME', default=app_name)

    if db_url != None and app_name != None:
        CONFIG.db_url = db_url
        CONFIG.app_name = app_name
    else:
        raise KeyError('No DB URL or APP NAME specified in ENV...')


graphql_app = GraphQLRouter(schema)
app.include_router(graphql_app, prefix='/graphql')

@app.get("/")
def read_root():
    return {"Hello": "World", "app_name": CONFIG.app_name}


@app.get("/books", tags=['books'])
def read_books():
    with Session(engine) as session:
        books = session.exec(select(Books)).all()
        return books


@app.post('/books', tags=['book'])
async def create_book(bookBody: Book, response: Response):
    try:
        title = bookBody.title
        author = bookBody.author
        genre = bookBody.genre
        description = bookBody.description
        price = bookBody.price
        stock_quantity = bookBody.stock_quantity
    
        book = Books(title=title, author=author, genre=genre, description=description, price=price, stock_quantity=stock_quantity)
        session = Session(engine)
        session.add(book)
        session.commit()
        session.close()

        response.status_code = status.HTTP_201_CREATED
        return {'book': book}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
@app.get("/books/{id}", tags=['book'])
def get_book(id: int, response: Response):
    with Session(engine) as session:
        book = session.exec(select(Books).where(Books.id == id))
        for b in book:
            response.status_code = status.HTTP_200_OK
            return b
    response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    return None

@app.delete("/books/{id}", tags=['book'])
def delete_book(id: int, response: Response):
    with Session(engine) as session:
        try:
            book = session.exec(select(Books).where(Books.id == id)).one()
        except Exception as e:
            response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            raise Exception(e)

        session.delete(book)
        session.commit()
        response.status_code = status.HTTP_200_OK
        return None

@app.put("/books/{id}", tags=['book'])
def update_book(id: int, newBook: Book, response: Response):
    with Session(engine) as session:
        try:
            book = session.exec(select(Books).where(Books.id == id)).one()
        except Exception as e:
            response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            raise Exception(e)

        book.author = newBook.author
        book.title = newBook.title
        book.description = newBook.description
        book.genre = newBook.genre
        book.stock_quantity = newBook.stock_quantity
        book.price = newBook.price

        session.add(book)
        session.commit()
        response.status_code = status.HTTP_200_OK
        return None
    
@app.put("/books/{id}/quantity", tags=['book'])
def change_book_stock_quantity(id: int, change: int, response: Response):
    with Session(engine) as session:
        try:
            book = session.exec(select(Books).where(Books.id == id)).one()
        except Exception as e:
            response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            raise Exception(e)

        book.stock_quantity = max(0, book.stock_quantity + change)

        session.add(book)
        session.commit()
        response.status_code = status.HTTP_200_OK
        return None

@app.get("/books/{id}/translate", tags=['translate'])
def translate_book(id: int, dest_lang: DestinationLanguage, response: Response):
    with Session(engine) as session:
        book = session.exec(select(Books).where(Books.id == id))
        for b in book:
            title = ts.translate_text(b.title, translator='google', from_language="sl", to_language=dest_lang.value)
            genre = ts.translate_text(b.genre, translator='google', from_language="sl", to_language=dest_lang.value)
            desc = ts.translate_text(b.description, translator='google', from_language="sl", to_language=dest_lang.value)
            response.status_code = status.HTTP_200_OK
            b.title = title
            b.genre = genre
            b.description = desc
            return b
    response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    return None

@app.get("/health/live", tags=['healthchecks'])
async def get_health_live(response: Response):
        healthy = True
        try:
            session = Session(engine)
            session.close()
            healthy = True
        except Exception as e:
            print(e)
            healthy = False

        if CONFIG.broken:
            healthy = False
        
        if healthy:
            response.status_code = status.HTTP_200_OK
            return {"State": "UP"}
        else:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return {"State": "DOWN"}

@app.get("/health/ready", tags=['healthchecks'])
async def get_health_ready(response: Response):
        healthy = True

        if CONFIG.broken:
            healthy = False
        
        if healthy:
            response.status_code = status.HTTP_200_OK
            return {"State": "UP"}
        else:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return {"State": "DOWN"}
        
@app.post("/broken", tags=['healthchecks'])
def set_broken():
    CONFIG.broken = True
    return Response(status_code=201)