# -*- coding: utf-8 -*-
"""User-Agent mapping management module.

Manages the relationship between users and their agents, including:
- User-Agent mapping configuration
- Creating default agent for new users
- Verifying user access to agents
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..config.config import (
    AgentProfileRef,
    AgentsConfig,
    Config,
)
from ..config.utils import load_config, save_config
from ..constant import SECRET_DIR, WORKING_DIR
from ..agents.utils.setup_utils import copy_md_files
from ..agents.skills_manager import get_workspace_skills_dir, get_builtin_skills_dir

logger = logging.getLogger(__name__)

USER_AGENTS_FILE = SECRET_DIR / "user_agents.json"


def _chmod_best_effort(path, mode: int) -> None:
    try:
        os.chmod(path, mode)
    except OSError:
        pass


def _prepare_secret_parent(path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _chmod_best_effort(path.parent, 0o700)


def _load_user_agents_data() -> dict:
    """Load user-agents mapping data."""
    if USER_AGENTS_FILE.is_file():
        try:
            with open(USER_AGENTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            logger.error("Failed to load user agents file: %s", exc)
            return {"_load_error": True}
    return {"version": 1, "users": {}}


def _save_user_agents_data(data: dict) -> None:
    """Save user-agents mapping data."""
    _prepare_secret_parent(USER_AGENTS_FILE)
    with open(USER_AGENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    _chmod_best_effort(USER_AGENTS_FILE, 0o600)


def get_user_workspace_dir(user_id: str) -> Path:
    """Get the workspace directory for a user.
    
    Args:
        user_id: The user identifier (accountId for yukuai users)
        
    Returns:
        Path to user's workspace directory
    """
    return WORKING_DIR / "workspaces" / f"user_{user_id}"


def get_user_agent_dir(user_id: str, agent_id: str) -> Path:
    """Get the workspace directory for a specific agent owned by a user.
    
    Args:
        user_id: The user identifier
        agent_id: The agent identifier
        
    Returns:
        Path to the agent's workspace directory
    """
    return get_user_workspace_dir(user_id) / agent_id


def get_user_agents(user_id: str) -> List[str]:
    """Get the list of agent IDs for a user.
    
    Args:
        user_id: The user identifier
        
    Returns:
        List of agent IDs the user has access to
    """
    data = _load_user_agents_data()
    users = data.get("users", {})
    user_config = users.get(user_id, {})
    return user_config.get("agents", [])


def get_user_default_agent(user_id: str) -> Optional[str]:
    """Get the default agent ID for a user.
    
    Args:
        user_id: The user identifier
        
    Returns:
        Default agent ID or None if not set
    """
    data = _load_user_agents_data()
    users = data.get("users", {})
    user_config = users.get(user_id, {})
    return user_config.get("default_agent")


def can_user_access_agent(user_id: str, agent_id: str) -> bool:
    """Check if a user has access to a specific agent.
    
    Args:
        user_id: The user identifier
        agent_id: The agent identifier
        
    Returns:
        True if user has access to the agent
    """
    user_agents = get_user_agents(user_id)
    return agent_id in user_agents


def _initialize_user_agent_workspace(workspace_dir: Path, language: str = "zh") -> None:
    """Initialize user agent workspace with standard template files.
    
    This function replicates the logic from routers/agents.py _initialize_agent_workspace
    to ensure consistent workspace setup without modifying original code.
    
    Args:
        workspace_dir: The workspace directory to initialize
        language: Language code for template files (default: zh)
    """
    workspace_dir.mkdir(parents=True, exist_ok=True)
    
    (workspace_dir / "sessions").mkdir(exist_ok=True)
    (workspace_dir / "memory").mkdir(exist_ok=True)
    get_workspace_skills_dir(workspace_dir).mkdir(exist_ok=True)
    
    copy_md_files(language=language, skip_existing=True, workspace_dir=workspace_dir)
    
    _ensure_heartbeat_file(workspace_dir, language)
    
    _copy_builtin_skills_to_workspace(workspace_dir)
    
    jobs_file = workspace_dir / "jobs.json"
    if not jobs_file.exists():
        with open(jobs_file, "w", encoding="utf-8") as file:
            json.dump(
                {"version": 1, "jobs": []},
                file,
                ensure_ascii=False,
                indent=2,
            )
    
    chats_file = workspace_dir / "chats.json"
    if not chats_file.exists():
        with open(chats_file, "w", encoding="utf-8") as file:
            json.dump(
                {"version": 1, "chats": []},
                file,
                ensure_ascii=False,
                indent=2,
            )


def _ensure_heartbeat_file(workspace_dir: Path, language: str) -> None:
    """Create the default HEARTBEAT.md if it is missing."""
    heartbeat_file = workspace_dir / "HEARTBEAT.md"
    if heartbeat_file.exists():
        return
    
    default_heartbeat_mds = {
        "zh": """# Heartbeat checklist
- 扫描收件箱紧急邮件
- 查看未来 2h 的日历
- 检查待办是否卡住
- 若安静超过 8h，轻量 check-in
""",
        "en": """# Heartbeat checklist
- Scan inbox for urgent email
- Check calendar for next 2h
- Check tasks for blockers
- Light check-in if quiet for 8h
""",
        "ru": """# Heartbeat checklist
