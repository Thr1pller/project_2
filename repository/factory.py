import sqlite3
from database import initialize_database
from repository.sqlite_repository import (
    SQLiteBookRepository, SQLiteUserRepository, SQLiteLoanRepository
)

class RepoBundle:
    """
    Бандл репозиторіїв для одного бекенду
    """
    def __init__(self, book_repo, user_repo, loan_repo):
        self.book_repo = book_repo
        self.user_repo = user_repo
        self.loan_repo = loan_repo

class RepositoryFactory:
    @staticmethod
    def create_sqlite(db_path: str) -> RepoBundle:
        """
        Створює бандл репозиторіїв на основі SQLite
        """
        initialize_database(db_path)
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return RepoBundle(
            book_repo=SQLiteBookRepository(conn),
            user_repo=SQLiteUserRepository(conn),
            loan_repo=SQLiteLoanRepository(conn),
        )

    @staticmethod
    def create_in_memory() -> RepoBundle:
        """
        Створює бандл репозиторіїв in-memory (для тестування)
        """
        path = ':memory:'
        initialize_database(path)
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        return RepoBundle(
            book_repo=SQLiteBookRepository(conn),
            user_repo=SQLiteUserRepository(conn),
            loan_repo=SQLiteLoanRepository(conn),
        )
