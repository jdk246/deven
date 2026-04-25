from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agent_tools.registry import ToolRegistry
from app.models import (
    KOLPost,
    KOLProfile,
    Token,
    TokenAudit,
    TokenInsight,
    TokenMention,
    TokenSnapshot,
)
from app.schemas import BackendValidationCheck, BackendValidationResponse


class BackendValidationService:
    def __init__(
        self,
        db: Session,
        *,
        registry: ToolRegistry | None = None,
    ) -> None:
        self.db = db
        self.registry = registry or ToolRegistry(db=db)

    def validate(self) -> BackendValidationResponse:
        tools = self.registry.list_agent_tools()
        binance_tools = [tool for tool in tools if tool["category"] == "binance_skill"]
        internal_tools = [tool for tool in tools if tool["category"] == "internal_context"]

        checks = [
            self._threshold_check(
                name="kol_profiles",
                expected=20,
                actual=self._count_rows(KOLProfile),
                fix_hint="Run POST /api/admin/refresh with the `kols` job.",
            ),
            self._threshold_check(
                name="kol_posts",
                expected=40,
                actual=self._count_rows(KOLPost),
                fix_hint="Run POST /api/admin/refresh with the `kols` job in seed mode.",
            ),
            self._threshold_check(
                name="token_mentions",
                expected=10,
                actual=self._count_rows(TokenMention),
                fix_hint="Run KOL refresh so extraction and mapping populate token_mentions.",
            ),
            self._threshold_check(
                name="tokens",
                expected=10,
                actual=self._count_rows(Token),
                fix_hint="Run POST /api/admin/refresh with the `market` job.",
            ),
            self._threshold_check(
                name="token_snapshots",
                expected=10,
                actual=self._count_rows(TokenSnapshot),
                fix_hint="Run POST /api/admin/refresh with the `market` job.",
            ),
            self._threshold_check(
                name="token_audits",
                expected=5,
                actual=self._count_rows(TokenAudit),
                fix_hint="Run POST /api/admin/refresh with the `audits` job.",
            ),
            self._threshold_check(
                name="token_insights",
                expected=5,
                actual=self._count_rows(TokenInsight),
                fix_hint="Run POST /api/admin/refresh with the `insights` job.",
            ),
            self._threshold_check(
                name="registered_agent_tools",
                expected=10,
                actual=len(tools),
                fix_hint="Register missing tools in backend/app/agent_tools/registry.py.",
            ),
            self._threshold_check(
                name="registered_binance_skill_tools",
                expected=5,
                actual=len(binance_tools),
                fix_hint="Register all Binance skill tools in backend/app/agent_tools/registry.py.",
            ),
            self._threshold_check(
                name="registered_internal_context_tools",
                expected=6,
                actual=len(internal_tools),
                fix_hint="Register all internal database context tools in backend/app/agent_tools/registry.py.",
            ),
        ]

        overall_status = self._overall_status(checks)
        return BackendValidationResponse(status=overall_status, checks=checks)

    def _count_rows(self, model: type[Any]) -> int:
        return int(self.db.execute(select(func.count()).select_from(model)).scalar_one() or 0)

    def _threshold_check(
        self,
        *,
        name: str,
        expected: int,
        actual: int,
        fix_hint: str,
    ) -> BackendValidationCheck:
        if actual >= expected:
            status = "pass"
        elif actual == 0:
            status = "fail"
        else:
            status = "warn"

        return BackendValidationCheck(
            name=name,
            status=status,
            expected=expected,
            actual=actual,
            fix_hint=fix_hint,
        )

    def _overall_status(self, checks: list[BackendValidationCheck]) -> str:
        statuses = {check.status for check in checks}
        if "fail" in statuses:
            return "fail"
        if "warn" in statuses:
            return "warn"
        return "pass"


__all__ = ["BackendValidationService"]
