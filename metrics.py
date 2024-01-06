from prometheus_client import Counter, make_asgi_app

books_get_request_counter = Counter('books_get_request', 'Counter for books GET request')
book_info_request_counter = Counter('book_info_request', 'Counter for book info request')

metrics_app = make_asgi_app()