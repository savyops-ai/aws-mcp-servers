from pydantic import BaseModel, Field

class AwsCredentials(BaseModel):
    access_key: str = Field(..., description="AWS Access Key ID")
    secret_access_key: str = Field(..., description="AWS Secret Access Key")
