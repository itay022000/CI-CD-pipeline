from flask import Flask, request, jsonify
from flask_restful import Api
from bson import ObjectId
import requests
from pymongo import MongoClient
import os
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
api = Api(app)

@app.route('/books', methods=['POST'])
def add_new_book():
    logger.debug("Received POST request to /books")
    if request.content_type != 'application/json':
        return jsonify({"error": "Unsupported media type"}), 415

    data = request.get_json()
    isbn = data.get('ISBN')
    title = data.get('title')
    genre = data.get('genre')

    try:
        book_id = library_manager.add_book(isbn, title, genre)
        return jsonify({"id": str(book_id)}), 201
    except DuplicateBookError as e:
        return jsonify({"error": str(e)}), 422
    except GenreNotValidError as e:
        return jsonify({"error": str(e)}), 422
    except RequiredFieldMissingError as e:
        return jsonify({"error": str(e)}), 422
    except ExternalAPIServiceError as e:
        return jsonify({"error": str(e)}), 500
    except APIBookNotFoundError as e:
        return jsonify({"error": str(e)}), 500

@app.route('/books/<book_id>', methods=['PUT'])
def modify_book(book_id):
    if request.content_type != 'application/json':
        return jsonify({"error": "Unsupported media type"}), 415

    update_info = request.get_json()

    try:
        book_id = library_manager.update_book(book_id, update_info)
        return jsonify({"id": str(book_id)}), 200
    except BookNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except GenreNotValidError as e:
        return jsonify({"error": str(e)}), 422
    except RequiredFieldMissingError as e:
        return jsonify({"error": str(e)}), 422

@app.route('/books', methods=['GET'])
def fetch_all_books():
    params = request.args
    books = library_manager.books.find()
    book_list = []
    for book in books:
        book["id"] = str(book["_id"])
        del book["_id"]
        book_list.append(book)

    if 'genre' in params:
        genre_filter = params['genre']
        filtered_books = [book for book in book_list if book['genre'] == genre_filter]
        return jsonify(filtered_books)
    
    return jsonify(book_list)

@app.route('/books/<book_id>', methods=['GET'])
def fetch_book(book_id):
    try:
        book = library_manager.get_book(book_id)
        return jsonify(book), 200
    except BookNotFoundError as e:
        return jsonify({"error": str(e)}), 404

@app.route('/books/<book_id>', methods=['DELETE'])
def remove_book(book_id):
    try:
        library_manager.delete_book(book_id)
        return jsonify({"id": str(book_id)}), 200
    except BookNotFoundError as e:
        return jsonify({"error": str(e)}), 404

@app.route('/ratings', methods=['GET'])
def fetch_ratings():
    all_ratings = list(library_manager.ratings.find())
    rating_list = [{
        'id': str(rating['book_id']),
        'title': rating['title'],
        'values': rating['values'],
        'average': rating['average']
    } for rating in all_ratings]
    return jsonify(rating_list)

@app.route('/ratings/<book_id>', methods=['GET'])
def fetch_rating(book_id):
    try:
        rating = library_manager.get_ratings(book_id)
        return jsonify(rating), 200
    except BookNotFoundError as e:
        return jsonify({"error": str(e)}), 404

@app.route('/ratings/<book_id>/values', methods=['POST'])
def submit_book_rating(book_id):
    if request.content_type != 'application/json':
        return jsonify({"error": "Unsupported media type"}), 415

    data = request.get_json()
    value = data.get('value')

    if value is None:
        return jsonify({"error": "Missing required fields."}), 422

    try:
        value = int(value)
        if value < 1 or value > 5:
            raise InvalidRating("The rating is not in the range of 1-5.")
        average = library_manager.add_rating(book_id, value)
        return jsonify({"new average": average}), 201
    except InvalidRating as e:
        return jsonify({"error": str(e)}), 422
    except BookNotFoundError as e:
        return jsonify({"error": str(e)}), 404

@app.route('/top', methods=['GET'])
def fetch_top_ratings():
    top_books = library_manager.get_top()
    top_ratings = [{'id': str(rating['book_id']),
                    'title': rating['title'],
                    'average': rating['average']} for rating in top_books]
    return jsonify(top_ratings), 200

class Book:
    def __init__(self, ISBN, title, genre):
        self.title = title
        self.authors = ""
        self.ISBN = ISBN
        self.genre = genre
        self.publisher = ""
        self.published_date = ""
        self.id = None
        self.fetch_from_api()

    def fetch_from_api(self):
        google_books_url = f'https://www.googleapis.com/books/v1/volumes?q=isbn:{self.ISBN}'
        try:
            response = requests.get(google_books_url)
            response.raise_for_status()
            book_data = response.json()['items'][0]['volumeInfo']
        except requests.exceptions.RequestException:
            raise ExternalAPIServiceError("Error occurred while calling the Google Books API.")
        except (KeyError, IndexError):
            raise APIBookNotFoundError(f"Book with ISBN {self.ISBN} not found in the Google Books API.")

        self.authors = " and ".join(book_data.get("authors", [])) if book_data.get("authors") else "missing"
        self.publisher = book_data.get("publisher", "missing")
        self.published_date = book_data.get("publishedDate", "missing")

    def json(self):
        return {
            'title': self.title,
            'authors': self.authors,
            'ISBN': self.ISBN,
            'genre': self.genre,
            'publisher': self.publisher,
            'published_date': self.published_date,
            'id': self.id
        }

