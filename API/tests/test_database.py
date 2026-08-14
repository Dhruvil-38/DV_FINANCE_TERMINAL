import database


def test_get_db_yields_session_and_closes_it():
    generator = database.get_db()
    session = next(generator)

    assert session.is_active
    try:
        next(generator)
    except StopIteration:
        pass
    assert not session.in_transaction()


def test_sqlite_url_disables_same_thread_check():
    assert database.DATABASE_URL.startswith("sqlite")
    assert database.engine.url.get_backend_name() == "sqlite"


def test_session_factory_is_not_autocommit_or_autoflush():
    session = database.SessionLocal()
    try:
        assert session.autoflush is False
    finally:
        session.close()
