from __future__ import annotations

from types import SimpleNamespace

from app.services.openai_agent import OpenAIAgentService


def test_agent_examples_endpoint_returns_public_example_shape(api_client) -> None:
    response = api_client.get("/api/agent/examples")

    assert response.status_code == 200
    payload = response.json()
    assert "items" in payload
    assert isinstance(payload["items"], list)
    assert len(payload["items"]) >= 5

    for item in payload["items"]:
        assert set(item) == {
            "title",
            "description",
            "endpoint",
            "method",
            "request_body",
            "expected_response_shape",
        }
        assert item["endpoint"] == "/api/agent/query"
        assert item["method"] == "POST"


def test_openai_agent_falls_back_to_deterministic_when_not_ready(db_session) -> None:
    settings = SimpleNamespace(
        openai_api_key=None,
        openai_model="gpt-5",
        kol_data_mode="seed",
        enabled_chains=["56", "CT_501"],
        agent_mode="openai",
    )
    service = OpenAIAgentService(db_session, settings=settings)

    response = service.answer_question(message="help", debug=False)

    assert set(response) == {"answer", "evidence_used", "missing_data", "tool_trace", "disclaimer"}
    assert response["answer"]
    assert response["disclaimer"]


def test_openai_agent_builds_strict_tool_schemas_with_all_properties_required(db_session) -> None:
    settings = SimpleNamespace(
        openai_api_key="test-key",
        openai_model="gpt-5-nano",
        kol_data_mode="seed",
        enabled_chains=["56", "CT_501"],
        agent_mode="openai",
    )
    service = OpenAIAgentService(db_session, settings=settings)

    tools = service._build_openai_tools(intent="token_explanation")

    assert tools
    for tool in tools:
        parameters = tool["parameters"]
        assert parameters["type"] == "object"
        assert sorted(parameters["required"]) == sorted(parameters["properties"].keys())


def test_openai_agent_narrows_tool_set_for_token_explanation_intent(db_session) -> None:
    settings = SimpleNamespace(
        openai_api_key="test-key",
        openai_model="gpt-5-nano",
        kol_data_mode="seed",
        enabled_chains=["56", "CT_501"],
        agent_mode="openai",
    )
    service = OpenAIAgentService(db_session, settings=settings)

    tools = service._build_openai_tools(intent="token_explanation")
    tool_names = {tool["name"] for tool in tools}

    assert "query_token_info" in tool_names
    assert "query_token_audit" in tool_names
    assert "get_latest_insight" in tool_names
    assert "rank_kols_by_track_record" not in tool_names
    assert "get_kol_call_examples" not in tool_names


def test_openai_agent_applies_bounded_timeout_and_no_retry_overrides(db_session) -> None:
    class FakeClient:
        def __init__(self) -> None:
            self.calls: list[dict[str, float | int]] = []

        def with_options(self, **kwargs):
            self.calls.append(kwargs)
            return self

    settings = SimpleNamespace(
        openai_api_key="test-key",
        openai_model="gpt-5-nano",
        openai_request_timeout_seconds=12.0,
        openai_max_total_seconds=18.0,
        openai_max_tool_rounds=3,
        openai_max_retries=0,
        kol_data_mode="seed",
        enabled_chains=["56", "CT_501"],
        agent_mode="openai",
    )
    fake_client = FakeClient()
    service = OpenAIAgentService(db_session, settings=settings, client=fake_client)

    configured = service._responses_client(client=fake_client, timeout_seconds=7.5)

    assert configured is fake_client
    assert fake_client.calls == [{"timeout": 7.5, "max_retries": 0}]
