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

import boto3
from typing import Any, Optional
from awslabs.aws_serverless_mcp_server.models import AWSConfig


def get_aws_client(service_name: str, aws_config: AWSConfig) -> Any:
    """Creates and returns a boto3 client for the specified AWS service.

    Args:
        service_name (str): The name of the AWS service (e.g., 's3', 'ec2').
        aws_config (AWSConfig): The AWS configuration containing credentials and region.

    Returns:
        object: A boto3 client instance for the specified AWS service.

    Notes:
        - The client is configured with a custom user agent string for identification.
        - Requires valid AWS credentials to be configured in the environment.
    """
    session_args = {
        'aws_access_key_id': aws_config.aws_access_key_id,
        'aws_secret_access_key': aws_config.aws_secret_access_key,
    }
    session = boto3.Session(
        **session_args, region_name=aws_config.region_name
    ) if aws_config.region_name else boto3.Session(**session_args)
    return session.client(service_name)
