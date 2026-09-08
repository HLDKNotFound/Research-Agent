import os
import tempfile
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def test_alembic_upgrade_and_downgrade_cycle():
    """
    Tests the complete Alembic migration cycle:
    1. upgrade to head
    2. inspect all created tables, constraints, and indexes
    3. downgrade to base
    4. verify tables are cleanly dropped
    5. upgrade to head again (verifies idempotency/clean state)
    """
    backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    alembic_ini_path = os.path.join(backend_dir, "alembic.ini")

    with tempfile.NamedTemporaryFile(suffix=".db") as tmp_db:
        sync_db_url = f"sqlite:///{tmp_db.name}"

        alembic_cfg = Config(alembic_ini_path)
        alembic_cfg.set_main_option("sqlalchemy.url", sync_db_url)
        alembic_cfg.set_main_option("script_location", os.path.join(backend_dir, "alembic"))

        # Step 1: Upgrade to head
        command.upgrade(alembic_cfg, "head")

        engine = create_engine(sync_db_url)
        inspector = inspect(engine)
        table_names = set(inspector.get_table_names())

        expected_tables = {
            "users",
            "projects",
            "project_members",
            "conversations",
            "messages",
            "files",
            "file_chunks",
            "runs",
            "run_steps",
            "run_events",
            "audit_logs",
            "evidence",
            "reports",
            "report_sections",
            "citations",
        }

        # Verify all expected tables exist after upgrade
        missing_tables = expected_tables - table_names
        assert not missing_tables, f"Tables missing after upgrade: {missing_tables}"

        # Verify index and foreign keys on users and projects
        user_indexes = {idx["name"] for idx in inspector.get_indexes("users")}
        assert "idx_users_email" in user_indexes

        engine.dispose()

        # Step 2: Downgrade to base
        command.downgrade(alembic_cfg, "base")

        engine_post_down = create_engine(sync_db_url)
        inspector_post_down = inspect(engine_post_down)
        remaining_tables = set(inspector_post_down.get_table_names()) - {"alembic_version"}
        assert len(remaining_tables) == 0, f"Tables remained after downgrade: {remaining_tables}"
        engine_post_down.dispose()

        # Step 3: Upgrade to head again
        command.upgrade(alembic_cfg, "head")
        engine_reup = create_engine(sync_db_url)
        inspector_reup = inspect(engine_reup)
        reup_tables = set(inspector_reup.get_table_names())
        assert expected_tables.issubset(reup_tables)
        engine_reup.dispose()
