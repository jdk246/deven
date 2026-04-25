from __future__ import annotations

from sqlalchemy import inspect


def test_kol_performance_tables_exist(db_session) -> None:
    inspector = inspect(db_session.bind)
    table_names = set(inspector.get_table_names())

    assert {"kol_calls", "kol_call_price_observations", "kol_track_record_scores"}.issubset(table_names)
