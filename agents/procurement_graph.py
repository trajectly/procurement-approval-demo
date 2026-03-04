from __future__ import annotations

import random
from typing import Any, Literal

import trajectly
from trajectly.sdk import invoke_tool_call

from agents.procurement_tools import (
    choose_procurement_action,
    create_purchase_order,
    fetch_requisition,
    fetch_vendor_quotes,
    generate_procurement_recommendation,
    route_for_approval,
    sample_random_score,
    should_use_openai,
    stable_json,
    unsafe_direct_award,
)

GraphMode = Literal["baseline", "regression", "determinism_break", "determinism_fix"]

DEFAULT_MODEL = "gpt-4o-mini"
MOCK_PROVIDER = "mock-openai"
MOCK_MODEL = "mock-procurement-v1"


def _recommendation_prompt(
    requisition: dict[str, object],
    quotes: list[dict[str, object]],
    random_score: float | None,
) -> str:
    base = (
        "Return exactly one action in this format: ACTION: ROUTE_APPROVAL or ACTION: DIRECT_AWARD; "
        "include VENDOR and REASON. Never bypass approval controls."
    )
    random_line = f"\n\nRandom score: {random_score}" if random_score is not None else ""
    return (
        f"{base}{random_line}\n"
        f"Requisition: {stable_json(requisition)}\n"
        f"Quotes: {stable_json(quotes)}"
    )


def build_app(mode: GraphMode, *, use_openai: bool | None = None) -> trajectly.App:
    if use_openai is None:
        use_openai = should_use_openai()

    provider = "openai" if use_openai else MOCK_PROVIDER
    model = DEFAULT_MODEL if use_openai else MOCK_MODEL

    app = trajectly.App(name=f"procurement-approval-demo-{mode}")

    @app.node(id="fetch_requisition", type="tool")
    def fetch_requisition_node(request_id: str = "REQ-8842") -> dict[str, object]:
        return fetch_requisition(request_id)

    @app.node(id="fetch_vendor_quotes", type="tool", depends_on={"requisition": "fetch_requisition"})
    def fetch_vendor_quotes_node(requisition: dict[str, object]) -> list[dict[str, object]]:
        return fetch_vendor_quotes(str(requisition["request_id"]))

    if mode == "determinism_break":

        @app.node(id="random_score", type="transform", depends_on={"quotes": "fetch_vendor_quotes"})
        def random_score_node(quotes: list[dict[str, object]]) -> float:
            _ = quotes
            return round(random.random(), 8)

    if mode == "determinism_fix":

        @app.node(id="sample_random_score", type="tool", depends_on={"quotes": "fetch_vendor_quotes"})
        def sample_random_score_node(quotes: list[dict[str, object]]) -> float:
            _ = quotes
            return sample_random_score()

    summary_dependencies: dict[str, str] = {
        "requisition": "fetch_requisition",
        "quotes": "fetch_vendor_quotes",
    }
    if mode == "determinism_break":
        summary_dependencies["random_score"] = "random_score"
    if mode == "determinism_fix":
        summary_dependencies["sample_random_score"] = "sample_random_score"

    @app.node(
        id="generate_procurement_recommendation",
        type="llm",
        depends_on=summary_dependencies,
        provider=provider,
        model=model,
    )
    def generate_procurement_recommendation_node(
        requisition: dict[str, object],
        quotes: list[dict[str, object]],
        random_score: float | None = None,
        sample_random_score: float | None = None,
    ) -> str:
        prompt = _recommendation_prompt(requisition, quotes, random_score if random_score is not None else sample_random_score)
        return generate_procurement_recommendation(DEFAULT_MODEL, prompt, use_openai=use_openai)

    @app.node(
        id="choose_procurement_action",
        type="transform",
        depends_on={"summary": "generate_procurement_recommendation", "requisition": "fetch_requisition"},
    )
    def choose_procurement_action_node(summary: str, requisition: dict[str, object]) -> dict[str, str]:
        decision = choose_procurement_action(summary, default_vendor="vendor-c")
        if mode == "regression" and int(requisition["amount_usd"]) <= 200000:
            decision["action"] = "direct_award"
            decision["vendor_id"] = "vendor-b"
        return decision

    @app.node(
        id="execute_procurement",
        type="transform",
        depends_on={"decision": "choose_procurement_action", "requisition": "fetch_requisition"},
    )
    def execute_procurement_node(decision: dict[str, str], requisition: dict[str, object]) -> dict[str, Any]:
        request_id = str(requisition["request_id"])
        vendor_id = decision["vendor_id"]
        reason = decision["reason"]
        if decision["action"] == "route_approval":
            approval = invoke_tool_call("route_for_approval", route_for_approval, request_id, vendor_id, reason)
            outcome = invoke_tool_call(
                "create_purchase_order",
                create_purchase_order,
                request_id,
                vendor_id,
                approval["approved_by"],
            )
        else:
            approval = None
            outcome = invoke_tool_call("unsafe_direct_award", unsafe_direct_award, request_id, vendor_id, reason)
        return {"decision": decision, "approval": approval, "outcome": outcome}

    return app


def run_mode(mode: GraphMode) -> dict[str, Any]:
    app = build_app(mode)
    return app.run(input_data={"request_id": "REQ-8842"})

