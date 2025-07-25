# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
ECS troubleshooting tool that aggregates all troubleshooting functionality.

This module provides a single entry point for all ECS troubleshooting operations
that were previously available as separate tools.
"""

import inspect
import logging
from typing import Any, Dict, Literal, Optional, Union

from awslabs.ecs_mcp_server.api.troubleshooting_tools.detect_image_pull_failures import (
    detect_image_pull_failures,
)
from awslabs.ecs_mcp_server.api.troubleshooting_tools.fetch_cloudformation_status import (
    fetch_cloudformation_status,
)
from awslabs.ecs_mcp_server.api.troubleshooting_tools.fetch_network_configuration import (
    fetch_network_configuration,
)
from awslabs.ecs_mcp_server.api.troubleshooting_tools.fetch_service_events import (
    fetch_service_events,
)
from awslabs.ecs_mcp_server.api.troubleshooting_tools.fetch_task_failures import (
    fetch_task_failures,
)
from awslabs.ecs_mcp_server.api.troubleshooting_tools.fetch_task_logs import (
    fetch_task_logs,
)
from awslabs.ecs_mcp_server.api.troubleshooting_tools.get_ecs_troubleshooting_guidance import (
    get_ecs_troubleshooting_guidance,
)
from awslabs.ecs_mcp_server.utils import schemas

logger = logging.getLogger(__name__)

# Type definitions
TroubleshootingAction = Literal[
    "get_ecs_troubleshooting_guidance",
    "fetch_cloudformation_status",
    "fetch_service_events",
    "fetch_task_failures",
    "fetch_task_logs",
    "detect_image_pull_failures",
    "fetch_network_configuration",
]

# Combined actions configuration with inline parameter transformers and documentation
ACTIONS = {
    "get_ecs_troubleshooting_guidance": {
        "func": get_ecs_troubleshooting_guidance,
        "required_params": ["creds", "app_name"],
        "optional_params": ["symptoms_description"],
        "transformer": lambda creds, app_name, params: {
            "creds": creds,
            "app_name": app_name,
            "symptoms_description": params.get("symptoms_description"),
        },
        "description": "Initial assessment and data collection",
        "param_descriptions": {
            "creds": "AWS credentials dict or model",
            "app_name": "The name of the application/stack to troubleshoot",
            "symptoms_description": "Description of symptoms experienced by the user",
        },
        "example": (
            'action="get_ecs_troubleshooting_guidance", '
            'creds={"access_key":"<key>","secret_access_key":"<secret>"}, '
            'parameters={"app_name":"my-app","symptoms_description":"ALB 503"}'
        ),
    },
    "fetch_cloudformation_status": {
        "func": fetch_cloudformation_status,
        "required_params": ["creds", "stack_id"],
        "optional_params": [],
        "transformer": lambda creds, _, params: {
            "creds": creds,
            "stack_id": params["stack_id"],
        },
        "description": "Infrastructure-level diagnostics for CloudFormation stacks",
        "param_descriptions": {
            "creds": "AWS credentials dict or model",
            "stack_id": "The CloudFormation stack identifier to analyze",
        },
        "example": (
            'action="fetch_cloudformation_status", '
            'creds={"access_key":"<key>","secret_access_key":"<secret>"}, '
            'parameters={"stack_id":"my-stack"}'
        ),
    },
    "fetch_service_events": {
        "func": fetch_service_events,
        "required_params": ["creds", "app_name", "cluster_name", "service_name"],
        "optional_params": ["time_window", "start_time", "end_time"],
        "transformer": lambda creds, app_name, params: {
            "creds": creds,
            "app_name": app_name,
            "cluster_name": params["cluster_name"],
            "service_name": params["service_name"],
            "time_window": params.get("time_window", 3600),
            "start_time": params.get("start_time"),
            "end_time": params.get("end_time"),
        },
        "description": "Service-level diagnostics for ECS services",
        "param_descriptions": {
            "creds": "AWS credentials dict or model",
            "app_name": "The name of the application to analyze",
            "cluster_name": "The name of the ECS cluster",
            "service_name": "The name of the ECS service to analyze",
            "time_window": "Time window in seconds to look back for events",
            "start_time": "Explicit start time for analysis (UTC)",
            "end_time": "Explicit end time for analysis (UTC)",
        },
        "example": (
            'action="fetch_service_events", '
            'creds={"access_key":"<key>","secret_access_key":"<secret>"}, '
            'parameters={"app_name":"my-app","cluster_name":"c","service_name":"s","time_window":7200}'
        ),
    },
    "fetch_task_failures": {
        "func": fetch_task_failures,
        "required_params": ["creds", "app_name", "cluster_name"],
        "optional_params": ["time_window", "start_time", "end_time"],
        "transformer": lambda creds, app_name, params: {
            "creds": creds,
            "app_name": app_name,
            "cluster_name": params["cluster_name"],
            "time_window": params.get("time_window", 3600),
            "start_time": params.get("start_time"),
            "end_time": params.get("end_time"),
        },
        "description": "Task-level diagnostics for ECS task failures",
        "param_descriptions": {
            "creds": "AWS credentials dict or model",
            "app_name": "The name of the application to analyze",
            "cluster_name": "The name of the ECS cluster",
            "time_window": "Time window in seconds to look back for failures", 
            "start_time": "Explicit start time for analysis (UTC)",
            "end_time": "Explicit end time for analysis (UTC)",
        },
        "example": (
            'action="fetch_task_failures", '
            'creds={"access_key":"<key>","secret_access_key":"<secret>"}, '
            'parameters={"app_name":"my-app","cluster_name":"c","time_window":3600}'
        ),
    },
    "fetch_task_logs": {
        "func": fetch_task_logs,
        "required_params": ["creds", "app_name", "cluster_name"],
        "optional_params": ["task_id", "time_window", "filter_pattern", "start_time", "end_time"],
        "transformer": lambda creds, app_name, params: {
            "creds": creds,
            "app_name": app_name,
            "cluster_name": params["cluster_name"],
            "task_id": params.get("task_id"),
            "time_window": params.get("time_window", 3600),
            "filter_pattern": params.get("filter_pattern"),
            "start_time": params.get("start_time"),
            "end_time": params.get("end_time"),
        },
        "description": "Application-level diagnostics through CloudWatch logs",
        "param_descriptions": {
            "creds": "AWS credentials dict or model",
            "app_name": "The name of the application to analyze",
            "cluster_name": "The name of the ECS cluster",
            "task_id": "Specific task ID to retrieve logs for",
            "time_window": "Time window in seconds to look back for logs",
            "filter_pattern": "CloudWatch logs filter pattern",
            "start_time": "Explicit start time for analysis (UTC)",
            "end_time": "Explicit end time for analysis (UTC)",
        },
        "example": (
            'action="fetch_task_logs", '
            'creds={"access_key":"<key>","secret_access_key":"<secret>"}, '
            'parameters={"app_name":"my-app","cluster_name":"c","filter_pattern":"ERROR","time_window":1800}'
        ),
    },
    "detect_image_pull_failures": {
        "func": detect_image_pull_failures,
        "required_params": ["creds", "app_name"],
        "optional_params": [],
        "transformer": lambda creds, app_name, params: {
            "creds": creds,
            "app_name": app_name,
        },
        "description": "Specialized tool for detecting container image pull failures",
        "param_descriptions": {
            "creds": "AWS credentials dict or model",
            "app_name": "Application name to check for image pull failures",
        },
        "example": (
            'action="detect_image_pull_failures", '
            'creds={"access_key":"<key>","secret_access_key":"<secret>"}, '
            'parameters={"app_name":"my-app"}'
        ),
    },
    "fetch_network_configuration": {
        "func": fetch_network_configuration,
        "required_params": ["creds", "app_name"],
        "optional_params": ["vpc_id", "cluster_name"],
        "transformer": lambda creds, app_name, params: {
            "creds": creds,
            "app_name": app_name,
            "vpc_id": params.get("vpc_id"),
            "cluster_name": params.get("cluster_name"),
        },
        "description": "Network-level diagnostics for ECS deployments",
        "param_descriptions": {
            "creds": "AWS credentials dict or model",
            "app_name": "The name of the application to analyze",
            "vpc_id": "Specific VPC ID to analyze",
            "cluster_name": "Specific ECS cluster name",
        },
        "example": (
            'action="fetch_network_configuration", '
            'creds={"access_key":"<key>","secret_access_key":"<secret>"}, '
            'parameters={"app_name":"my-app","vpc_id":"vpc-123","cluster_name":"c"}'
        ),
    },
}


def generate_troubleshooting_docs():
    """Generate documentation for the troubleshooting tools based on the ACTIONS dictionary."""

    # Generate the main body of the documentation
    actions_docs = []
    quick_usage_examples = []

    for action_name, action_data in ACTIONS.items():
        # Build the action documentation
        action_doc = f"### {len(actions_docs) + 1}. {action_name}\n"
        action_doc += f"{action_data['description']}\n"

        # Required parameters
        action_doc += "- Required: " + ", ".join(action_data["required_params"]) + "\n"

        # Optional parameters if any
        if action_data.get("optional_params"):
            optional_params_with_desc = []
            for param in action_data.get("optional_params", []):
                desc = action_data["param_descriptions"].get(param, "")
                optional_params_with_desc.append(f"{param} ({desc})")
            if optional_params_with_desc:
                action_doc += "- Optional: " + ", ".join(optional_params_with_desc) + "\n"

        # Example usage
        action_doc += f"- Example: {action_data['example']}\n"

        actions_docs.append(action_doc)

        # Build a quick usage example
        example = f"# {action_data['description']}\n"
        example += f'action: "{action_name}"\n'

        # Extract parameters from the example string
        import re

        params_match = re.search(r"parameters=\{(.*?)\}", action_data["example"])
        if params_match:
            params_str = params_match.group(1)
            example += f"parameters: {{{params_str}}}\n"
        else:
            example += "parameters: {}\n"

        quick_usage_examples.append(example)

    # Combine all documentation sections
    doc_header = """
