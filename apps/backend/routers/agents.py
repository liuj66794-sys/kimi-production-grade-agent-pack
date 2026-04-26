"""
Agents Router - Agent listing, skills, and permissions endpoints.

Provides read-only access to agent configurations and available skills.
Agent enablement/disablement is controlled via scripts/*.py.
"""

import os
import glob
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import SKILLS_DIR, BASE_DIR

router = APIRouter(prefix="/api", tags=["agents"])


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

class AgentInfo(BaseModel):
    """Agent configuration and capabilities."""
    name: str
    level: str  # l1 | l2 | l3
    enabled: bool
    tools: List[str]
    description: str


class SkillInfo(BaseModel):
    """Skill/Flow metadata."""
    name: str
    type: str  # skill | flow
    path: str
    description: Optional[str]


class AgentsResponse(BaseModel):
    """List of all configured agents."""
    agents: List[AgentInfo]
    total: int
    enabled_count: int


class SkillsResponse(BaseModel):
    """List of available skills and flows."""
    skills: List[SkillInfo]
    total: int


# ---------------------------------------------------------------------------
# Agent Registry (hardcoded for v3.0)
# ---------------------------------------------------------------------------
# In v3.1+, this should be loaded from a configuration file
# and managed via scripts/*.py, not directly by the UI.

_AGENT_REGISTRY = [
    {
        "name": "researcher",
        "level": "l1",
        "enabled": True,
        "tools": ["SearchWeb", "FetchURL", "ReadFile", "Glob"],
        "description": "Web research and data gathering agent",
    },
    {
        "name": "analyst",
        "level": "l1",
        "enabled": True,
        "tools": ["ReadFile", "SearchWeb", "Grep", "Glob"],
        "description": "Data analysis and insight extraction agent",
    },
    {
        "name": "coder",
        "level": "l1",
        "enabled": True,
        "tools": ["ReadFile", "WriteFile", "StrReplaceFile", "Shell", "Glob", "Grep"],
        "description": "Code generation and implementation agent",
    },
    {
        "name": "writer",
        "level": "l1",
        "enabled": True,
        "tools": ["ReadFile", "WriteFile", "StrReplaceFile", "Glob"],
        "description": "Report writing and documentation agent",
    },
    {
        "name": "qa-reviewer",
        "level": "l1",
        "enabled": True,
        "tools": ["ReadFile", "Grep", "Glob"],
        "description": "Quality assurance and review agent",
    },
    {
        "name": "slide-maker",
        "level": "l2",
        "enabled": False,
        "tools": ["ReadFile", "WriteFile", "Glob"],
        "description": "Presentation/slide generation agent",
    },
    {
        "name": "spreadsheet",
        "level": "l2",
        "enabled": False,
        "tools": ["ReadFile", "WriteFile", "Shell"],
        "description": "Spreadsheet generation and data processing agent",
    },
    {
        "name": "multimodal",
        "level": "l3",
        "enabled": False,
        "tools": ["ReadMediaFile", "ReadFile", "Glob"],
        "description": "Multimedia content processing agent",
    },
    {
        "name": "memory-curator",
        "level": "l2",
        "enabled": False,
        "tools": ["ReadFile", "WriteFile", "Glob", "Grep"],
        "description": "Memory management and curation agent",
    },
]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/agents", response_model=AgentsResponse)
def get_agents() -> Dict[str, Any]:
    """
    Get all configured agents with their capabilities.

    Returns:
        List of agents with name, level, enabled status, and available tools.
    """
    agents = [AgentInfo(**a).model_dump() for a in _AGENT_REGISTRY]
    enabled_count = sum(1 for a in agents if a["enabled"])

    return {
        "agents": agents,
        "total": len(agents),
        "enabled_count": enabled_count,
    }


@router.get("/agents/{agent_name}")
def get_agent_detail(agent_name: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific agent.

    Args:
        agent_name: Name of the agent

    Returns:
        Agent details including tool descriptions.
    """
    for agent in _AGENT_REGISTRY:
        if agent["name"] == agent_name:
            return {
                **agent,
                "tool_details": _get_tool_details(agent["tools"]),
            }

    raise HTTPException(status_code=404, detail=f"Agent not found: {agent_name}")


@router.get("/skills", response_model=SkillsResponse)
def get_skills() -> Dict[str, Any]:
    """
    Get all available skills and flows.

    Scans the skills/ directory for SKILL.md files and classifies
    each skill as 'skill' or 'flow' based on its metadata.

    Returns:
        List of skills with type and path information.
    """
    skills = []

    if not os.path.exists(SKILLS_DIR):
        return {"skills": [], "total": 0}

    skill_dirs = glob.glob(os.path.join(SKILLS_DIR, "*"))

    for d in sorted(skill_dirs):
        if not os.path.isdir(d):
            continue

        skill_name = os.path.basename(d)
        skill_md = os.path.join(d, "SKILL.md")

        # Determine skill type from SKILL.md metadata
        skill_type = "skill"
        description = None

        if os.path.exists(skill_md):
            try:
                with open(skill_md, "r", encoding="utf-8") as f:
                    content = f.read()
                    if "type: flow" in content.lower() or "flow" in content.lower()[:200]:
                        skill_type = "flow"
                    # Extract first line as description
                    lines = [l.strip() for l in content.split("\n") if l.strip()]
                    if lines:
                        description = lines[0].replace("# ", "").strip()
            except (IOError, UnicodeDecodeError):
                pass

        skills.append({
            "name": skill_name,
            "type": skill_type,
            "path": d,
            "description": description,
        })

    return {
        "skills": skills,
        "total": len(skills),
    }


@router.get("/skills/{skill_name}")
def get_skill_detail(skill_name: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific skill.

    Args:
        skill_name: Name of the skill directory

    Returns:
        Skill metadata and SKILL.md content.
    """
    skill_path = os.path.join(SKILLS_DIR, skill_name)
    skill_md = os.path.join(skill_path, "SKILL.md")

    if not os.path.exists(skill_path):
        raise HTTPException(status_code=404, detail=f"Skill not found: {skill_name}")

    skill_type = "skill"
    content = None

    if os.path.exists(skill_md):
        try:
            with open(skill_md, "r", encoding="utf-8") as f:
                content = f.read()
                if "type: flow" in content.lower():
                    skill_type = "flow"
        except (IOError, UnicodeDecodeError):
            content = "[Failed to read SKILL.md]"

    # List skill files
    files = []
    if os.path.exists(skill_path):
        for item in os.listdir(skill_path):
            item_path = os.path.join(skill_path, item)
            files.append({
                "name": item,
                "type": "dir" if os.path.isdir(item_path) else "file",
            })

    return {
        "name": skill_name,
        "type": skill_type,
        "path": skill_path,
        "content": content,
        "files": files,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TOOL_DESCRIPTIONS = {
    "SearchWeb": "Search the web for information",
    "FetchURL": "Fetch content from a URL",
    "ReadFile": "Read file contents",
    "WriteFile": "Write content to a file",
    "StrReplaceFile": "Replace string in a file",
    "Shell": "Execute shell commands",
    "Glob": "Find files matching a pattern",
    "Grep": "Search text within files",
    "ReadMediaFile": "Read multimedia files (images, audio, video)",
}


def _get_tool_details(tools: List[str]) -> List[Dict[str, str]]:
    """Get human-readable descriptions for tools."""
    return [
        {
            "name": tool,
            "description": _TOOL_DESCRIPTIONS.get(tool, "No description available"),
        }
        for tool in tools
    ]
