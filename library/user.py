class User:
    def __init__(
        self,
        user_id: str,
        first_name: str,
        last_name: str,
        email: str
    ):
        self.user_id = user_id
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.issued_books = []

    def __repr__(self):
        return f"User({self.user_id!r}, {self.email!r})"