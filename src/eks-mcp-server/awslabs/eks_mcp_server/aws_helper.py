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

"""AWS helper for the EKS MCP Server."""

import boto3
from awslabs.eks_mcp_server import __version__
from botocore.config import Config
from loguru import logger
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class AWSConfig(BaseModel):
    """AWS credentials and region/profile configuration."""
    aws_access_key_id: Optional[str] = Field(..., description="AWS access key ID")
    aws_secret_access_key: Optional[str] = Field(..., description="AWS secret access key")
    region_name: str = Field("us-east-1", description="AWS region name, e.g. 'us-east-1'")

class AwsHelper:
    """Helper for creating AWS service clients using AWSConfig."""

    _client_cache: Dict[str, Any] = {}

    @staticmethod
    def _cache_key(service_name: str, config: AWSConfig) -> str:
        # include region in cache key
        return f"{service_name}:{config.region_name}"

    @classmethod
    def create_boto3_client(
        cls,
        service_name: str,
        aws_config: AWSConfig,
    ) -> Any:
        """
        Create or retrieve a cached boto3 client for the given service, using the provided AWSConfig.

        Args:
            service_name: AWS service name (e.g. 'ec2', 's3', 'eks')
            aws_config: AWSConfig object with credentials and region

        Returns:
            boto3 client
        """
        if aws_config is None:
            raise ValueError("AWSConfig must be provided to create_client")

        key = cls._cache_key(service_name, aws_config)
        if key in cls._client_cache:
            logger.info(f"Using cached boto3 client for {service_name} (key={key})")
            return cls._client_cache[key]

        # Build session parameters
        session_kwargs: Dict[str, Any] = {
            'aws_access_key_id': aws_config.aws_access_key_id,
            'aws_secret_access_key': aws_config.aws_secret_access_key,
            'region_name': aws_config.region_name,
        }

        # Create session
        session = boto3.Session(**session_kwargs)

        # Configure user agent suffix
        config = Config(user_agent_extra=f"awslabs/mcp/eks-mcp-server/{__version__}")

        # Create client
        try:
            client = session.client(service_name, config=config)
        except Exception as e:
            raise Exception(f"Failed to create boto3 client for {service_name}: {e}")

        # Cache and return
        cls._client_cache[key] = client
        logger.info(f"Created new boto3 client for {service_name} (key={key})")
        return client
