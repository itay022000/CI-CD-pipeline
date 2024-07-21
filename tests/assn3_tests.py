import time
import pytest
import requests
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:5001"

def retry_request(func, max_retries=3):
    for i in range(max_retries):
        try:
            return func()
        except requests.RequestException as e:
            logger.error(f"Request failed (attempt {i+1}/{max_retries}): {str(e)}")
            if i == max_retries - 1:
                raise
            time.sleep(2 ** i)

@pytest.fixture(scope="module")
def setup_teardown():
    logger.info("Setting up test environment")
    yield
    logger.info("Tearing down test environment")
    requests.delete(f"{BASE_URL}/books")

@pytest.fixture
def sample_books():
    return [
        {"title": "Adventures of Huckleberry Finn", "ISBN": "9780520343641", "genre": "Fiction"},
        {"title": "The Best of Isaac Asimov", "ISBN": "9780385050784", "genre": "Science Fiction"},
        {"title": "Fear No Evil", "ISBN": "9780394558783", "genre": "Biography"},
        {"title": "No such book", "ISBN": "0000001111111", "genre": "Biography"},
        {"title": "The Greatest Joke Book Ever", "authors": "Mel Greene", "ISBN": "9780380798490", "genre": "Jokes"},
        {"title": "The Adventures of Tom Sawyer", "ISBN": "9780195810400", "genre": "Fiction"},
        {"title": "I, Robot", "ISBN": "9780553294385", "genre": "Science Fiction"},
        {"title": "Second Foundation", "ISBN": "9780553293364", "genre": "Science Fiction"}
    ]

def cleanup_books():
    response = retry_request(lambda: requests.get(f"{BASE_URL}/books"))
    for book in response.json():
        retry_request(lambda: requests.delete(f"{BASE_URL}/books/{book['id']}"))

def test_post_books(setup_teardown, sample_books):
    logger.info("Starting test_post_books")
    cleanup_books()
    book_ids = []
    for book in sample_books[:3]:
        logger.debug(f"Posting book: {book['title']}")
        response = retry_request(lambda: requests.post(f"{BASE_URL}/books", json=book))
        logger.info(f"POST /books response: {response.status_code}, {response.text}")
        assert response.status_code in [201, 422], f"Unexpected status code: {response.status_code}"
        if response.status_code == 201:
            book_ids.append(response.json().get("id"))
    assert len(set(book_ids)) == 3, f"Expected 3 unique book IDs, got {len(set(book_ids))}"

def test_get_book(setup_teardown, sample_books):
    logger.info("Starting test_get_book")
    cleanup_books()
    response = retry_request(lambda: requests.post(f"{BASE_URL}/books", json=sample_books[0]))
    logger.info(f"POST /books response: {response.status_code}, {response.text}")
    assert response.status_code == 201, f"Failed to post book: {response.text}"
    book_id = response.json().get("id")
    
    response = retry_request(lambda: requests.get(f"{BASE_URL}/books/{book_id}"))
    logger.info(f"GET /books/{book_id} response: {response.status_code}, {response.text}")
    assert response.status_code == 200, f"Failed to get book: {response.text}"
    book_data = response.json()
    assert book_data.get("title") == sample_books[0]['title'], f"Expected title '{sample_books[0]['title']}', but got '{book_data.get('title')}'"

def test_get_all_books(setup_teardown, sample_books):
    logger.info("Starting test_get_all_books")
    cleanup_books()
    for book in sample_books[:3]:
        logger.debug(f"Posting book: {book['title']}")
        retry_request(lambda: requests.post(f"{BASE_URL}/books", json=book))
    logger.debug("Getting all books")
    response = retry_request(lambda: requests.get(f"{BASE_URL}/books"))
    logger.info(f"GET /books response: {response.status_code}, {response.text}")
    assert response.status_code == 200
    books = response.json()
    assert len(books) >= 3, f"Expected at least 3 books, but got {len(books)}"

def test_post_invalid_book(setup_teardown):
    logger.info("Starting test_post_invalid_book")
    invalid_book = {"title": "Invalid Book", "author": "Unknown", "ISBN": "0000000000000", "genre": "Fiction"}
    logger.debug(f"Posting invalid book: {invalid_book}")
    response = retry_request(lambda: requests.post(f"{BASE_URL}/books", json=invalid_book))
    logger.info(f"POST /books (invalid) response: {response.status_code}, {response.text}")
    assert response.status_code in [400, 500]

def test_delete_book(setup_teardown, sample_books):
    logger.info("Starting test_delete_book")
    cleanup_books()
    response = retry_request(lambda: requests.post(f"{BASE_URL}/books", json=sample_books[1]))
    logger.info(f"POST /books response: {response.status_code}, {response.text}")
    assert response.status_code == 201, f"Failed to post book: {response.text}"
    book_id = response.json().get("id")
    
    response = retry_request(lambda: requests.delete(f"{BASE_URL}/books/{book_id}"))
    logger.info(f"DELETE /books/{book_id} response: {response.status_code}, {response.text}")
    assert response.status_code == 200, f"Failed to delete book: {response.text}"

def test_get_deleted_book(setup_teardown, sample_books):
    logger.info("Starting test_get_deleted_book")
    cleanup_books()
    response = retry_request(lambda: requests.post(f"{BASE_URL}/books", json=sample_books[1]))
    logger.info(f"POST /books response: {response.status_code}, {response.text}")
    assert response.status_code == 201, f"Failed to post book: {response.text}"
    book_id = response.json().get("id")
    
    retry_request(lambda: requests.delete(f"{BASE_URL}/books/{book_id}"))
    
    response = retry_request(lambda: requests.get(f"{BASE_URL}/books/{book_id}"))
    logger.info(f"GET /books/{book_id} response: {response.status_code}, {response.text}")
    assert response.status_code == 404, f"Expected status code 404, but got {response.status_code}"

def test_post_invalid_genre(setup_teardown):
    logger.info("Starting test_post_invalid_genre")
    invalid_genre_book = {"title": "Invalid Genre Book", "author": "Author Unknown", "ISBN": "1234567890123", "genre": "Unknown Genre"}
    logger.debug(f"Posting book with invalid genre: {invalid_genre_book}")
    response = retry_request(lambda: requests.post(f"{BASE_URL}/books", json=invalid_genre_book))
    logger.info(f"POST /books (invalid genre) response: {response.status_code}, {response.text}")
    assert response.status_code == 200, f"Expected status code 200, but got {response.status_code}"

if __name__ == "__main__":
    pytest.main(["-v", __file__])