class LibraryManager:
    VALID_GENRES = ["Biography", "Children", "Fantasy", "Fiction", "Other", "Science", "Science Fiction"]

    def __init__(self):
        mongo_uri = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
        logger.debug(f"Connecting to MongoDB with URI: {mongo_uri}")
        self.client = MongoClient(mongo_uri)
        logger.debug("MongoDB connection established")
        self.db = self.client['library_db']
        self.books = self.db['books']
        self.ratings = self.db['ratings']
        self.top_books = None

    def add_book(self, ISBN, title, genre):
        if not ISBN or not title or not genre:
            raise RequiredFieldMissingError("Missing required fields.")
        if self.books.find_one({"ISBN": ISBN}):
            raise DuplicateBookError("This book is already in the library.")
        if genre not in self.VALID_GENRES:
            raise GenreNotValidError("Invalid genre.")

        new_book = Book(ISBN, title, genre)
        book_id = self.books.insert_one(new_book.json()).inserted_id
        self.ratings.insert_one({'values': [], 'average': 0, 'title': title, 'book_id': book_id})

        return str(book_id)

    def update_book(self, book_id, update_data):
        try:
            object_id = ObjectId(book_id)
        except Exception:
            raise BookNotFoundError("Invalid ID format.")

        isbn = update_data.get("ISBN")
        title = update_data.get("title")
        genre = update_data.get("genre")
        authors = update_data.get("authors")
        publisher = update_data.get("publisher")
        published_date = update_data.get("publishedDate")

        if not isbn or not title or not genre or not authors or not publisher or not published_date:
            raise RequiredFieldMissingError("Missing required fields.")
        if genre not in self.VALID_GENRES:
            raise GenreNotValidError("Invalid genre.")

        update_fields = {
            "ISBN": isbn,
            "title": title,
            "genre": genre,
            "authors": authors,
            "publisher": publisher,
            "publishedDate": published_date
        }

        update_result = self.books.update_one({"_id": object_id}, {"$set": update_fields})

        if update_result.matched_count == 0:
            raise BookNotFoundError(f"Book with ID: {book_id} not found in the library.")

        return book_id

    def get_book(self, book_id):
        try:
            object_id = ObjectId(book_id)
        except Exception:
            raise BookNotFoundError("Invalid ID format.")
        
        book = self.books.find_one({"_id": object_id})
        
        if not book:
            raise BookNotFoundError(f"Book with ID: {book_id} not found.")
        
        book["id"] = str(book["_id"])
        del book["_id"]
        
        return book

    def delete_book(self, book_id):
        try:
            object_id = ObjectId(book_id)
        except Exception:
            raise BookNotFoundError("Invalid ID format.")
        
        delete_result = self.books.delete_one({"_id": object_id})
        
        if delete_result.deleted_count == 0:
            raise BookNotFoundError(f"Book with ID: {book_id} not found.")
        
        self.ratings.delete_one({"book_id": object_id})
        
        return True

    def add_rating(self, book_id, rating):
        if not book_id or not rating:
            raise RequiredFieldMissingError("Missing required fields.")
        if rating < 1 or rating > 5:
            raise InvalidRating("The rating is not in the range of 1-5.")

        try:
            object_id = ObjectId(book_id)
        except Exception:
            raise BookNotFoundError("Invalid ID format.")

        book_rating = self.ratings.find_one({"book_id": object_id})

        if not book_rating:
            raise BookNotFoundError(f"Book with ID: {book_id} not found in the library.")
        
        values = book_rating['values']
        values.append(rating)
        new_average = round(sum(values) / len(values), 2)
        self.ratings.update_one({"book_id": object_id}, {"$set": {"values": values, "average": new_average}})

        return new_average

    def get_ratings(self, book_id):
        try:
            object_id = ObjectId(book_id)
        except Exception:
            raise BookNotFoundError("Invalid ID format.")

        book_ratings = self.ratings.find_one({"book_id": object_id})

        if not book_ratings:
            raise BookNotFoundError(f"Book with ID: {book_id} not found.")
        
        return {
            "title": str(book_ratings["title"]),
            "values": book_ratings["values"],
            "average": book_ratings["average"],
            "id": str(book_ratings["book_id"])
        }

    def update_top(self):
        ratings = list(self.ratings.find())
        ratings.sort(key=lambda x: x['average'], reverse=True)
        self.top_books = ratings[:3]

    def get_top(self):
        self.update_top()
        return self.top_books

class Error(Exception):
    pass

class ExternalAPIServiceError(Error):
    """Issue with an external API"""
    pass

class APIBookNotFoundError(Error):
    """ISBN is not found in the Google Books API"""
    pass

class BookNotFoundError(Error):
    """ID is not found in the library"""
    pass

class DuplicateBookError(Error):
    """Book already exists"""
    pass

class GenreNotValidError(Error):
    pass

class RequiredFieldMissingError(Error):
    """Missing field"""
    pass

class InvalidRating(Error):
    """Rating not 1-5"""
    pass

port = int(os.getenv('PORT', 5001))

if __name__ == '__main__':
    print("Starting the book management application...")
    library_manager = LibraryManager()
    app.run(host='0.0.0.0', port=port, debug=True)
