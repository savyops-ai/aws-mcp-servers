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

"""awslabs amazon-qindex MCP Server implementation."""

import boto3
import os
import sys
from typing import Dict, List, Union, Any
from awslabs.amazon_qindex_mcp_server.clients import QBusinessClient, QBusinessClientError
from loguru import logger
from mcp.server.fastmcp import FastMCP
from mypy_boto3_qbusiness.type_defs import SearchRelevantContentResponseTypeDef
from pydantic import BaseModel, Field
from typing import Dict, List, Optional


# Configure logging
logger.remove(0)
logger.add(sys.stderr, level='INFO')


class DocumentAttributeValue(BaseModel):
    """Model for document attribute value types."""

    stringValue: Optional[str] = Field(default=None, description='String value')
    stringListValue: Optional[List[str]] = Field(default=None, description='List of string values')
    longValue: Optional[int] = Field(default=None, description='Long integer value')
    longListValue: Optional[List[int]] = Field(
        default=None, description='List of long integer values'
    )
    dateValue: Optional[str] = Field(default=None, description='Date value in ISO 8601 format')
    dateListValue: Optional[List[str]] = Field(default=None, description='List of date values')


class DocumentAttribute(BaseModel):
    """Model for document attribute with name and value."""

    name: str = Field(description='Name of the document attribute')
    value: DocumentAttributeValue = Field(description='Value of the document attribute')


class AttributeFilter(BaseModel):
    """Model for attribute filter conditions."""

    andAllFilters: Optional[List['AttributeFilter']] = Field(
        default=None, description='List of filters to AND together'
    )
    orAllFilters: Optional[List['AttributeFilter']] = Field(
        default=None, description='List of filters to OR together'
    )
    notFilter: Optional['AttributeFilter'] = Field(
        default=None, description='Negation of a filter'
    )
    equalsTo: Optional[DocumentAttribute] = Field(default=None, description='Exact match filter')
    containsAll: Optional[DocumentAttribute] = Field(
        default=None, description='Contains all values filter'
    )
    containsAny: Optional[DocumentAttribute] = Field(
        default=None, description='Contains any values filter'
    )
    greaterThan: Optional[DocumentAttribute] = Field(
        default=None, description='Greater than filter'
    )
    greaterThanOrEquals: Optional[DocumentAttribute] = Field(
        default=None, description='Greater than or equals filter'
    )
    lessThan: Optional[DocumentAttribute] = Field(default=None, description='Less than filter')
    lessThanOrEquals: Optional[DocumentAttribute] = Field(
        default=None, description='Less than or equals filter'
    )


class RetrieverContentSource(BaseModel):
    """Model for retriever content source."""

    retrieverId: str = Field(description='Identifier of the retriever')


class ContentSource(BaseModel):
    """Model for content source configuration.

    This is a union type, so only one field should be specified.
    """

    retriever: Optional[RetrieverContentSource] = Field(
        default=None, description='Retriever to use as content source'
    )

class AwsCredentials(BaseModel):
    access_key: str = Field(..., description="AWS Access Key ID")
    secret_access_key: str = Field(..., description="AWS Secret Access Key")
    region: str = Field("us-east-1", description="AWS Region, defaults to us-east-1")

# # Update forward references for recursive AttributeFilter
AttributeFilter.model_rebuild()


# Initialize MCP server
mcp = FastMCP(
    'awslabs.amazon-qindex-mcp-server',
    instructions="Amazon Q index for ISVs MCP server provides access to your customers' enterprise data into your applications.",
    dependencies=[
        'pydantic',
        'loguru',
        'boto3',
    ],
)

def _get_keys(creds: Union[AwsCredentials, Dict[str, Any]]) -> Dict[str, str]:
    if isinstance(creds, AwsCredentials):
        data = creds
    else:
        data = AwsCredentials(**creds)  # will validate or raise
    return data.model_dump(include={"access_key", "secret_access_key"})