- Проверить входящие на срочные письма
- Просмотреть календарь на ближайшие 2 часа
- Проверить задачи на наличие блокировок
- Лёгкая проверка при отсутствии активности более 8 часов
""",
    }
    
    content = default_heartbeat_mds.get(language, default_heartbeat_mds.get("en", ""))
    if content:
        with open(heartbeat_file, "w", encoding="utf-8") as file:
            file.write(content)


def _copy_builtin_skills_to_workspace(workspace_dir: Path) -> None:
    """Copy builtin skills into workspace when missing."""
    builtin_skills_dir = get_builtin_skills_dir()
    if not builtin_skills_dir or not builtin_skills_dir.exists():
        return
    
    target_skills_dir = get_workspace_skills_dir(workspace_dir)
    target_skills_dir.mkdir(parents=True, exist_ok=True)
    
    for skill_dir in builtin_skills_dir.iterdir():
        if not skill_dir.is_dir() or not (skill_dir / "SKILL.md").exists():
            continue
        target_skill_dir = target_skills_dir / skill_dir.name
        if target_skill_dir.exists():
            continue
        try:
            shutil.copytree(skill_dir, target_skill_dir)
            logger.debug("Copied builtin skill: %s", skill_dir.name)
        except Exception as e:
            logger.warning("Failed to copy skill %s: %s", skill_dir.name, e)


def create_default_agent_for_user(user_id: str) -> Optional[str]:
    """Create a default agent for a new user.
    
    Creates the user's workspace directory and a default agent.
    Also registers the user in user_agents.json if not already registered.
    
    Args:
        user_id: The user identifier
        
    Returns:
        The created default agent ID, or None on failure
    """
    default_agent_id = f"user_{user_id}_default"
    agent_workspace = get_user_agent_dir(user_id, default_agent_id)
    
    logger.info("Creating default agent for user %s at %s", user_id, agent_workspace)
    
    config = load_config()
    language = config.agents.language or "zh"
    
    _initialize_user_agent_workspace(agent_workspace, language)
    
    data = _load_user_agents_data()
    if "users" not in data:
        data["users"] = {}
    
    if user_id not in data["users"]:
        data["users"][user_id] = {
            "agents": [default_agent_id],
            "default_agent": default_agent_id,
            "created_at": int(time.time()),
        }
        _save_user_agents_data(data)
    
    _register_agent_in_config(user_id, default_agent_id, str(agent_workspace))
    
    logger.info("Default agent '%s' created for user %s", default_agent_id, user_id)
    return default_agent_id


def _register_agent_in_config(user_id: str, agent_id: str, workspace_dir: str) -> None:
    """Register an agent in the global config.
    
    Args:
        user_id: The user identifier
        agent_id: The agent identifier
        workspace_dir: The agent's workspace directory path
    """
    config = load_config()
    
    if "agents" not in config.model_dump():
        config.agents = AgentsConfig()
    
    if agent_id in config.agents.profiles:
        logger.debug("Agent %s already exists in config", agent_id)
        return
    
    config.agents.profiles[agent_id] = AgentProfileRef(
        id=agent_id,
        workspace_dir=workspace_dir,
        enabled=True,
    )
    
    if agent_id not in config.agents.agent_order:
        config.agents.agent_order.append(agent_id)
    
    save_config(config)
    logger.info("Registered agent %s for user %s in config", agent_id, user_id)


def create_agent_for_user(user_id: str, agent_id: str, agent_name: str) -> Optional[str]:
    """Create a new agent for a user.
    
    Args:
        user_id: The user identifier
        agent_id: The new agent ID
        agent_name: The new agent name
        
    Returns:
        The created agent ID, or None on failure
    """
    agent_workspace = get_user_agent_dir(user_id, agent_id)
    
    logger.info("Creating agent '%s' for user %s at %s", agent_id, user_id, agent_workspace)
    
    config = load_config()
    language = config.agents.language or "zh"
    
    _initialize_user_agent_workspace(agent_workspace, language)
    
    data = _load_user_agents_data()
    if "users" not in data:
        data["users"] = {}
    
    if user_id not in data["users"]:
        data["users"][user_id] = {
            "agents": [],
            "default_agent": None,
            "created_at": int(time.time()),
        }
    
    user_config = data["users"][user_id]
    if agent_id not in user_config.get("agents", []):
        user_config.setdefault("agents", []).append(agent_id)
        if not user_config.get("default_agent"):
            user_config["default_agent"] = agent_id
        _save_user_agents_data(data)
    
    _register_agent_in_config(user_id, agent_id, str(agent_workspace))
    
    logger.info("Agent '%s' created for user %s", agent_id, user_id)
    return agent_id


def ensure_user_has_default_agent(user_id: str) -> Optional[str]:
    """Ensure a user has a default agent, create if not exists.
    
    Args:
        user_id: The user identifier
        
    Returns:
        The default agent ID
    """
    existing_agents = get_user_agents(user_id)
    if existing_agents:
        default_agent = get_user_default_agent(user_id)
        return default_agent or existing_agents[0]
    
    return create_default_agent_for_user(user_id)


def get_user_info(user_id: str) -> Optional[Dict[str, Any]]:
    """Get user configuration info.
    
    Args:
        user_id: The user identifier
        
    Returns:
        User configuration dict or None if not found
    """
    data = _load_user_agents_data()
    users = data.get("users", {})
    return users.get(user_id)


def get_all_users() -> Dict[str, Dict[str, Any]]:
    """Get all users and their configurations.
    
    Returns:
        Dict mapping user_id to user configuration
    """
    data = _load_user_agents_data()
    return data.get("users", {})