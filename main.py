import os
from typing import Optional
from fastapi import FastAPI, Request, HTTPException, Response, status
from fastapi_utils.tasks import repeat_every
from sqlmodel import Field, Session, SQLModel, create_engine, select
import os
from pydantic import BaseModel
from dotenv import dotenv_values
from prometheus_client import Counter, make_asgi_app
import logging
import time
import uuid

class Config:
    db_url: str = None
    app_name: str = "bookstore_catalog"
    version: str = "v1"
    # Read from .env file
    try:
        db_url = dotenv_values('.env')['DB_URL']
        app_name = dotenv_values('.env')['APP_NAME']
    except Exception as e:
        print('No .env file with DB_URL and APP_NAME found...')
    # Read from ENV
    db_url = os.getenv('DB_URL', default=db_url)
    app_name = os.getenv('APP_NAME', default=app_name)

    broken: bool = False

books_get_request_counter = Counter('books_get_request', 'Counter for books GET request')

CONFIG = Config()
app = FastAPI()
# logging.basicConfig('logging.conf')
logger = logging.getLogger('uvicorn')
# Add prometheus asgi middleware to route /metrics requests
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    idem = uuid.uuid4()
    logger.info(f"method={str.upper(request.method)} rid={idem} app={CONFIG.app_name} version={CONFIG.version} START_REQUEST path={request.url.path}")
    start_time = time.time()
    
    response = await call_next(request)
    
    process_time = (time.time() - start_time) * 1000
    formatted_process_time = '{0:.2f}'.format(process_time)
    logger.info(f"method={str.upper(request.method)} rid={idem} app={CONFIG.app_name} version={CONFIG.version} END_REQUEST completed_in={formatted_process_time}ms status_code={response.status_code}")
    
    return response

class Book(BaseModel):
    title: str
    author: str
    genre: str
    price: int
    stock_quantity: int


class Books(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    author: str
    genre: str
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


if CONFIG.db_url == None:
    raise KeyError('No DB URL specified in ENV...')

engine = create_engine(CONFIG.db_url, echo=True)

@app.get("/")
def read_root():
    return {"Hello": "World", "app_name": CONFIG.app_name}


@app.get("/books")
def read_books():
    with Session(engine) as session:
        books = session.exec(select(Books)).all()
        books_get_request_counter.inc()
        for book in books:
            print(book)
        return books


@app.post('/books')
async def create_book(bookBody: Book):
    try:
        title = bookBody.title
        author = bookBody.author
        genre = bookBody.genre
        price = bookBody.price
        stock_quantity = bookBody.stock_quantity
    
        book = Books(title=title, author=author, genre=genre, price=price, stock_quantity=stock_quantity)
        session = Session(engine)
        session.add(book)
        session.commit()
        session.close()

        return Response(status_code=201, content='Book added.')

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
@app.get("/books/{id}")
def get_book(id: int, response: Response):
    with Session(engine) as session:
        book = session.exec(select(Books).where(Books.id == id))
        for b in book:
            print(b)
            response.status_code = status.HTTP_200_OK
            return b
    response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    return None

@app.get("/health/live")
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

@app.get("/health/ready")
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
        
@app.post("/broken")
def set_broken():
    CONFIG.broken = True
    return Response(status_code=201)