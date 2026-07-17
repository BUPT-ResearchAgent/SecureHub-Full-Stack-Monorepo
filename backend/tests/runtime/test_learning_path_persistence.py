# Status: real

"""Regression coverage for the durable ``course_plan_v1`` terminal action."""

from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from app.db.models.identity.user import User
from app.db.models.knowledge.course import Course
from app.db.models.knowledge.knowledge_node import KnowledgeNode
from app.db.models.learning.learning_path import LearningPath
from app.db.models.learning.learning_task import LearningTask
from app.runtime.actions import WorkflowActionService
from app.services.learning.student_learning_loop_service import StudentLearningLoopService


async def _seed_existing_path(sqlite_session) -> tuple[User, Course, KnowledgeNode, LearningPath]:
    user = User(id=uuid4(), email="path-action@example.test", display_name="Path Action Learner")
    course = Course(id=uuid4(), code="PATH-ACTION-101", title="Path action test course")
    node = KnowledgeNode(
        id=uuid4(),
        domain="course_websec",
        course_id=course.id,
        name="SQL injection defense",
        metadata_={},
    )
    prior_path = LearningPath(
        id=uuid4(),
        user_id=user.id,
        course_id=course.id,
        title="Prior usable path",
        objective="retain until replacement is valid",
        status="active",
        metadata_={},
    )
    prior_task = LearningTask(
        id=uuid4(),
        path_id=prior_path.id,
        kp_id=node.id,
        title="Prior durable task",
        task_type="course_learning",
        order_index=1,
        status="todo",
        metadata_={},
    )
    sqlite_session.add_all([user, course, node, prior_path, prior_task])
    await sqlite_session.commit()
    return user, course, node, prior_path


@pytest.mark.anyio
async def test_persist_learning_path_materialises_tasks_before_superseding_prior_path(sqlite_session) -> None:
    user, course, node, prior_path = await _seed_existing_path(sqlite_session)

    result = await WorkflowActionService(sqlite_session, storage_service=SimpleNamespace()).persist_learning_path(
        {"user_id": str(user.id), "course_id": str(course.id), "query": "SQL injection learning plan"},
        {
            "generate_path": {
                "output": {
                    "title": "Generated secure-coding path",
                    "nodes": [
                        {
                            "kp_id": str(node.id),
                            "title": "Study parameterized queries",
                            "status": "in_progress",
                            "est_minutes": 30,
                        },
                        {
                            "id": "fixture-sqli-payloads",
                            "label": "Review classic SQLi payload patterns",
                            "task_type": "practice",
                            "estimated_minutes": 45,
                        },
                    ],
                    "edges": [],
                    "milestones": [],
                    "quality_score": 0.84,
                }
            }
        },
        SimpleNamespace(),
    )
    await sqlite_session.commit()

    active_paths = list(
        (
            await sqlite_session.execute(
                select(LearningPath).where(
                    LearningPath.user_id == user.id,
                    LearningPath.course_id == course.id,
                    LearningPath.status == "active",
                )
            )
        ).scalars()
    )
    assert len(active_paths) == 1
    assert str(active_paths[0].id) == result["learning_path_id"]
    assert (await sqlite_session.get(LearningPath, prior_path.id)).status == "superseded"

    tasks = list(
        (
            await sqlite_session.execute(
                select(LearningTask)
                .where(LearningTask.path_id == active_paths[0].id)
                .order_by(LearningTask.order_index)
            )
        ).scalars()
    )
    assert result["task_count"] == len(tasks) == 2
    assert [(task.title, task.kp_id, task.status) for task in tasks] == [
        ("Study parameterized queries", node.id, "in_progress"),
        ("Review classic SQLi payload patterns", None, "todo"),
    ]
    assert tasks[0].metadata_["expected_minutes"] == 30
    assert tasks[1].metadata_["source_node_id"] == "fixture-sqli-payloads"
    assert tasks[1].metadata_["expected_minutes"] == 45


@pytest.mark.anyio
async def test_persist_learning_path_rejects_empty_task_projection_without_retiring_prior_path(sqlite_session) -> None:
    user, course, _node, prior_path = await _seed_existing_path(sqlite_session)

    with pytest.raises(ValueError, match="no task title"):
        await WorkflowActionService(sqlite_session, storage_service=SimpleNamespace()).persist_learning_path(
            {"user_id": str(user.id), "course_id": str(course.id)},
            {"generate_path": {"output": {"nodes": [{"id": "missing-title"}]}}},
            SimpleNamespace(),
        )

    active_paths = list(
        (
            await sqlite_session.execute(
                select(LearningPath).where(
                    LearningPath.user_id == user.id,
                    LearningPath.course_id == course.id,
                    LearningPath.status == "active",
                )
            )
        ).scalars()
    )
    assert [path.id for path in active_paths] == [prior_path.id]
    assert (await sqlite_session.get(LearningPath, prior_path.id)).status == "active"


@pytest.mark.anyio
async def test_three_generated_tasks_receive_only_one_replan_supplement(sqlite_session) -> None:
    """Keep course planning and learner replan cardinalities separately owned."""
    user, course, node, _prior_path = await _seed_existing_path(sqlite_session)

    result = await WorkflowActionService(sqlite_session, storage_service=SimpleNamespace()).persist_learning_path(
        {"user_id": str(user.id), "course_id": str(course.id), "query": "SQL injection learning plan"},
        {
            "generate_path": {
                "output": {
                    "title": "Three-step secure-coding path",
                    "nodes": [
                        {"kp_id": str(node.id), "title": "Study parameterized queries"},
                        {"id": "fixture-sqli-payloads", "title": "Review SQLi payload patterns"},
                        {"id": "fixture-sqli-defense", "title": "Validate query defenses"},
                    ],
                }
            }
        },
        SimpleNamespace(),
    )
    await sqlite_session.commit()

    generated_path = await sqlite_session.get(LearningPath, UUID(result["learning_path_id"]))
    assert generated_path is not None
    generated_tasks = list(
        (
            await sqlite_session.execute(
                select(LearningTask)
                .where(LearningTask.path_id == generated_path.id)
                .order_by(LearningTask.order_index)
            )
        ).scalars()
    )
    assert result["task_count"] == len(generated_tasks) == 3

    proposal = StudentLearningLoopService(sqlite_session)._proposed_tasks(
        [(task, node if task.kp_id == node.id else None) for task in generated_tasks],
        node,
        "SQL injection defense review",
        20,
    )

    assert len(proposal) == 4
    assert sum(item["action"] == "added" for item in proposal) == 1
    assert [item["order_index"] for item in proposal] == [1, 2, 3, 4]
