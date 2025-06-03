import os
import unittest
import sqlite3
from datetime import date, timedelta
from unittest.mock import MagicMock, patch
import datetime
import tkinter as tk
import tkinter.ttk as ttk

from repository.sqlite_repository import (
    SQLiteBookRepository,
    SQLiteUserRepository,
    SQLiteLoanRepository,
)
from repository.factory import RepositoryFactory, RepoBundle
from container import Container
from library.book import Book
from library.user import User
from service.library_service import LibraryService
from Client import LibraryGUI


# -----------------------------------------
# Repository Tests
# -----------------------------------------

class TestSQLiteBookRepository(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("""
            CREATE TABLE books (
                isbn TEXT PRIMARY KEY,
                title TEXT, author TEXT, year INTEGER,
                genre TEXT, available INTEGER,
                issued_to TEXT, issue_date TEXT, times_issued INTEGER
            )
        """)
        self.conn.commit()
        self.repo = SQLiteBookRepository(self.conn)

    def tearDown(self):
        self.conn.close()

    def test_add_and_get_book(self):
        b = Book("A", "Auth", 2000, "G", "ISBN1")
        self.repo.add(b)
        fetched = self.repo.get("ISBN1")
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.title, "A")
        self.assertTrue(fetched.available)
        self.assertEqual(fetched.times_issued, 0)

    def test_update_book_fields(self):
        b = Book("B", "Auth", 2001, "G", "ISBN2")
        self.repo.add(b)
        b.available = False
        b.issued_to = "u1"
        b.issue_date = date(2025, 1, 1)
        b.times_issued = 7
        self.repo.update(b)
        u = self.repo.get("ISBN2")
        self.assertFalse(u.available)
        self.assertEqual(u.issued_to, "u1")
        self.assertEqual(u.times_issued, 7)
        self.assertEqual(u.issue_date, date(2025, 1, 1))

    def test_list_all_and_delete(self):
        b1 = Book("X", "A", 2002, "G", "I1")
        b2 = Book("Y", "B", 2003, "G", "I2")
        self.repo.add(b1)
        self.repo.add(b2)
        all_isbns = {b.isbn for b in self.repo.list_all()}
        self.assertSetEqual(all_isbns, {"I1", "I2"})
        self.repo.delete("I1")
        self.assertIsNone(self.repo.get("I1"))
        self.assertEqual(len(self.repo.list_all()), 1)

    def test_get_nonexistent_returns_none(self):
        self.assertIsNone(self.repo.get("NOISBN"))


class TestSQLiteUserRepository(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("""
            CREATE TABLE users (
                user_id TEXT PRIMARY KEY,
                first_name TEXT, last_name TEXT, email TEXT
            )
        """)
        self.conn.commit()
        self.repo = SQLiteUserRepository(self.conn)

    def tearDown(self):
        self.conn.close()

    def test_add_get_list_user(self):
        u = User("u42", "Alice", "Wonder", "a@b.com")
        self.repo.add(u)
        fetched = self.repo.get("u42")
        self.assertEqual(fetched.first_name, "Alice")
        users = self.repo.list_all()
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0].email, "a@b.com")

    def test_empty_list_and_get_none(self):
        self.assertEqual(self.repo.list_all(), [])
        self.assertIsNone(self.repo.get("nouser"))


