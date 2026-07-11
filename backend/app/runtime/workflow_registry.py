# Status: real

"""Versioned registry for framework-neutral workflow definitions."""

from __future__ import annotations

from app.runtime.workflow_definition import WorkflowDefinition


class UnknownWorkflow(KeyError):
    pass


class WorkflowRegistry:
    def __init__(self) -> None:
        self._definitions: dict[tuple[str, int], WorkflowDefinition] = {}

    def register(self, definition: WorkflowDefinition) -> WorkflowDefinition:
        if definition.key in self._definitions:
            raise ValueError(f"workflow already registered: {definition.name}@{definition.version}")
        self._definitions[definition.key] = definition
        return definition

    def get(self, name: str, version: int | None = None) -> WorkflowDefinition:
        if version is None:
            versions = [item for (registered_name, _), item in self._definitions.items() if registered_name == name]
            if not versions:
                raise UnknownWorkflow(name)
            return max(versions, key=lambda item: item.version)
        try:
            return self._definitions[(name, version)]
        except KeyError as exc:
            raise UnknownWorkflow(f"{name}@{version}") from exc

    def all(self) -> tuple[WorkflowDefinition, ...]:
        return tuple(sorted(self._definitions.values(), key=lambda item: item.key))


GLOBAL_WORKFLOW_REGISTRY = WorkflowRegistry()


__all__ = ["GLOBAL_WORKFLOW_REGISTRY", "UnknownWorkflow", "WorkflowRegistry"]
