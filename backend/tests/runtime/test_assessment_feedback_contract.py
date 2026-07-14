from app.agents.career_planner.skills.update_persona import UpdatePersonaOutput
from app.agents.outcome_evaluator.skills.run_assessment import RunAssessmentInput
from app.runtime.workflows.product_workflows import AssessmentUpdateV2Input


def test_update_persona_exposes_the_patch_field_consumed_by_persistence() -> None:
    output = UpdatePersonaOutput.model_validate(
        {"updated_dimensions": {"weak_points": ["kp-blind-sqli"]}}
    )

    assert output.dimensions == {"weak_points": ["kp-blind-sqli"]}
    assert output.updated_dimensions == {"weak_points": ["kp-blind-sqli"]}


def test_assessment_answers_do_not_share_a_mutable_default() -> None:
    first = RunAssessmentInput(user_id="user", query="assessment")
    second = RunAssessmentInput(user_id="user", query="assessment")

    first.answers.append({"quiz_item_id": "quiz-1"})

    assert second.answers == []


def test_assessment_v2_retains_server_owned_mutation_constraints() -> None:
    payload = AssessmentUpdateV2Input.model_validate(
        {
            "user_id": "user",
            "course_id": "course",
            "capability_dimensions": ["web_security"],
            "persona_dimension_keys": ["easy_mistakes"],
            "context": {"kp_id": "kp-sqli", "current_path_node_ids": ["node-1"]},
        }
    ).model_dump()

    assert payload["capability_dimensions"] == ["web_security"]
    assert payload["persona_dimension_keys"] == ["easy_mistakes"]
    assert payload["context"] == {"kp_id": "kp-sqli", "current_path_node_ids": ["node-1"]}
