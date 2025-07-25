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

# pyright: reportAttributeAccessIssue=false, reportFunctionMemberAccess=false
# because boto3 client doesn't have any type hinting
import boto3
import botocore.session
import inspect
import os
import sys
from botocore.exceptions import ClientError
from mcp.server.fastmcp import FastMCP
from pydantic import Field
from typing import Annotated, Any, Callable, Dict, List


# Defining type alias
BOTO3_CLIENT_GETTER = Callable[[str], Any]
OVERRIDE_FUNC_TYPE = Callable[[FastMCP, BOTO3_CLIENT_GETTER, str], None]
VALIDATOR = Callable[[FastMCP, Any, Dict[str, Any]], tuple[bool, str | None]]


class AWSToolGenerator:
    """Generic AWS Service Tool that can be used for any AWS service."""

    def __init__(
        self,
        service_name: str,
        service_display_name: str,
        mcp: FastMCP,
        tool_configuration: Dict[str, Dict[str, Any]] | None = None,
        skip_param_documentation: bool = False,
    ):
        """Initialize the AWS Service Tool.

        Args:
            service_name: The AWS service name (e.g., 'sns', 'sqs', 'mq')
            service_display_name: Display name for the service (defaults to uppercase of service_name)
            mcp: The MCP server instance
            tool_configuration: Confguration for each tool
            skip_param_documentation: If True, parameter documentation will be skipped

        """
        self.service_name = service_name
        self.service_display_name = service_display_name or service_name.upper()
        self.mcp = mcp
        self.clients: Dict[str, Any] = {}
        self.tool_configuration = tool_configuration or {}
        self.skip_param_documentation = skip_param_documentation
        self.__validate_tool_configuration()

    def generate(self):
        """Augment the MCP server with tools derived from the boto3 client and tool configurations."""
        self.__register_operations()

    def get_mcp(self):
        """Reture the MCP server instance."""
        return self.mcp

    def __register_operations(self):
        for operation in self.__get_operations():
            cfg = self.tool_configuration.get(operation, {})
            if cfg.get('ignore'):
                continue
            if cfg.get('func_override'):
                self.__handle_override(operation, cfg['func_override'])
            else:
                fn = self.__create_operation_function(
                    operation,
                    cfg.get('documentation_override'),
                    cfg.get('validator'),
                )
                if fn:
                    self.mcp.tool(description=fn.__doc__)(fn)

    def __get_client(self, creds: Dict[str, Any], region: str = 'us-east-1') -> Any:
        """Get or create a service client for the specified region."""
        client_key = f'{self.service_name}_{region}'
        if client_key not in self.clients:
            self.clients[client_key] = boto3.Session(
                aws_access_key_id=creds['access_key'],
                aws_secret_access_key=creds['secret_access_key'],
                region_name=region
            ).client(self.service_name)
        return self.clients[client_key]

    def __get_operations(self) -> List[str]:
        """Get all available operations from boto3 for this service."""
        default_client = boto3.client(self.service_name)
        operations = [
            op
            for op in dir(default_client)
            if not op.startswith('_') and callable(getattr(default_client, op))
        ]
        return sorted(operations)

    def __handle_override(
        self,
        operation: str,
        override_fn: OVERRIDE_FUNC_TYPE,
    ):
        def client_getter(region: str, credentials: Dict[str, str]):
            return self.__get_client(region, credentials)
        override_fn(self.mcp, client_getter, operation)

    def __create_operation_function(
        self,
        operation: str,
        doc_override: str | None,
        validator: VALIDATOR | None,
    ) -> Callable[..., Any] | None:
        try:
            params_meta = self.__get_operation_input_parameters(operation)
        except Exception:
            print(f"Skipping {operation}: cannot get model", file=sys.stderr)
            return None

        # Build signature: credentials + each API param + region
        parameters: List[inspect.Parameter] = [
            inspect.Parameter(
                'credentials',
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                annotation=Dict[str, str],
            )
        ]
        type_map = {'string': str, 'boolean': bool, 'integer': int, 'map': dict}
        default_map = {'string': '', 'boolean': False, 'integer': 0, 'map': {}}

        for name, tname, req, doc in params_meta:
            ann = type_map.get(tname, str)
            if req:
                parameters.append(
                    inspect.Parameter(name, inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=ann)
                )
            else:
                parameters.append(
                    inspect.Parameter(
                        name,
                        inspect.Parameter.POSITIONAL_OR_KEYWORD,
                        annotation=Annotated[ann, Field(description=doc)],
                        default=default_map.get(tname),
                    )
                )

        parameters.append(
            inspect.Parameter('region', inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=str)
        )

        async def operation_fn(*args, **kwargs) -> Dict[str, Any]:
            bound = operation_fn.__signature__.bind(*args, **kwargs)
            bound.apply_defaults()
            creds = bound.arguments['credentials']
            region = bound.arguments['region']
            # remove our extras before calling AWS
            call_args = {
                k: v
                for k, v in bound.arguments.items()
                if k not in ('credentials', 'region')
            }
            client = self.__get_client(region, creds)
            if validator:
                ok, msg = validator(self.mcp, client, call_args)
                if not ok:
                    return {'error': msg}
            try:
                resp = getattr(client, operation)(**call_args)
                resp.pop('ResponseMetadata', None)
                return resp
            except ClientError as e:
                err = e.response.get('Error', {})
                return {'error': err.get('Message', str(e)), 'code': err.get('Code')}
            except Exception as e:
                return {'error': str(e)}

        operation_fn.__name__ = operation
        operation_fn.__doc__ = doc_override or f"Execute AWS {self.service_display_name} `{operation}`."
        operation_fn.__signature__ = inspect.Signature(parameters)
        return operation_fn

    def __get_operation_input_parameters(
        self, operation_name: str
    ) -> List[tuple[str, str, bool, str]]:
        """Return a list of input parameter names for a given operation."""
        session = botocore.session.get_session()
        service_model = session.get_service_model(self.service_name)
        op_model = service_model.operation_model(self.__snake_to_camel(operation_name))
        input_shape = op_model.input_shape
        if not input_shape:
            return []
        res = []
        for param_name in input_shape.members.keys():
            param_shape = input_shape.members[param_name]
            # Skip documentation if flag is set
            if self.skip_param_documentation:
                param_documentation = ''
            else:
                param_documentation = getattr(param_shape, 'documentation', '')
            is_required = param_name in input_shape.required_members
            res.append((param_name, param_shape.type_name, is_required, param_documentation))
        return res

    def __snake_to_camel(self, snake_str: str) -> str:
        return ''.join(word.capitalize() for word in snake_str.split('_'))

    # TODO: Rewrite this validation logic. It is messy
    def __validate_tool_configuration(self):
        for operation, configuration in self.tool_configuration.items():
            if (
                configuration.get('ignore') is True
                and configuration.get('func_override') is not None
            ):
                raise ValueError(
                    f'For tool {operation}, cannot specify both ignore=True and a function override'
                )
            if configuration.get('ignore') is True and (
                configuration.get('documentation_override') is not None
                and configuration.get('documentation_override') != ''
            ):
                raise ValueError(
                    f'For tool {operation}, cannot specify both ignore=True and a documentation override'
                )
            if (
                configuration.get('func_override') is not None
                and configuration.get('documentation_override') is not None
                and configuration.get('documentation_override') != ''
            ):
                raise ValueError(
                    f'For tool {operation}, cannot specify both func_override and a documentation override'
                )
            if (
                configuration.get('func_override') is None
                and configuration.get('documentation_override') is None
                and configuration.get('ignore') is None
                and configuration.get('validator') is None
            ):
                raise ValueError(f'For tool {operation}, cannot specify empty override')
