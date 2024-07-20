import pytest
import requests
import os

BASE_URL = os.getenv('BASE_URL', 'http://localhost:5001')

@pytest.fixture(scope="module")
def setup_teardown():
    # Setup
    yield
    # Teardown
    requests.delete(f"{BASE_URL}/books")

@pytest.fixture
def sample_books():
    return [
        {"title": "Adventures of Huckleberry Finn", "author": "Mark Twain", "ISBN": "9780142437179", "genre": "Fiction"},
        {"title": "The Best of Isaac Asimov", "author": "Isaac Asimov", "ISBN": "9780385121741", "genre": "Science Fiction"},
        {"title": "1984", "author": "George Orwell", "ISBN": "9780451524935", "genre": "Fiction"}
    ]

def test_post_books(setup_teardown, sample_books):
    book_ids = []
    for book in sample_books:
        response = requests.post(f"{BASE_URL}/books", json=book)
        assert response.status_code == 201
        book_id = response.json().get("id")
        assert book_id is not None
        book_ids.append(book_id)
    assert len(set(book_ids)) == 3

def test_get_book(setup_teardown, sample_books):
    response = requests.post(f"{BASE_URL}/books", json=sample_books[0])
    book_id = response.json().get("id")
    response = requests.get(f"{BASE_URL}/books/{book_id}")
    assert response.status_code == 200
    book_data = response.json()
    assert "Mark Twain" in book_data.get("authors", "")

def test_get_all_books(setup_teardown, sample_books):
    for book in sample_books:
        requests.post(f"{BASE_URL}/books", json=book)
    response = requests.get(f"{BASE_URL}/books")
    assert response.status_code == 200
    books = response.json()
    assert len(books) == 3

def test_post_invalid_book(setup_teardown):
    invalid_book = {"title": "Invalid Book", "author": "Unknown", "ISBN": "0000000000000", "genre": "Fiction"}
    response = requests.post(f"{BASE_URL}/books", json=invalid_book)
    assert response.status_code in [422, 500]

def test_delete_book(setup_teardown, sample_books):
    response = requests.post(f"{BASE_URL}/books", json=sample_books[1])
    book_id = response.json().get("id")
    response = requests.delete(f"{BASE_URL}/books/{book_id}")
    assert response.status_code == 200
    response = requests.get(f"{BASE_URL}/books/{book_id}")
    assert response.status_code == 404

def test_post_invalid_genre(setup_teardown):
    invalid_genre_book = {"title": "Invalid Genre Book", "author": "Author Unknown", "ISBN": "1234567890123", "genre": "Unknown Genre"}
    response = requests.post(f"{BASE_URL}/books", json=invalid_genre_book)
    assert response.status_code == 422

def test_update_book(setup_teardown, sample_books):
    response = requests.post(f"{BASE_URL}/books", json=sample_books[0])
    book_id = response.json().get("id")
    update_data = {"title": "Updated Title", "genre": "Science Fiction"}
    response = requests.put(f"{BASE_URL}/books/{book_id}", json=update_data)
    assert response.status_code == 200
    response = requests.get(f"{BASE_URL}/books/{book_id}")
    updated_book = response.json()
    assert updated_book["title"] == "Updated Title"
    assert updated_book["genre"] == "Science Fiction"

def test_filter_books_by_genre(setup_teardown, sample_books):
    for book in sample_books:
        requests.post(f"{BASE_URL}/books", json=book)
    response = requests.get(f"{BASE_URL}/books?genre=Fiction")
    assert response.status_code == 200
    books = response.json()
    assert all(book["genre"] == "Fiction" for book in books)

def test_add_rating(setup_teardown, sample_books):
    response = requests.post(f"{BASE_URL}/books", json=sample_books[0])
    book_id = response.json().get("id")
    rating_data = {"value": 4}
    response = requests.post(f"{BASE_URL}/ratings/{book_id}/values", json=rating_data)
    assert response.status_code == 201
    response = requests.get(f"{BASE_URL}/ratings/{book_id}")
    assert response.status_code == 200
    rating_info = response.json()
    assert rating_info["average"] == 4.0

def test_get_top_ratings(setup_teardown, sample_books):
    for book in sample_books:
        response = requests.post(f"{BASE_URL}/books", json=book)
        book_id = response.json().get("id")
        rating_data = {"value": 4}
        requests.post(f"{BASE_URL}/ratings/{book_id}/values", json=rating_data)
    response = requests.get(f"{BASE_URL}/top")
    assert response.status_code == 200
    top_books = response.json()
    assert len(top_books) <= 3
    assert all(book["average"] == 4.0 for book in top_books)

if __name__ == "__main__":
    pytest.main(["-v", __file__])
