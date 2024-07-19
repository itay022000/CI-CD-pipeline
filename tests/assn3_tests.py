import pytest
import requests
import json

BASE_URL = "http://localhost:5001"

def test_post_books():
    book1 = {"title": "Adventures of Huckleberry Finn", "author": "Mark Twain", "isbn": "9780486280615"}
    book2 = {"title": "The Best of Isaac Asimov", "author": "Isaac Asimov", "isbn": "9780449208069"}
    book3 = {"title": "The Hobbit", "author": "J.R.R. Tolkien", "isbn": "9780547928227"}
    
    ids = []
    for book in [book1, book2, book3]:
        response = requests.post(f"{BASE_URL}/books", json=book)
        assert response.status_code == 201
        book_id = response.json().get("ID")
        assert book_id is not None
        ids.append(book_id)
    
    assert len(set(ids)) == 3  # Ensure all IDs are unique

def test_get_book1():
    book1 = {"title": "Adventures of Huckleberry Finn", "author": "Mark Twain", "isbn": "9780486280615"}
    response = requests.post(f"{BASE_URL}/books", json=book1)
    book_id = response.json().get("ID")
    
    response = requests.get(f"{BASE_URL}/books/{book_id}")
    assert response.status_code == 200
    book_data = response.json()
    assert "Mark Twain" in book_data.get("authors", [])

def test_get_all_books():
    response = requests.get(f"{BASE_URL}/books")
    assert response.status_code == 200
    books = response.json()
    assert len(books) == 3

def test_post_invalid_book():
    invalid_book = {"title": "Invalid Book", "author": "No One", "isbn": "1234567890"}
    response = requests.post(f"{BASE_URL}/books", json=invalid_book)
    assert response.status_code in [400, 500]

def test_delete_book():
    book2 = {"title": "The Best of Isaac Asimov", "author": "Isaac Asimov", "isbn": "9780449208069"}
    response = requests.post(f"{BASE_URL}/books", json=book2)
    book_id = response.json().get("ID")
    
    response = requests.delete(f"{BASE_URL}/books/{book_id}")
    assert response.status_code == 200

def test_get_deleted_book():
    book2 = {"title": "The Best of Isaac Asimov", "author": "Isaac Asimov", "isbn": "9780449208069"}
    response = requests.post(f"{BASE_URL}/books", json=book2)
    book_id = response.json().get("ID")
    
    requests.delete(f"{BASE_URL}/books/{book_id}")
    
    response = requests.get(f"{BASE_URL}/books/{book_id}")
    assert response.status_code == 404

def test_post_invalid_genre():
    invalid_genre_book = {"title": "Invalid Genre Book", "author": "Some Author", "isbn": "9781234567890", "genre": "InvalidGenre"}
    response = requests.post(f"{BASE_URL}/books", json=invalid_genre_book)
    assert response.status_code == 422

if __name__ == "__main__":
    pytest.main(["-v", __file__])
