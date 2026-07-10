# Status: partial-real

"""Fixed workflow implementations for the Run API."""

from app.runtime.workflows.course_learning_minimal import (
    WORKFLOW_NAME,
    run_course_learning_minimal,
    workflow_nodes,
)

__all__ = ["WORKFLOW_NAME", "run_course_learning_minimal", "workflow_nodes"]
