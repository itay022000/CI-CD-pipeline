import pytest
import requests

BASE_URL = "http://localhost:5001"

books = [
    {
        "title": "Adventures of Huckleberry Finn",
        "author": "Mark Twain",
        "isbn": "9780142437179",
        "genre": "Fiction",
        "published": "1884"
    },
    {
        "title": "The Best of Isaac Asimov",
        "author": "Isaac Asimov",
        "isbn": "9780385121741",
        "genre": "Science Fiction",
        "published": "1974"
    },
    {
        "title": "1984",
        "author": "George Orwell",
        "isbn": "9780451524935",
        "genre": "Dystopian",
        "published": "1949"
    },
    {
        "title": "Non-Existent Book",
        "author": "Unknown",
        "isbn": "0000000000000",
        "genre": "Fiction",
        "published": "2024"
    },
    {
        "title": "Incorrect Genre Book",
        "author": "Author Unknown",
        "isbn": "1234567890123",
        "genre": "Unknown Genre",
        "published": "2024"
    }
]

book_ids = []

def test_post_books():
    for book in books[:3]:
        response = requests.post(f"{BASE_URL}/books", json=book)
        assert response.status_code == 201
        book_ids.append(response.json()["id"])
    assert len(set(book_ids)) == 3

def test_get_book1():
    response = requests.get(f"{BASE_URL}/books/{book_ids[0]}")
    assert response.status_code == 200
    assert response.json()["author"] == "Mark Twain"

def test_get_all_books():
    response = requests.get(f"{BASE_URL}/books")
    assert response.status_code == 200
    assert len(response.json()) == 3

def test_post_invalid_book():
    response = requests.post(f"{BASE_URL}/books", json=books[3])
    assert response.status_code in [400, 500]

def test_delete_book2():
    response = requests.delete(f"{BASE_URL}/books/{book_ids[1]}")
    assert response.status_code == 200

def test_get_deleted_book2():
    response = requests.get(f"{BASE_URL}/books/{book_ids[1]}")
    assert response.status_code == 404

def test_post_invalid_genre_book():
    response = requests.post(f"{BASE_URL}/books", json=books[4])
    assert response.status_code == 422
