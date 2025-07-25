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
"""Utility functions for AWS Documentation MCP Server."""

import os
import boto3
from typing import Any, Dict, Union
from pydantic import BaseModel, Field
from mypy_boto3_kendra.client import KendraClient

class AwsCredentials(BaseModel):
    access_key: str = Field(..., description="AWS Access Key ID")
    secret_access_key: str = Field(..., description="AWS Secret Access Key")


def _get_keys(creds: Union[AwsCredentials, Dict[str, Any]]) -> Dict[str, str]:
    if isinstance(creds, AwsCredentials):
        data = creds
    else:
        data = AwsCredentials(**creds)  # will validate or raise
    return data.model_dump(include={"access_key", "secret_access_key"})


def get_kendra_client(creds: Union[AwsCredentials, Dict[str, Any]], region=None) -> KendraClient:
    """Get a Kendra runtime client.

    Allows access to Kendra Indexes for RAG via the Kendra runtime client.

    Returns:
        boto3.client: A boto3 Kendra client instance.
    """
    # Extract access keys from credentials
    keys = _get_keys(creds)
    access_key = keys["access_key"]
    secret_access_key = keys["secret_access_key"]
    # Initialize the Kendra client with given region or profile
    AWS_REGION = region or os.environ.get('AWS_REGION', 'us-east-1')

    kendra_client = boto3.client(
        'kendra',
        aws_access_key_id = access_key,
        aws_secret_access_key = secret_access_key,
        region_name=AWS_REGION
    )
    return kendra_client
