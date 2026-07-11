# Status: partial-real

"""Versioned, framework-neutral WorkflowDefinition modules."""

from app.runtime.workflows.course_learning_full_v1 import COURSE_LEARNING_FULL_V1
from app.runtime.workflows.product_workflows import PRODUCT_WORKFLOWS
from app.runtime.workflows.resource_generate_v1 import RESOURCE_GENERATE_V1

__all__ = ["COURSE_LEARNING_FULL_V1", "PRODUCT_WORKFLOWS", "RESOURCE_GENERATE_V1"]
