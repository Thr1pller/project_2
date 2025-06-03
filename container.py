# container.py
from dependency_injector import containers, providers
from repository.factory import RepositoryFactory
from service.library_service import LibraryService

class Container(containers.DeclarativeContainer):
    config = providers.Configuration()

    storage_strategy = providers.Selector(
        config.storage.backend,
        sqlite=providers.Factory(RepositoryFactory.create_sqlite, db_path=config.storage.db_path),
        in_memory=providers.Factory(RepositoryFactory.create_in_memory),
    )

    # Тепер кожен репозиторій — це екземпляр
    book_repository = providers.Factory(lambda bundle: bundle.book_repo, storage_strategy)
    user_repository = providers.Factory(lambda bundle: bundle.user_repo, storage_strategy)
    loan_repository = providers.Factory(lambda bundle: bundle.loan_repo, storage_strategy)

    library_service = providers.Factory(
        LibraryService,
        books=book_repository,
        users=user_repository,
        loans=loan_repository,
    )
