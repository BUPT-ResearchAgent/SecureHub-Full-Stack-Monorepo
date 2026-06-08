# Status: real

"""Idempotent seed scripts for the data-layer v2 demo dataset.

``seed_demo.run()`` is the single entry point; it composes the per-domain
seeders in the right order. Each individual seeder is also runnable on its
own (helpful for partial re-seeding during development).
"""

from app.db.seeds.seed_agent_skills import run as seed_agent_skills
from app.db.seeds.seed_agents import run as seed_agents
from app.db.seeds.seed_course_websec import run as seed_course_websec
from app.db.seeds.seed_demo import run as seed_demo
from app.db.seeds.seed_demo_user import run as seed_demo_user

__all__ = [
    "seed_agents",
    "seed_agent_skills",
    "seed_course_websec",
    "seed_demo_user",
    "seed_demo",
]
