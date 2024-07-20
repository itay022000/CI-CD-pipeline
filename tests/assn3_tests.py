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
        {"title": "Adventures of Huckleberry Finn", "author": "Mark Twain", "ISBN": "9780142437179", "genre": "Fiction"},
        {"title": "The Best of Isaac Asimov", "author": "Isaac Asimov", "ISBN": "9780385121741", "genre": "Science Fiction"},
        {"title": "1984", "author": "George Orwell", "ISBN": "9780451524935", "genre": "Fiction"}
    ]

def test_post_books(setup_teardown, sample_books):
    logger.info("Starting test_post_books")
    book_ids = []
    for book in sample_books:
        logger.debug(f"Posting book: {book['title']}")
        response = retry_request(lambda: requests.post(f"{BASE_URL}/books", json=book))
        assert response.status_code == 201, f"Failed to post book: {response.text}"
        book_id = response.json().get("id")
        assert book_id is not None, "Book ID is None"
        book_ids.append(book_id)
    assert len(set(book_ids)) == 3, f"Expected 3 unique book IDs, got {len(set(book_ids))}"
    logger.info("test_post_books completed successfully")

def test_get_book(setup_teardown, sample_books):
    logger.info("Starting test_get_book")
    response = retry_request(lambda: requests.post(f"{BASE_URL}/books", json=sample_books[0]))
    book_id = response.json().get("id")
    logger.debug(f"Getting book with ID: {book_id}")
    response = retry_request(lambda: requests.get(f"{BASE_URL}/books/{book_id}"))
    assert response.status_code == 200
    book_data = response.json()
    assert "Mark Twain" in book_data.get("authors", "")
    logger.info("test_get_book completed successfully")

def test_get_all_books(setup_teardown, sample_books):
    logger.info("Starting test_get_all_books")
    for book in sample_books:
        logger.debug(f"Posting book: {book['title']}")
        retry_request(lambda: requests.post(f"{BASE_URL}/books", json=book))
    logger.debug("Getting all books")
    response = retry_request(lambda: requests.get(f"{BASE_URL}/books"))
    assert response.status_code == 200
    books = response.json()
    assert len(books) == 3
    logger.info("test_get_all_books completed successfully")

def test_post_invalid_book(setup_teardown):
    logger.info("Starting test_post_invalid_book")
    invalid_book = {"title": "Invalid Book", "author": "Unknown", "ISBN": "0000000000000", "genre": "Fiction"}
    logger.debug(f"Posting invalid book: {invalid_book}")
    response = retry_request(lambda: requests.post(f"{BASE_URL}/books", json=invalid_book))
    assert response.status_code in [422, 500]
    logger.info("test_post_invalid_book completed successfully")

def test_post_invalid_genre(setup_teardown):
    logger.info("Starting test_post_invalid_genre")
    invalid_genre_book = {"title": "Invalid Genre Book", "author": "Author Unknown", "ISBN": "1234567890123", "genre": "Unknown Genre"}
    logger.debug(f"Posting book with invalid genre: {invalid_genre_book}")
    response = retry_request(lambda: requests.post(f"{BASE_URL}/books", json=invalid_genre_book))
    assert response.status_code == 422
    logger.info("test_post_invalid_genre completed successfully")

if __name__ == "__main__":
    pytest.main(["-v", __file__])
