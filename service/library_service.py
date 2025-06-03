from typing import List, Protocol
from library.book import Book
from library.user import User
import datetime

class Observer(Protocol):
    def update(self, event: str, data: dict): ...

class LibraryService:
    def __init__(self, books, users, loans):
        self.books = books
        self.users = users
        self.loans = loans
        self._observers: List[Observer] = []

    def register_observer(self, observer: Observer):
        """Реєстрація спостерігача для подій"""
        self._observers.append(observer)

    def notify_observers(self, event: str, data: dict):
        """Оповіщення зареєстрованих спостерігачів"""
        for obs in self._observers:
            obs.update(event, data)

    def add_book(self, book: Book):
        self.books.add(book)
        self.notify_observers('book_added', {'isbn': book.isbn})

    def remove_book(self, isbn: str):
        self.books.delete(isbn)
        self.notify_observers('book_removed', {'isbn': isbn})

    def register_user(self, user: User):
        self.users.add(user)
        self.notify_observers('user_registered', {'user_id': user.user_id})

    def issue_book(self, isbn: str, user_id: str) -> bool:
        book = self.books.get(isbn)
        user = self.users.get(user_id)
        if book and user and book.available:
            today = datetime.date.today().isoformat()
            self.loans.issue(isbn, user_id, today)
            self.notify_observers('book_issued', {'isbn': isbn, 'user_id': user_id})
            return True
        return False

    def return_book(self, isbn: str, user_id: str) -> bool:
        self.loans.return_book(isbn, user_id)
        self.notify_observers('book_returned', {'isbn': isbn, 'user_id': user_id})
        return True

    def search_books(self, **criteria) -> List[Book]:
        all_books = self.books.list_all()
        def match(b: Book):
            for k, v in criteria.items():
                attr = getattr(b, k)
                if isinstance(attr, str) and isinstance(v, str):
                    if v.lower() not in attr.lower():
                        return False
                elif attr != v:
                    return False
            return True
        return [b for b in all_books if match(b)]

    def list_overdue(self, max_days: int = 30) -> List[str]:
        overdue = []
        today = datetime.date.today()
        for isbn in self.loans.list_issued():
            book = self.books.get(isbn)
            if book and book.issue_date and (today - book.issue_date).days > max_days:
                overdue.append(isbn)
        return overdue