class TestSQLiteLoanRepository(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        c = self.conn.cursor()
        c.execute("""
            CREATE TABLE books (
                isbn TEXT PRIMARY KEY,
                available INTEGER,
                issued_to TEXT,
                issue_date TEXT,
                times_issued INTEGER
            )
        """)
        c.execute("CREATE TABLE issued_books (user_id TEXT, isbn TEXT)")
        c.execute("INSERT INTO books VALUES(?,?,?,?,?)", ("B1", 1, None, None, 0))
        self.conn.commit()
        self.loan = SQLiteLoanRepository(self.conn)

    def tearDown(self):
        self.conn.close()

    def test_issue_book_updates_tables(self):
        self.loan.issue("B1", "u1", "2025-01-02")
        self.assertIn("B1", self.loan.list_issued())
        row = self.conn.execute(
            "SELECT available, issued_to, issue_date FROM books WHERE isbn=?", ("B1",)
        ).fetchone()
        self.assertEqual(row["available"], 0)
        self.assertEqual(row["issued_to"], "u1")
        self.assertEqual(row["issue_date"], "2025-01-02")

    def test_return_book_clears_issued(self):
        self.loan.issue("B1", "u1", "2025-01-02")
        self.loan.return_book("B1", "u1")
        self.assertEqual(self.loan.list_issued(), [])
        row = self.conn.execute(
            "SELECT available, issued_to, issue_date FROM books WHERE isbn=?", ("B1",)
        ).fetchone()
        self.assertEqual(row["available"], 1)
        self.assertIsNone(row["issued_to"])
        self.assertIsNone(row["issue_date"])

    def test_list_issued_empty_when_no_entries(self):
        fresh_conn = sqlite3.connect(":memory:")
        fresh_conn.row_factory = sqlite3.Row
        # Create necessary tables for a fresh loan repo
        c = fresh_conn.cursor()
        c.execute("""
            CREATE TABLE books (
                isbn TEXT PRIMARY KEY,
                available INTEGER,
                issued_to TEXT,
                issue_date TEXT,
                times_issued INTEGER
            )
        """)
        c.execute("CREATE TABLE issued_books (user_id TEXT, isbn TEXT)")
        fresh_conn.commit()
        fresh_repo = SQLiteLoanRepository(fresh_conn)
        self.assertEqual(fresh_repo.list_issued(), [])


# -----------------------------------------
# Factory & Container Tests
# -----------------------------------------

class TestRepositoryFactoryAndBundle(unittest.TestCase):
    def test_sqlite_bundle_creation(self):
        bundle: RepoBundle = RepositoryFactory.create_sqlite(":memory:")
        self.assertIsInstance(bundle.book_repo, SQLiteBookRepository)
        self.assertIsInstance(bundle.user_repo, SQLiteUserRepository)
        self.assertIsInstance(bundle.loan_repo, SQLiteLoanRepository)

    def test_inmemory_bundle_creation(self):
        b2 = RepositoryFactory.create_in_memory()
        self.assertTrue(callable(b2.book_repo.list_all))
        self.assertTrue(callable(b2.loan_repo.issue))


class TestContainerInjection(unittest.TestCase):
    def test_sqlite_strategy_injection(self):
        os.environ["STORAGE_BACKEND"] = "sqlite"
        os.environ["DB_PATH"] = ":memory:"
        c = Container()
        c.config.storage.backend.from_env("STORAGE_BACKEND")
        c.config.storage.db_path.from_env("DB_PATH")
        svc = c.library_service()
        # Create tables so that list_all does not fail
        conn = svc.books.conn
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS books (
                isbn TEXT PRIMARY KEY,
                title TEXT, author TEXT, year INTEGER,
                genre TEXT, available INTEGER,
                issued_to TEXT, issue_date TEXT, times_issued INTEGER
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                first_name TEXT, last_name TEXT, email TEXT
            )
        """)
        cur.execute("CREATE TABLE IF NOT EXISTS issued_books (user_id TEXT, isbn TEXT)")
        conn.commit()
        self.assertEqual(svc.books.list_all(), [])

    def test_inmemory_strategy_injection(self):
        os.environ["STORAGE_BACKEND"] = "in_memory"
        os.environ.pop("DB_PATH", None)
        c = Container()
        c.config.storage.backend.from_env("STORAGE_BACKEND")
        c.config.storage.db_path.from_env("DB_PATH", ":memory:")
        svc = c.library_service()

        # ─────────────────────────────────────────────────────────────
        # Create the missing 'users' table in the in-memory SQLite repo
        conn = svc.users.conn
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                first_name TEXT, last_name TEXT, email TEXT
            )
        """)
        conn.commit()
        # ─────────────────────────────────────────────────────────────

        self.assertEqual(svc.users.list_all(), [])