ECS troubleshooting tool with multiple diagnostic actions.

This tool provides access to all ECS troubleshooting operations through a single
interface. Use the 'action' parameter to specify which troubleshooting operation
to perform.

## Available Actions and Parameters:

"""

    doc_examples = """
## Quick Usage Examples:

```
"""

    doc_footer = """```

Parameters:
    app_name: Application/stack name (required for most actions)
    action: The troubleshooting action to perform (see available actions above)
    parameters: Action-specific parameters (see parameter specifications above)

Returns:
    Results from the selected troubleshooting action
"""

    # Combine all the documentation parts
    full_doc = (
        doc_header
        + "\n".join(actions_docs)
        + doc_examples
        + "\n".join(quick_usage_examples)
        + doc_footer
    )

    return full_doc


def _validate_action(action: str) -> None:
    """Validate that the action is supported."""
    if action not in ACTIONS:
        valid_actions = ", ".join(ACTIONS.keys())
        raise ValueError(f"Invalid action '{action}'. Valid actions: {valid_actions}")



def _validate_parameters(
    creds: Dict[str, Any],
    action: str,
    app_name: Optional[str],
    parameters: Dict[str, Any],
) -> None:
    """Validate required parameters (including AWS creds) for the given action."""
    required = ACTIONS[action]["required_params"]

    # Ensure credential keys exist if required
    if "access_key" in required and not creds.get("access_key"):
        raise ValueError(f"access_key is required for action '{action}'")
    if "secret_access_key" in required and not creds.get("secret_access_key"):
        raise ValueError(f"secret_access_key is required for action '{action}'")

    # Validate app_name
    if "app_name" in required and not app_name:
        raise ValueError(f"app_name is required for action '{action}'")

    # Validate other required parameters
    for param in required:
        if param in ("access_key", "secret_access_key", "app_name"):
            continue
        if param not in parameters:
            raise ValueError(f"Missing required parameter '{param}' for action '{action}'")


# Pre-generate the documentation once to avoid regenerating it on each call
TROUBLESHOOTING_DOCS = generate_troubleshooting_docs()


async def ecs_troubleshooting_tool(
    creds: Union[schemas.AwsCredentials, Dict[str, Any]],
    app_name: Optional[str] = None,
    action: TroubleshootingAction = "get_ecs_troubleshooting_guidance",
    parameters: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    ECS troubleshooting tool.

    Args:
        creds: AWS credentials (AwsCredentials model or dict with access_key & secret_access_key)
        app_name: Application/stack name (required for most actions)
        action: The troubleshooting action to perform
        parameters: Action-specific parameters

    Returns:
        Results from the selected troubleshooting action
    """
    try:
        if parameters is None:
            parameters = {}

        # Validate action
        _validate_action(action)

        # Ensure raw creds dict
        raw_creds = creds.model_dump() if isinstance(creds, schemas.AwsCredentials) else creds

        # Check permissions for sensitive actions
        sensitive_data_actions = [
            "fetch_task_logs",
            "fetch_service_events",
            "fetch_task_failures",
            "fetch_network_configuration",
        ]
        if action in sensitive_data_actions:
            from awslabs.ecs_mcp_server.utils.config import get_config

            config = get_config()
            if not config.get("allow-sensitive-data", False):
                return {"status": "error", "error": f"Action {action} not allowed"}

        # Validate parameters including creds
        _validate_parameters(raw_creds, action, app_name, parameters)

        # Call underlying function, always passing creds plus any args
        func = ACTIONS[action]["func"]
        call_args: Dict[str, Any] = {"creds": raw_creds}
        if app_name is not None:
            call_args["app_name"] = app_name
        call_args.update(parameters)

        result = func(**call_args)
        if inspect.iscoroutine(result):
            result = await result
        return result

    except ValueError as e:
        logger.error(f"Parameter validation error: {str(e)}")
        return {"status": "error", "error": str(e)}
    except Exception as e:
        logger.exception(f"Error in ecs_troubleshooting_tool: {str(e)}")
        return {"status": "error", "error": f"Internal error: {str(e)}"}
