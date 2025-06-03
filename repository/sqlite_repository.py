import sqlite3
import logging
from typing import List, Optional
from datetime import date

from library.book import Book
from library.user import User
from repository.interfaces import IBookRepository, IUserRepository, ILoanRepository

# Модульний логер
logger = logging.getLogger(__name__)


class SQLiteBookRepository(IBookRepository):
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def add(self, book: Book) -> None:
        try:
            self.conn.execute(
                "INSERT OR REPLACE INTO books "
                "(isbn, title, author, year, genre, available, issued_to, issue_date, times_issued) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    book.isbn,
                    book.title,
                    book.author,
                    book.year,
                    book.genre,
                    int(book.available),
                    book.issued_to,
                    book.issue_date.isoformat() if book.issue_date else None,
                    book.times_issued,
                ),
            )
            self.conn.commit()
            logger.debug(f"Added/Updated book: {book.isbn}")
        except sqlite3.Error as e:
            logger.error(f"Error adding book [{book.isbn}]: {e}")

    def get(self, isbn: str) -> Optional[Book]:
        try:
            row = self.conn.execute(
                "SELECT * FROM books WHERE isbn=?", (isbn,)
            ).fetchone()
            if not row:
                logger.debug(f"Book not found: {isbn}")
                return None
            book = Book(
                title=row["title"],
                author=row["author"],
                year=row["year"],
                genre=row["genre"],
                isbn=row["isbn"],
            )
            book.available = bool(row["available"])
            book.issued_to = row["issued_to"]
            book.issue_date = date.fromisoformat(row["issue_date"]) if row["issue_date"] else None
            book.times_issued = row["times_issued"]
            logger.debug(f"Fetched book: {isbn}")
            return book
        except sqlite3.Error as e:
            logger.error(f"Error fetching book [{isbn}]: {e}")
            return None

    def update(self, book: Book) -> None:
        # Оскільки add робить INSERT OR REPLACE, просто викликаємо add
        self.add(book)

    def delete(self, isbn: str) -> None:
        try:
            self.conn.execute("DELETE FROM books WHERE isbn=?", (isbn,))
            self.conn.commit()
            logger.debug(f"Deleted book: {isbn}")
        except sqlite3.Error as e:
            logger.error(f"Error deleting book [{isbn}]: {e}")

    def list_all(self) -> List[Book]:
        try:
            rows = self.conn.execute("SELECT * FROM books").fetchall()
            books: List[Book] = []
            for row in rows:
                book = Book(
                    title=row["title"],
                    author=row["author"],
                    year=row["year"],
                    genre=row["genre"],
                    isbn=row["isbn"],
                )
                book.available = bool(row["available"])
                book.issued_to = row["issued_to"]
                book.issue_date = date.fromisoformat(row["issue_date"]) if row["issue_date"] else None
                book.times_issued = row["times_issued"]
                books.append(book)
            logger.debug(f"Listed all books, count={len(books)}")
            return books
        except sqlite3.Error as e:
            logger.error(f"Error listing books: {e}")
            return []


class SQLiteUserRepository(IUserRepository):
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def add(self, user: User) -> None:
        try:
            self.conn.execute(
                "INSERT OR REPLACE INTO users (user_id, first_name, last_name, email) "
                "VALUES (?, ?, ?, ?)",
                (user.user_id, user.first_name, user.last_name, user.email),
            )
            self.conn.commit()
            logger.debug(f"Added/Updated user: {user.user_id}")
        except sqlite3.Error as e:
            logger.error(f"Error adding user [{user.user_id}]: {e}")

    def get(self, user_id: str) -> Optional[User]:
        try:
            row = self.conn.execute(
                "SELECT * FROM users WHERE user_id=?", (user_id,)
            ).fetchone()
            if not row:
                logger.debug(f"User not found: {user_id}")
                return None
            user = User(
                user_id=row["user_id"],
                first_name=row["first_name"],
                last_name=row["last_name"],
                email=row["email"],
            )
            logger.debug(f"Fetched user: {user_id}")
            return user
        except sqlite3.Error as e:
            logger.error(f"Error fetching user [{user_id}]: {e}")
            return None

    def list_all(self) -> List[User]:
        try:
            rows = self.conn.execute("SELECT * FROM users").fetchall()
            users = [
                User(
                    user_id=row["user_id"],
                    first_name=row["first_name"],
                    last_name=row["last_name"],
                    email=row["email"],
                )
                for row in rows
            ]
            logger.debug(f"Listed all users, count={len(users)}")
            return users
        except sqlite3.Error as e:
            logger.error(f"Error listing users: {e}")
            return []


class SQLiteLoanRepository(ILoanRepository):
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def issue(self, isbn: str, user_id: str, date: str) -> None:
        try:
            self.conn.execute(
                "INSERT INTO issued_books (user_id, isbn) VALUES (?, ?)",
                (user_id, isbn),
            )
            self.conn.execute(
                "UPDATE books SET available=0, issued_to=?, issue_date=? WHERE isbn=?",
                (user_id, date, isbn),
            )
            self.conn.commit()
            logger.debug(f"Issued book {isbn} to user {user_id}")
        except sqlite3.Error as e:
            logger.error(f"Error issuing book [{isbn}] to [{user_id}]: {e}")

    def return_book(self, isbn: str, user_id: str) -> None:
        try:
            self.conn.execute(
                "DELETE FROM issued_books WHERE user_id=? AND isbn=?",
                (user_id, isbn),
            )
            self.conn.execute(
                "UPDATE books SET available=1, issued_to=NULL, issue_date=NULL WHERE isbn=?",
                (isbn,),
            )
            self.conn.commit()
            logger.debug(f"Returned book {isbn} from user {user_id}")
        except sqlite3.Error as e:
            logger.error(f"Error returning book [{isbn}] from [{user_id}]: {e}")

    def list_issued(self) -> List[str]:
        try:
            rows = self.conn.execute("SELECT isbn FROM issued_books").fetchall()
            isbns = [row["isbn"] for row in rows]
            logger.debug(f"Listed issued books, count={len(isbns)}")
            return isbns
        except sqlite3.Error as e:
            logger.error(f"Error listing issued books: {e}")
            return []