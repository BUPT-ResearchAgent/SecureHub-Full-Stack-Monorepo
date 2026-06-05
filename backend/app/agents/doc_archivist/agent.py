# Status: [planned]

from app.agents.base import AgentCapability, BaseAgent
from app.agents.doc_archivist.skills import (
    generate_course_doc,
    generate_course_ppt,
    generate_mindmap,
    generate_video_storyboard,
)


class DocArchivistAgent(BaseAgent):
    name = "doc_archivist"
    role_description = "Generate course docs, slides, mindmaps, storyboards, and archive artifacts."
    capability_vector = AgentCapability(doc=1.0, topic=0.4, task=0.3)
    tools = ["rag.retrieve", "llm.xfyun"]
    risk_level = "low"
    skills = {
        "GenerateCourseDoc": generate_course_doc.GenerateCourseDoc,
        "GenerateCoursePPT": generate_course_ppt.GenerateCoursePPT,
        "GenerateMindmap": generate_mindmap.GenerateMindmap,
        "GenerateVideoStoryboard": generate_video_storyboard.GenerateVideoStoryboard,
    }
