# Status: real

from app.runtime.workflows.resource_generate_v1 import (
    RESOURCE_GENERATE_PRODUCER_BUDGET_TOKENS,
    RESOURCE_GENERATE_V1,
)


def test_resource_generate_producer_budget_covers_structured_ppt_payload() -> None:
    producer = next(node for node in RESOURCE_GENERATE_V1.nodes if node.node_id == "producer")

    assert producer.budget_tokens == RESOURCE_GENERATE_PRODUCER_BUDGET_TOKENS
    assert producer.budget_tokens >= 2400
