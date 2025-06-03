class Book:
    def __init__(
        self,
        title: str,
        author: str,
        year: int,
        genre: str,
        isbn: str,
        available: bool = True,
        issued_to: str = None
    ):
        self.title = title
        self.author = author
        self.year = year
        self.genre = genre
        self.isbn = isbn
        self.available = available
        self.issued_to = issued_to
        self.issue_date = None
        self.times_issued = 0

    def __repr__(self):
        return f"Book({self.title!r}, {self.isbn!r})"