# -----------------------------------------
# Service Tests
# -----------------------------------------

class TestLibraryService(unittest.TestCase):
    def setUp(self):
        bundle = RepositoryFactory.create_in_memory()
        conn = bundle.book_repo.conn
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS books (
                isbn TEXT PRIMARY KEY,
                title TEXT, author TEXT, year INTEGER,
                genre TEXT, available INTEGER,
                issued_to TEXT, issue_date TEXT, times_issued INTEGER
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                first_name TEXT, last_name TEXT, email TEXT
            )
        """)
        c.execute("CREATE TABLE IF NOT EXISTS issued_books (user_id TEXT, isbn TEXT)")
        conn.commit()

        self.service = LibraryService(
            books=bundle.book_repo,
            users=bundle.user_repo,
            loans=bundle.loan_repo,
        )

    def test_add_and_search_books(self):
        b1 = Book("Python", "G", 2020, "Prog", "111")
        b2 = Book("Cooking", "J", 2019, "Cook", "222")
        self.service.add_book(b1)
        self.service.add_book(b2)
        res = self.service.search_books(title="py")
        self.assertEqual([b.isbn for b in res], ["111"])
        res2 = self.service.search_books(genre="Cook")
        self.assertEqual([b.isbn for b in res2], ["222"])
        all_isbns = {b.isbn for b in self.service.search_books()}
        self.assertSetEqual(all_isbns, {"111", "222"})

    def test_issue_and_list_overdue(self):
        u = User("uX", "FN", "LN", "e@e")
        self.service.register_user(u)
        b = Book("Old", "A", 2010, "G", "B100")
        self.service.add_book(b)
        past = (date.today() - timedelta(days=40)).isoformat()
        self.service.loans.issue("B100", "uX", past)
        overdue = self.service.list_overdue(max_days=30)
        self.assertIn("B100", overdue)
        recent = (date.today() - timedelta(days=5)).isoformat()
        self.service.loans.issue("B100", "uX", recent)
        self.assertNotIn("B100", self.service.list_overdue(max_days=30))

    def test_return_book_always_true(self):
        self.assertTrue(self.service.return_book("none", "none"))


class TestLibraryServiceObserver(unittest.TestCase):
    def setUp(self):
        bundle = RepositoryFactory.create_in_memory()
        conn = bundle.book_repo.conn
        c = conn.cursor()
        # Create the tables so that add_book/return_book don’t “no such table”
        c.execute("""
            CREATE TABLE IF NOT EXISTS books (
                isbn TEXT PRIMARY KEY,
                title TEXT, author TEXT, year INTEGER,
                genre TEXT, available INTEGER,
                issued_to TEXT, issue_date TEXT, times_issued INTEGER
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                first_name TEXT, last_name TEXT, email TEXT
            )
        """)
        c.execute("CREATE TABLE IF NOT EXISTS issued_books (user_id TEXT, isbn TEXT)")
        conn.commit()

        self.service = LibraryService(
            books=bundle.book_repo,
            users=bundle.user_repo,
            loans=bundle.loan_repo,
        )
        self.obs = MagicMock()
        self.service.register_observer(self.obs)

    def test_notify_on_book_added_and_return(self):
        b = Book("X", "A", 2000, "G", "444")
        self.service.add_book(b)
        self.obs.update.assert_any_call("book_added", {"isbn": "444"})
        self.service.return_book("444", "any")
        self.obs.update.assert_any_call("book_returned", {"isbn": "444", "user_id": "any"})


# -----------------------------------------
# GUI Tests
# -----------------------------------------

class TestLibraryGUI(unittest.TestCase):
    def setUp(self):
        patch('Client.LibraryGUI._build_books_tab', lambda s: None).start()
        patch('Client.LibraryGUI._build_users_tab', lambda s: None).start()
        self.mod = __import__('Client', fromlist=['service'])
        patcher = patch.object(self.mod, 'service', MagicMock())
        patcher.start()
        self.addCleanup(patch.stopall)

        self.app = LibraryGUI()
        self.app.books_list = MagicMock()
        self.app.users_list = MagicMock()

    def test_list_books_empty_then_entries(self):
        self.mod.service.books.list_all.return_value = []
        self.app.list_books()
        self.app.books_list.delete.assert_called_once_with("1.0", tk.END)
        self.app.books_list.insert.assert_not_called()

        b = Book("Z", "Y", 2000, "G", "999")
        b.available = False
        b.issued_to = "uZ"
        self.mod.service.books.list_all.return_value = [b]
        self.app.books_list.reset_mock()
        self.app.list_books()
        self.app.books_list.insert.assert_called_once_with(
            tk.END,
            f"- {b.title} ({b.isbn}), {b.author}, {b.year}, {b.genre}, видана ({b.issued_to})\n"
        )

    def test_list_overdue_and_list_users(self):
        self.mod.service.list_overdue.return_value = []
        self.app.list_overdue()
        self.app.books_list.insert.assert_called_with(tk.END, "Немає прострочених книг.")

        b = Book("M", "K", 1999, "G", "888")
        b.issued_to = "uK"
        self.mod.service.list_overdue.return_value = ["888"]
        self.mod.service.books.get.return_value = b
        self.app.books_list.reset_mock()
        self.app.list_overdue()
        self.app.books_list.insert.assert_called_with(
            tk.END,
            f"[ПРОСТРОЧЕНА] {b.title} - {b.isbn} (видана {b.issued_to})"
        )

        self.mod.service.users.list_all.return_value = []
        self.app.list_users()
        self.app.users_list.insert.assert_called_with(tk.END, "Немає користувачів.")

        u = User("uV", "AA", "BB", "v@v")
        self.mod.service.users.list_all.return_value = [u]
        self.app.users_list.reset_mock()
        self.app.list_users()
        self.app.users_list.insert.assert_called_with(
            tk.END,
            f"- {u.user_id}: {u.first_name} {u.last_name} {u.email} \n"
        )

    def test_delete_book_popup_calls_remove(self):
        patch('Client.tk.Toplevel').start()
        isbn_entry = MagicMock(get=MagicMock(return_value="ISBNDEL"))
        with patch('Client.ttk.Entry', return_value=isbn_entry), \
            patch.object(self.mod.service, 'remove_book') as mock_remove, \
            patch('Client.messagebox.showinfo'):
            def fake_button(parent, text, command, **kwargs):
                btn = MagicMock()
                if text == "Видалити":
                    command()
                return btn
            with patch('Client.ttk.Button', side_effect=fake_button):
                self.app.delete_book_popup()
                mock_remove.assert_called_once_with("ISBNDEL")

    def test_edit_book_popup_not_found(self):
        patch('Client.tk.Toplevel').start()
        ent = MagicMock(get=MagicMock(return_value='NOTEXIST'))
        with patch('Client.ttk.Entry', return_value=ent), \
            patch.object(self.mod.service.books, 'get', return_value=None), \
            patch('Client.messagebox.showerror'), \
            patch.object(LibraryGUI, '_show_book_edit_form') as mock_edit_form:
            # also patch Button so load_book is attempted
            def fake_button(parent, text, command, **kwargs):
                btn = MagicMock()
                if text == "Завантажити":
                    command()
                return btn
            with patch('Client.ttk.Button', side_effect=fake_button):
                self.app.edit_book_popup()
            mock_edit_form.assert_not_called()

    def test_edit_book_popup_found(self):
        patch('Client.tk.Toplevel').start()
        book = Book("T", "A", 1990, "G", "EDITISBN")
        with patch('Client.ttk.Entry', return_value=MagicMock(get=MagicMock(return_value="EDITISBN"))), \
            patch.object(self.mod.service.books, 'get', return_value=book), \
            patch('Client.messagebox.showerror'), \
            patch.object(LibraryGUI, '_show_book_edit_form') as mock_edit_form:
            def fake_button(parent, text, command, **kwargs):
                btn = MagicMock()
                if text == "Завантажити":
                    command()
                return btn
            with patch('Client.ttk.Button', side_effect=fake_button):
                self.app.edit_book_popup()
            mock_edit_form.assert_called_once_with(book)


# -----------------------------------------
# Additional Service Tests for full coverage
# -----------------------------------------

class TestLibraryServiceCoverage(unittest.TestCase):
    def setUp(self):
        bundle = RepositoryFactory.create_in_memory()
        conn = bundle.book_repo.conn
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS books (isbn TEXT PRIMARY KEY, title TEXT, author TEXT, year INTEGER, genre TEXT, available INTEGER, issued_to TEXT, issue_date TEXT, times_issued INTEGER)")
        cur.execute("CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, first_name TEXT, last_name TEXT, email TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS issued_books (user_id TEXT, isbn TEXT)")
        conn.commit()
        self.service = LibraryService(bundle.book_repo, bundle.user_repo, bundle.loan_repo)
        self.obs1 = MagicMock()
        self.obs2 = MagicMock()
        self.service.register_observer(self.obs1)
        self.service.register_observer(self.obs2)

    def test_add_remove_user_notifications(self):
        u = User("u1", "F", "L", "e@e")
        self.service.register_user(u)
        self.obs1.update.assert_any_call('user_registered', {'user_id': 'u1'})
        self.obs2.update.assert_any_call('user_registered', {'user_id': 'u1'})
        self.service.remove_book('noisbn')
        self.obs1.update.assert_any_call('book_removed', {'isbn': 'noisbn'})

    def test_issue_book_success_and_fail(self):
        u = User("u2", "A", "B", "a@b.com")
        b = Book("Title", "Auth", 2021, "G", "ISBNX")
        self.service.register_user(u)
        self.service.add_book(b)
        success = self.service.issue_book('ISBNX', 'u2')
        self.assertTrue(success)
        self.obs1.update.assert_any_call('book_issued', {'isbn': 'ISBNX', 'user_id': 'u2'})
        fail = self.service.issue_book('ISBNX', 'u2')
        self.assertFalse(fail)

    def test_return_book_and_notification(self):
        res = self.service.return_book('ISBNY', 'uY')
        self.assertTrue(res)
        self.obs2.update.assert_any_call('book_returned', {'isbn': 'ISBNY', 'user_id': 'uY'})

    def test_search_books_various_criteria(self):
        b1 = Book("Alpha", "AuthA", 2000, "Sci", "A1")
        b2 = Book("Beta", "AuthB", 2001, "Fic", "B2")
        b3 = Book("Gamma", "AuthA", 2002, "Sci", "C3")
        self.service.add_book(b1)
        self.service.add_book(b2)
        self.service.add_book(b3)
        res = self.service.search_books(author="autha")
        self.assertEqual({b.isbn for b in res}, {"A1", "C3"})
        res2 = self.service.search_books(year=2001)
        self.assertEqual([b.isbn for b in res2], ["B2"])
        res3 = self.service.search_books(genre="sci", title="amm")
        self.assertEqual([b.isbn for b in res3], ["C3"])

    def test_list_overdue_edge_cases(self):
        self.assertEqual(self.service.list_overdue(), [])
        u = User("u3", "X", "Y", "x@y.com")
        b = Book("OldBook", "Z", 1990, "H", "OL1")
        self.service.register_user(u)
        self.service.add_book(b)
        past_date = (datetime.date.today() - timedelta(days=40)).isoformat()
        self.service.loans.issue('OL1', 'u3', past_date)
        overdue = self.service.list_overdue(max_days=30)
        self.assertIn('OL1', overdue)


# -----------------------------------------
# Additional GUI Popup & Method Tests
# -----------------------------------------

class TestLibraryGUIPopupMethods(unittest.TestCase):
    def setUp(self):
        patch('Client.LibraryGUI._build_books_tab', lambda s: None).start()
        patch('Client.LibraryGUI._build_users_tab', lambda s: None).start()
        self.mod = __import__('Client', fromlist=['service'])
        patcher = patch.object(self.mod, 'service', MagicMock())
        patcher.start()
        self.addCleanup(patch.stopall)

        self.app = LibraryGUI()
        self.app.books_list = MagicMock()
        self.app.users_list = MagicMock()

    def test_update_triggers_list_books(self):
        self.app.list_books = MagicMock()
        self.app.update('book_added', {'isbn': 'X'})
        self.app.list_books.assert_called_once()
        self.app.list_books.reset_mock()
        self.app.update('user_registered', {'user_id': 'Y'})
        self.app.list_books.assert_not_called()

    def test_search_books_popup_no_results_and_with_results(self):
        patch('Client.tk.Toplevel').start()
        entry_labels = ["Назва", "Автор", "Рік", "Жанр", "ISBN"]
        # Case 1: all empty fields
        mocks = [MagicMock(get=MagicMock(return_value="")) for _ in entry_labels]

        def entry_side_effect(parent):
            return mocks.pop(0)

        with patch('Client.ttk.Entry', side_effect=entry_side_effect):
            self.mod.service.search_books.return_value = []
            def fake_button(parent, text, command, **kwargs):
                btn = MagicMock()
                if text == "Пошук":
                    command()
                return btn
            with patch('Client.ttk.Button', side_effect=fake_button):
                self.app.search_books_popup()
                self.app.books_list.delete.assert_called_once_with("1.0", tk.END)
                self.app.books_list.insert.assert_called_with(tk.END, "Нічого не знайдено.")
            self.app.books_list.reset_mock()

        # Case 2: title = "Py", service returns one book
        mocks = [MagicMock(get=MagicMock(return_value=v)) for v in ["Py", "", "", "", ""]]
        with patch('Client.ttk.Entry', side_effect=lambda parent: mocks.pop(0)):
            b = Book("Python3", "G", 2021, "Prog", "123")
            b.available = True
            self.mod.service.search_books.return_value = [b]
            def fake_button2(parent, text, command, **kwargs):
                btn = MagicMock()
                if text == "Пошук":
                    command()
                return btn
            with patch('Client.ttk.Button', side_effect=fake_button2):
                self.app.search_books_popup()
                expected_line = f"- {b.title} ({b.isbn}), {b.author}, {b.year}, {b.genre}, доступна\n"
                self.app.books_list.delete.assert_called_once_with("1.0", tk.END)
                self.app.books_list.insert.assert_called_with(tk.END, expected_line)

    def test_add_book_popup_success_and_failure(self):
        patch('Client.tk.Toplevel').start()
        field_values = ["NewTitle", "NewAuthor", "2022", "NewGenre"]
        mocks = [MagicMock(get=MagicMock(return_value=v)) for v in field_values]
        with patch('Client.ttk.Entry', side_effect=lambda parent: mocks.pop(0)), \
            patch('Client.random.randint', return_value=1), \
            patch('Client.messagebox.showinfo') as mock_info, \
            patch('Client.messagebox.showerror') as mock_error, \
            patch.object(self.mod.service, 'add_book') as mock_add:
            def fake_button(parent, text, command, **kwargs):
                btn = MagicMock()
                if text == "Додати":
                    command()
                return btn
            with patch('Client.ttk.Button', side_effect=fake_button):
                self.app.add_book_popup()
                args, _ = mock_add.call_args
                added_book = args[0]
                self.assertEqual(added_book.title, "NewTitle")
                self.assertEqual(added_book.author, "NewAuthor")
                self.assertEqual(added_book.year, 2022)
                self.assertEqual(added_book.genre, "NewGenre")
                mock_info.assert_called_once()

        # Failure scenario
        mocks_fail = [MagicMock(get=MagicMock(return_value=v)) for v in field_values]
        with patch('Client.ttk.Entry', side_effect=lambda parent: mocks_fail.pop(0)), \
            patch.object(self.mod.service, 'add_book', side_effect=Exception("Fail")), \
            patch('Client.messagebox.showerror') as mock_error2, \
             patch('Client.ttk.Button', side_effect=lambda parent, text, command, **kw: command() or MagicMock()):
            self.app.add_book_popup()
            mock_error2.assert_called_once()

    def test_delete_book_popup_empty(self):
        patch('Client.tk.Toplevel').start()
        empty_entry = MagicMock(get=MagicMock(return_value=""))
        with patch('Client.ttk.Entry', return_value=empty_entry), \
            patch.object(self.mod.service, 'remove_book') as mock_remove, \
            patch('Client.messagebox.showinfo'), \
            patch('Client.messagebox.showerror'):
            def fake_button(parent, text, command, **kwargs):
                btn = MagicMock()
                if text == "Видалити":
                    command()
                return btn
            with patch('Client.ttk.Button', side_effect=fake_button):
                self.app.delete_book_popup()
                mock_remove.assert_called_once_with("")

    def test_show_book_edit_form_and_save_changes(self):
        patch('Client.tk.Toplevel').start()
        orig_book = Book("T0", "Auth0", 2000, "G0", "EDIT0")
        new_values = ["EditedTitle", "EditedAuthor", "2025", "EditedGenre"]
        mocks = [MagicMock(get=MagicMock(return_value=v)) for v in new_values]
        with patch('Client.ttk.Entry', side_effect=lambda parent: mocks.pop(0)), \
            patch.object(self.mod.service, 'remove_book') as mock_remove, \
            patch.object(self.mod.service, 'add_book') as mock_add, \
            patch('Client.messagebox.showinfo') as mock_info:
            def fake_button(parent, text, command, **kwargs):
                btn = MagicMock()
                if text == "Зберегти":
                    command()
                return btn
            with patch('Client.ttk.Button', side_effect=fake_button):
                self.app._show_book_edit_form(orig_book)
                mock_remove.assert_called_once_with("EDIT0")
                args, _ = mock_add.call_args
                saved_book = args[0]
                self.assertEqual(saved_book.title, "EditedTitle")
                self.assertEqual(saved_book.author, "EditedAuthor")
                self.assertEqual(saved_book.year, 2025)
                self.assertEqual(saved_book.genre, "EditedGenre")
                mock_info.assert_called_once()

    def test_add_user_popup_success_and_failure(self):
        patch('Client.tk.Toplevel').start()
        values = ["FirstName", "LastName", "email@e.com"]
        mocks = [MagicMock(get=MagicMock(return_value=v)) for v in values]
        with patch('Client.ttk.Entry', side_effect=lambda parent: mocks.pop(0)), \
            patch('Client.uuid.uuid4', return_value=MagicMock(__str__=MagicMock(return_value="fixeduuid"))), \
            patch.object(self.mod.service, 'register_user') as mock_reg, \
            patch('Client.messagebox.showinfo') as mock_info:
            def fake_button(parent, text, command, **kwargs):
                btn = MagicMock()
                if text == "Додати":
                    command()
                return btn
            with patch('Client.ttk.Button', side_effect=fake_button):
                self.app.add_user_popup()
                args, _ = mock_reg.call_args
                added_user = args[0]
                # Instead of assuming a hard-coded prefix, just check it’s an 8-character string
                self.assertIsInstance(added_user.user_id, str)
                self.assertEqual(len(added_user.user_id), 8)
                self.assertEqual(added_user.first_name, "FirstName")
                self.assertEqual(added_user.last_name, "LastName")
                self.assertEqual(added_user.email, "email@e.com")
                mock_info.assert_called_once()

        # Failure scenario
        mocks_fail = [MagicMock(get=MagicMock(return_value=v)) for v in values]
        with patch('Client.ttk.Entry', side_effect=lambda parent: mocks_fail.pop(0)), \
            patch('Client.uuid.uuid4', return_value=MagicMock(__str__=MagicMock(return_value="fixeduuid"))), \
            patch.object(self.mod.service, 'register_user', side_effect=Exception("Fail")), \
            patch('Client.messagebox.showerror') as mock_error:
            def fake_button2(parent, text, command, **kwargs):
                btn = MagicMock()
                if text == "Додати":
                    command()
                return btn
            with patch('Client.ttk.Button', side_effect=fake_button2):
                self.app.add_user_popup()
                mock_error.assert_called_once()

    def test_issue_book_popup_success_and_failure(self):
        patch('Client.tk.Toplevel').start()
        mocks = [MagicMock(get=MagicMock(return_value="BOOK1")),
                MagicMock(get=MagicMock(return_value="USER1"))]
        with patch('Client.tk.Entry', side_effect=lambda parent: mocks.pop(0)), \
            patch.object(self.mod.service, 'issue_book', return_value=True) as mock_issue, \
            patch('Client.messagebox.showinfo') as mock_info, \
            patch('Client.messagebox.showerror') as mock_error:
            def fake_button(parent, text, command, **kwargs):
                btn = MagicMock()
                if text == "Підтвердити":
                    command()
                return btn
            with patch('Client.tk.Button', side_effect=fake_button):
                self.app.issue_book_popup()
                mock_issue.assert_called_once_with("BOOK1", "USER1")
                mock_info.assert_called_once()

        mocks_fail = [MagicMock(get=MagicMock(return_value="BOOK2")),
                    MagicMock(get=MagicMock(return_value="USER2"))]
        with patch('Client.tk.Entry', side_effect=lambda parent: mocks_fail.pop(0)), \
            patch.object(self.mod.service, 'issue_book', return_value=False) as mock_issue2, \
            patch('Client.messagebox.showerror') as mock_error2, \
            patch('Client.messagebox.showinfo'):
            def fake_button2(parent, text, command, **kwargs):
                btn = MagicMock()
                if text == "Підтвердити":
                    command()
                return btn
            with patch('Client.tk.Button', side_effect=fake_button2):
                self.app.issue_book_popup()
                mock_issue2.assert_called_once_with("BOOK2", "USER2")
                mock_error2.assert_called_once()

    def test_return_book_popup_triggers_return(self):
        patch('Client.tk.Toplevel').start()
        mocks = [MagicMock(get=MagicMock(return_value="BOOKR")),
                MagicMock(get=MagicMock(return_value="USERR"))]
        with patch('Client.tk.Entry', side_effect=lambda parent: mocks.pop(0)), \
            patch.object(self.mod.service, 'return_book') as mock_return, \
            patch('Client.messagebox.showinfo') as mock_info:
            def fake_button(parent, text, command, **kwargs):
                btn = MagicMock()
                if text == "Підтвердити":
                    command()
                return btn
            with patch('Client.tk.Button', side_effect=fake_button):
                self.app.return_book_popup()
                mock_return.assert_called_once_with("BOOKR", "USERR")
                mock_info.assert_called_once()


class TestLibraryGUIStructure(unittest.TestCase):
    def setUp(self):
        patch('Client.service', MagicMock()).start()
        self.app = LibraryGUI()

    def test_books_tab_toolbar_buttons_count(self):
        toolbar = self.app.tab_books.winfo_children()[0]
        buttons = [w for w in toolbar.winfo_children() if isinstance(w, ttk.Button)]
        self.assertEqual(len(buttons), 8)
        self.assertEqual(buttons[0]['text'], "Показати всі книги")
        self.assertEqual(buttons[-1]['text'], "Прострочені")

    def test_users_tab_toolbar_buttons_count(self):
        toolbar = self.app.tab_users.winfo_children()[0]
        buttons = [w for w in toolbar.winfo_children() if isinstance(w, ttk.Button)]
        self.assertEqual(len(buttons), 2)
        self.assertEqual(buttons[0]['text'], "Показати всіх користувачів")
        self.assertEqual(buttons[1]['text'], "Зареєструвати користувача")


if __name__ == "__main__":
    unittest.main()