@mcp.tool(name='SearchRelevantContent')
async def search_relevant_content(
    creds: AwsCredentials = Field(
        ..., description="AWS credentials: access_key, secret_access_key and region"
    ),
    application_id: str = Field(
        description='The unique identifier of the application to search in'
    ),
    query_text: str = Field(description='The text to search for'),
    attribute_filter: Optional[AttributeFilter] = Field(
        default=None,
        description='Filter criteria to narrow down search results based on specific document attributes',
    ),
    content_source: Optional[ContentSource] = Field(
        default=None,
        description='Configuration specifying which content sources to include in the search',
    ),
    max_results: Optional[int] = Field(
        default=3, description='Maximum number of results to return (1-100)', ge=1, le=100
    ),
    next_token: Optional[str] = Field(
        default=None, description='Token for pagination to get the next set of results'
    ),
) -> SearchRelevantContentResponseTypeDef:
    """Search for relevant content in an Amazon Q Business application.

    This operation searches for content within a Q Business application based on the provided
    query text and returns relevant matches.

    IMPORTANT: This tool requires valid AWS credentials. If credentials are not provided or are invalid,
    you must first:
    1. Call AuthorizeQBusiness to get an authorization URL
    2. Have the user authenticate at that URL to get an authorization code
    3. Call CreateTokenWithIAM with the code to get a token
    4. Call AssumeRoleWithIdentityContext with the token's identity context to get temporary credentials
    5. Finally, call this tool again with those temporary credentials

    See: https://docs.aws.amazon.com/amazonq/latest/api-reference/API_SearchRelevantContent.html

    Parameters:
        application_id (str): The unique identifier of the application to search in
        query_text (str): The text to search for
        attribute_filter (Optional[AttributeFilter]): Filter criteria to narrow down search results based on specific document attributes
        content_source (Optional[ContentSource]): Configuration specifying which content sources to include in the search
        max_results (Optional[int]): Maximum number of results to return (1-100)
        next_token (Optional[str]): Token for pagination to get the next set of results


    Returns:
        Dict: Response syntax:
        {
            'nextToken': 'string',
            'relevantContent': [
                {
                    'content': 'string',
                    'documentAttributes': [
                        {
                            'name': 'string',
                            'value': {
                                # Various value types based on attribute
                            }
                        }
                    ],
                    'documentId': 'string',
                    'documentTitle': 'string',
                    'documentUri': 'string',
                    'scoreAttributes': {
                        'scoreConfidence': 'string'
                    }
                }
            ]
        }

    Raises:
        ValueError: If there's an error with the Q Business API call or if credentials are missing/invalid
    """
    try:
        # extract keys
        keys = _get_keys(creds)
        region_name = keys.get('region', os.environ.get('AWS_REGION', 'us-east-1'))
        aws_access_key_id = keys['access_key']
        aws_secret_access_key = keys['secret_access_key']
        
        # Check for credentials first
        if not aws_access_key_id or not aws_secret_access_key:
            raise QBusinessClientError('Missing AWS credentials')

        # Create QBusinessClient with provided credentials
        client = QBusinessClient(
            region_name=region_name,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
        )

        # Convert models to dictionaries
        content_source_dict = None
        if content_source:
            content_source_dict = content_source.model_dump(exclude_none=True)
            if 'retriever' in content_source_dict:
                content_source_dict = {'retriever': content_source_dict['retriever']}

        attribute_filter_dict = None
        if attribute_filter:
            attribute_filter_dict = attribute_filter.model_dump(exclude_none=True)

        # Ensure max_results is properly typed
        max_results_int = int(max_results) if max_results is not None else None

        # Perform the search
        return client.search_relevant_content(
            application_id=str(application_id),
            query_text=str(query_text),
            attribute_filter=attribute_filter_dict,
            content_source=content_source_dict,
            max_results=max_results_int,
            next_token=str(next_token) if next_token else None,
        )
    except Exception as e:
        logger.error(f'Error searching Q Business content: {str(e)}')
        raise ValueError(str(e))


def main():
    """Run the MCP server with CLI argument support."""
    mcp.run()


if __name__ == '__main__':
    main()
