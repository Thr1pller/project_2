import tkinter as tk
from tkinter import ttk, messagebox
import random
import uuid
from container import Container
from library.book import Book
from library.user import User

# Налаштування DI-контейнера
container = Container()
container.config.storage.backend.from_env('STORAGE_BACKEND', 'sqlite')
container.config.storage.db_path.from_env('DB_PATH', 'library.db')
service = container.library_service()

class LibraryGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Library Manager")
        self.geometry("850x500")

        # Observer pattern: підписуємо GUI на події сервісу
        service.register_observer(self)

        # Створюємо вкладки
        tabs = ttk.Notebook(self)
        self.tab_books = ttk.Frame(tabs)
        self.tab_users = ttk.Frame(tabs)
        tabs.add(self.tab_books, text="Книги")
        tabs.add(self.tab_users, text="Користувачі")
        tabs.pack(expand=1, fill="both")

        # Будуємо UI
        self._build_books_tab()
        self._build_users_tab()

    def update(self, event: str, data: dict):
        """
        Метод Observer: реагує на події з LibraryService.
        Наприклад, після додавання або видачі книги автоматично перелічує всі книги.
        """
        if event in ('book_added', 'book_removed', 'book_issued', 'book_returned'):
            self.list_books()

    def _build_books_tab(self):
        frame = self.tab_books
        toolbar = ttk.Frame(frame)
        toolbar.pack(fill="x", pady=5)

        for text, cmd in [
            ("Показати всі книги", self.list_books),
            ("Пошук книг", self.search_books_popup),
            ("Додати книгу", self.add_book_popup),
            ("Редагувати книгу", self.edit_book_popup),
            ("Видалити книгу", self.delete_book_popup),
            ("Видати книгу", self.issue_book_popup),
            ("Повернути книгу", self.return_book_popup),
            ("Прострочені", self.list_overdue)
        ]:
            ttk.Button(toolbar, text=text, command=cmd).pack(side="left", padx=5)

        self.books_list = tk.Text(frame, height=30)
        self.books_list.pack(fill="both", padx=5, pady=5)

    def _build_users_tab(self):
        frame = self.tab_users
        toolbar = ttk.Frame(frame)
        toolbar.pack(fill="x", pady=5)

        for text, cmd in [
            ("Показати всіх користувачів", self.list_users),
            ("Зареєструвати користувача", self.add_user_popup)
        ]:
            ttk.Button(toolbar, text=text, command=cmd).pack(side="left", padx=5)

        self.users_list = tk.Text(frame, height=25)
        self.users_list.pack(fill="both", padx=5, pady=5)

    def list_books(self):
        self.books_list.delete("1.0", tk.END)
        for book in service.books.list_all():
            status = "доступна" if book.available else f"видана ({book.issued_to})"
            self.books_list.insert(
                tk.END,
                f"- {book.title} ({book.isbn}), {book.author}, {book.year}, {book.genre}, {status}\n"
            )

    def list_overdue(self):
        self.books_list.delete("1.0", tk.END)
        overdue = service.list_overdue()
        if not overdue:
            self.books_list.insert(tk.END, "Немає прострочених книг.")
            return
        for isbn in overdue:
            book = service.books.get(isbn)
            if book:
                self.books_list.insert(
                    tk.END,
                    f"[ПРОСТРОЧЕНА] {book.title} - {isbn} (видана {book.issued_to})"
                )

    def search_books_popup(self):
        popup = tk.Toplevel(self)
        popup.title("Пошук книг")
        fields = ["Назва", "Автор", "Рік", "Жанр", "ISBN"]
        entries = {}
        for i, label in enumerate(fields):
            ttk.Label(popup, text=label).grid(row=i, column=0, sticky="e", padx=5, pady=5)
            ent = ttk.Entry(popup)
            ent.grid(row=i, column=1, padx=5, pady=5)
            entries[label] = ent

        def submit():
            crit = {}
            if entries["Назва"].get():    crit["title"] = entries["Назва"].get()
            if entries["Автор"].get():   crit["author"] = entries["Автор"].get()
            if entries["Рік"].get():      crit["year"] = int(entries["Рік"].get())
            if entries["Жанр"].get():     crit["genre"] = entries["Жанр"].get()
            if entries["ISBN"].get():     crit["isbn"] = entries["ISBN"].get()

            results = service.search_books(**crit)
            self.books_list.delete("1.0", tk.END)
            if not results:
                self.books_list.insert(tk.END, "Нічого не знайдено.")
            else:
                for b in results:
                    status = "доступна" if b.available else f"видана ({b.issued_to})"
                    self.books_list.insert(
                        tk.END,
                        f"- {b.title} ({b.isbn}), {b.author}, {b.year}, {b.genre}, {status}\n"
                    )
            popup.destroy()

        ttk.Button(popup, text="Пошук", command=submit).grid(row=len(fields), column=0, columnspan=2, pady=10)

    def add_book_popup(self):
        popup = tk.Toplevel(self)
        popup.title("Додати книгу")
        fields = ["Назва", "Автор", "Рік видання", "Жанр"]
        entries = {}
        for i, label in enumerate(fields):
            ttk.Label(popup, text=label).grid(row=i, column=0, sticky="e", pady=5)
            ent = ttk.Entry(popup)
            ent.grid(row=i, column=1, padx=5, pady=5)
            entries[label] = ent
        isbn_val = ''.join(str(random.randint(0, 9)) for _ in range(13))

        def submit_book():
            try:
                book = Book(
                    entries["Назва"].get(),
                    entries["Автор"].get(),
                    int(entries["Рік видання"].get()),
                    entries["Жанр"].get(),
                    isbn_val
                )
                service.add_book(book)
                messagebox.showinfo("Успіх", "Книгу додано")
                popup.destroy()
                self.list_books()
            except Exception as e:
                messagebox.showerror("Помилка", f"Не вдалося: {e}")

        ttk.Button(popup, text="Додати", command=submit_book).grid(
            row=len(fields), column=0, columnspan=2, pady=10
        )

    def delete_book_popup(self):
        popup = tk.Toplevel(self)
        popup.title("Видалити книгу")
        ttk.Label(popup, text="ISBN книги").pack(padx=5, pady=5)
        ent = ttk.Entry(popup)
        ent.pack(padx=5, pady=5)

        def delete_book():
            try:
                service.remove_book(ent.get())
                messagebox.showinfo("Успіх", "Книгу видалено")
                popup.destroy()
                self.list_books()
            except Exception as e:
                messagebox.showerror("Помилка", f"Не вдалося: {e}")

        ttk.Button(popup, text="Видалити", command=delete_book).pack(pady=10)

    def edit_book_popup(self):
        popup = tk.Toplevel(self)
        popup.title("Редагувати книгу")
        ttk.Label(popup, text="ISBN книги").grid(row=0, column=0, padx=5, pady=5)
        ent = ttk.Entry(popup)
        ent.grid(row=0, column=1, padx=5, pady=5)

        def load_book():
            book = service.books.get(ent.get())
            if not book:
                messagebox.showerror("Помилка", "Книгу не знайдено")
                popup.destroy()
                return
            popup.destroy()
            self._show_book_edit_form(book)

        ttk.Button(popup, text="Завантажити", command=load_book).grid(
            row=1, column=0, columnspan=2, pady=10
        )

    def _show_book_edit_form(self, book: Book):
        popup = tk.Toplevel(self)
        popup.title(f"Редагувати: {book.title}")
        fields = {
            "Назва": book.title,
            "Автор": book.author,
            "Рік видання": book.year,
            "Жанр": book.genre
        }
        entries = {}
        for i, (lbl, val) in enumerate(fields.items()):
            ttk.Label(popup, text=lbl).grid(row=i, column=0, sticky="e", padx=5, pady=5)
            ent = ttk.Entry(popup)
            ent.insert(0, val)
            ent.grid(row=i, column=1, padx=5, pady=5)
            entries[lbl] = ent

        def save_changes():
            try:
                book.title = entries["Назва"].get()
                book.author = entries["Автор"].get()
                book.year = int(entries["Рік видання"].get())
                book.genre = entries["Жанр"].get()
                service.remove_book(book.isbn)
                service.add_book(book)
                messagebox.showinfo("Успіх", "Зміни збережено")
                popup.destroy()
                self.list_books()
            except Exception as e:
                messagebox.showerror("Помилка", f"Не вдалося: {e}")

        ttk.Button(popup, text="Зберегти", command=save_changes).grid(
            row=len(fields), column=0, columnspan=2, pady=10
        )

    def list_users(self):
        self.users_list.delete("1.0", tk.END)
        users = service.users.list_all()
        if not users:
            self.users_list.insert(tk.END, "Немає користувачів.")
            return
        for u in users:
            self.users_list.insert(
                tk.END,
                f"- {u.user_id}: {u.first_name} {u.last_name} {u.email} \n"
            )

    def add_user_popup(self):
        popup = tk.Toplevel(self)
        popup.title("Зареєструвати користувача")
        fields = ["Ім'я", "Прізвище", "Email"]
        entries = {}
        for i, label in enumerate(fields):
            ttk.Label(popup, text=label).grid(row=i, column=0, sticky="e", pady=5)
            ent = ttk.Entry(popup)
            ent.grid(row=i, column=1, padx=5, pady=5)
            entries[label] = ent

        def submit_user():
            try:
                uid = str(uuid.uuid4())[:8]
                user = User(
                    uid,
                    entries["Ім'я"].get(),
                    entries["Прізвище"].get(),
                    entries["Email"].get()
                )
                service.register_user(user)
                messagebox.showinfo("Успіх", f"Користувача додано. ID: {uid}")
                popup.destroy()
                self.list_users()
            except Exception as e:
                messagebox.showerror("Помилка", f"Не вдалося: {e}")

        ttk.Button(popup, text="Додати", command=submit_user).grid(
            row=len(fields), column=0, columnspan=2, pady=10
        )

    def issue_book_popup(self):
        popup = tk.Toplevel(self)
        popup.title("Видати книгу")

        tk.Label(popup, text="ISBN книги:").grid(row=0, column=0, padx=5, pady=5)
        isbn_entry = tk.Entry(popup)
        isbn_entry.grid(row=0, column=1, padx=5, pady=5)

        tk.Label(popup, text="ID користувача:").grid(row=1, column=0, padx=5, pady=5)
        user_id_entry = tk.Entry(popup)
        user_id_entry.grid(row=1, column=1, padx=5, pady=5)

        def confirm_issue():
            success = service.issue_book(isbn_entry.get(), user_id_entry.get())
            if success:
                messagebox.showinfo("Успіх", "Книгу видано успішно")
            else:
                messagebox.showerror("Помилка", "Неможливо видати книгу")
            popup.destroy()

        tk.Button(popup, text="Підтвердити", command=confirm_issue).grid(
            row=2, column=0, columnspan=2, pady=10
        )

    def return_book_popup(self):
        popup = tk.Toplevel(self)
        popup.title("Повернути книгу")

        tk.Label(popup, text="ISBN книги:").grid(row=0, column=0, padx=5, pady=5)
        isbn_entry = tk.Entry(popup)
        isbn_entry.grid(row=0, column=1, padx=5, pady=5)

        tk.Label(popup, text="ID користувача:").grid(row=1, column=0, padx=5, pady=5)
        user_id_entry = tk.Entry(popup)
        user_id_entry.grid(row=1, column=1, padx=5, pady=5)

        def confirm_return():
            service.return_book(isbn_entry.get(), user_id_entry.get())
            messagebox.showinfo("Успіх", "Книгу повернуто")
            popup.destroy()

        tk.Button(popup, text="Підтвердити", command=confirm_return).grid(
            row=2, column=0, columnspan=2, pady=10
        )


if __name__ == "__main__":
    app = LibraryGUI()
    app.mainloop()
