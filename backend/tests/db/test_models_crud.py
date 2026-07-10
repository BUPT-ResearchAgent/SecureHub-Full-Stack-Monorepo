# Status: real

"""数据库模型可导入性和 schema 一致性检查。"""

from __future__ import annotations

import pytest


def test_agent_model_importable():
    from app.db.models.agent import Agent

    assert hasattr(Agent, "name")
    assert hasattr(Agent, "risk_level")


def test_user_profile_model_importable():
    from app.db.models.identity.user_profile import UserProfile

    assert hasattr(UserProfile, "dimensions")
    assert hasattr(UserProfile, "user_id")


def test_chunk_model_importable():
    from app.db.models.knowledge.chunk import Chunk

    assert hasattr(Chunk, "chunk_text")
    assert hasattr(Chunk, "domain")


def test_learning_event_model_importable():
    from app.db.models.learning.learning_event import LearningEvent

    assert hasattr(LearningEvent, "user_id")
    assert hasattr(LearningEvent, "event_type")


def test_generated_resource_model_importable():
    from app.db.models.resource.generated_resource import GeneratedResource

    assert hasattr(GeneratedResource, "resource_type")
