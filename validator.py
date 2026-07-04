import json
import logging
from typing import Any, Dict, Tuple
from pydantic import BaseModel, field_validator
from config_manager import config_manager

logger = logging.getLogger("ZeroTrust.Agent.Validator")

class DatabaseReadSchema(BaseModel):
    query: str

    @field_validator('query')
    @classmethod
    def must_be_select(cls, v: str) -> str:
        # Enforce strict SELECT-only queries
        if not v.strip().upper().startswith("SELECT"):
            raise ValueError("Only SELECT queries are allowed.")
        return v

SCHEMA_REGISTRY = {
    "DatabaseReadSchema": DatabaseReadSchema
}

active_tools = {}

def init_validator():
    global active_tools
    allowed_tools = config_manager.config.get("validator", {}).get("allowed_tools", {})
    for tool_name, tool_cfg in allowed_tools.items():
        schema_type = tool_cfg.get("schema_type")
        if schema_type in SCHEMA_REGISTRY:
            active_tools[tool_name] = SCHEMA_REGISTRY[schema_type]
    logger.info(f"Validator initialized with {len(active_tools)} allowed tools.")

def validate_tool_call(tool_name: str, arguments_json: str) -> Tuple[bool, str]:
    """
    Validates LLM-generated tool arguments against predefined Pydantic schemas.
    Returns (is_valid, reason_if_invalid).
    """
    if tool_name not in active_tools:
        logger.warning(f"Tool {tool_name} not found in Allowed Registry.")
        return False, f"Tool {tool_name} not in config registry."

    try:
        args = json.loads(arguments_json)
        schema = active_tools[tool_name]
        schema(**args)
        return True, "Valid"
    except Exception as e:
        logger.warning(f"Tool validation failed for {tool_name}: {str(e)}")
        return False, f"Schema validation error: {str(e)}"
