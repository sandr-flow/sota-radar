"""Tests for storage layer."""

import pytest
from sqlalchemy import text

from src.storage.database import get_engine, get_session, session_scope, init_db
from src.storage.models import Base, PaperModel, UserModel


class TestDatabase:
    """Test database connection and session management."""

    def test_get_engine_singleton(self, tmp_path):
        """Test that get_engine returns the same instance."""
        import os
        os.environ["DB_PATH"] = str(tmp_path / "test.db")

        engine1 = get_engine()
        engine2 = get_engine()
        assert engine1 is engine2

    def test_get_session_creates_new_session(self):
        """Test that get_session creates a new session each time."""
        session1 = get_session()
        session2 = get_session()
        assert session1 is not session2
        session1.close()
        session2.close()

    def test_session_scope_commits_on_success(self, tmp_path):
        """Test that session_scope commits on successful execution."""
        from src.config.settings import settings

        original_db_path = settings.DB_PATH

        try:
            # Override settings.DB_PATH for this test
            settings.DB_PATH = tmp_path / "test_scope.db"

            # Re-initialize engine with new path
            import src.storage.database as db_module
            db_module._engine = None
            db_module._SessionLocal = None

            # Create a user within session scope
            with session_scope() as session:
                user = UserModel(
                    telegram_id=99999,
                    language="en"
                )
                session.add(user)

            # Verify user was committed
            with session_scope() as session:
                retrieved_user = session.execute(
                    text("SELECT language FROM users WHERE telegram_id = 99999")
                ).fetchone()
                assert retrieved_user is not None
                assert retrieved_user[0] == "en"

        finally:
            # Restore original settings
            settings.DB_PATH = original_db_path
            db_module._engine = None
            db_module._SessionLocal = None

    def test_session_scope_rollbacks_on_error(self, tmp_path):
        """Test that session_scope rollbacks on exception."""
        import os
        from src.config.settings import settings

        original_db_path = settings.DB_PATH

        try:
            # Override settings.DB_PATH for this test
            settings.DB_PATH = tmp_path / "test_rollback.db"

            # Re-initialize engine with new path
            import src.storage.database as db_module
            db_module._engine = None
            db_module._SessionLocal = None

            # Try to create invalid user (should fail constraint)
            with pytest.raises(Exception):
                with session_scope() as session:
                    user = UserModel(telegram_id=None, language="en")
                    session.add(user)
                    session.flush()  # Force flush to trigger error

            # Session should be rolled back - count should be 0
            with session_scope() as session:
                result = session.execute(
                    text("SELECT COUNT(*) FROM users")
                ).fetchone()
                assert result[0] == 0, f"Expected 0 users, got {result[0]}"

        finally:
            # Restore original settings
            settings.DB_PATH = original_db_path
            db_module._engine = None
            db_module._SessionLocal = None


class TestModels:
    """Test database models."""

    def test_paper_model_creation(self):
        """Test PaperModel can be created with required fields."""
        paper = PaperModel(
            source="arxiv",
            source_id="2301.00001",
            title="Test Paper",
            url="https://arxiv.org/abs/2301.00001",
            pdf_url="https://arxiv.org/pdf/2301.00001.pdf",
        )
        assert paper.source == "arxiv"
        assert paper.source_id == "2301.00001"
        assert paper.title == "Test Paper"
        assert paper.summary_json is None  # optional field

    def test_user_model_creation(self):
        """Test UserModel can be created."""
        user = UserModel(
            telegram_id=12345,
            language="ru"
        )
        assert user.telegram_id == 12345
        assert user.language == "ru"
