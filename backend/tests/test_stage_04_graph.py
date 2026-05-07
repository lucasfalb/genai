from engine.base_graph import create_base_graph, handoff_node, route_after_llm


def test_route_after_llm_responds_without_tool_calls() -> None:
    assert route_after_llm({"pending_tool_calls": None, "linked_agents": []}) == "respond"


def test_route_after_llm_dispatches_regular_tool_calls() -> None:
    assert (
        route_after_llm(
            {
                "pending_tool_calls": [{"name": "search_docs"}],
                "linked_agents": [{"transfer_tool_name": "handoff_billing"}],
            }
        )
        == "tool_call"
    )


def test_route_after_llm_routes_linked_agent_handoff() -> None:
    assert (
        route_after_llm(
            {
                "pending_tool_calls": [{"name": "handoff_billing"}],
                "linked_agents": [{"transfer_tool_name": "handoff_billing"}],
            }
        )
        == "handoff"
    )


def test_handoff_node_sets_target_and_summary() -> None:
    result = handoff_node(
        {
            "pending_tool_calls": [{"name": "handoff_billing", "arguments": {"reason": "invoice issue"}}],
            "linked_agents": [
                {
                    "transfer_tool_name": "handoff_billing",
                    "target_instance_id": "target-1",
                }
            ],
        }
    )

    assert result == {"handoff_target": "target-1", "handoff_summary": "invoice issue"}


def test_base_graph_compiles_and_runs_respond_path() -> None:
    graph = create_base_graph()
    result = graph.invoke({"pending_tool_calls": [], "linked_agents": []})

    assert result["retrieved_chunks"] == []
    assert result["final_response"] == ""
