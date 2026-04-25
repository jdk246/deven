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
