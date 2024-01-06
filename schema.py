from typing import List
import strawberry
from database import get_all_books, get_one_book

@strawberry.type
class Book:
    id: int
    title: str
    author: str
    description: str
    genre: str
    price: int
    stock_quantity: int

@strawberry.type
class Query:
    books: List[Book] = strawberry.field(resolver=get_all_books)

    @strawberry.field
    def book(self, id: strawberry.ID) -> Book:
        return get_one_book(id)

schema = strawberry.Schema(Query)