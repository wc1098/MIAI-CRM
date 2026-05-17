from pydantic import BaseModel, Field


class OssPolicyRequestSchema(BaseModel):
    scene: str = Field(description="上传场景")
    filename: str = Field(description="原始文件名")
    content_type: str = Field(description="文件 MIME 类型")
    size: int = Field(default=0, description="文件大小")


class OssPolicyResponseSchema(BaseModel):
    host: str
    object_key: str
    file_url: str
    policy: str
    signature: str
    access_key_id: str
    expire_at: str
    max_size: int


class UploadConfirmRequestSchema(BaseModel):
    scene: str = Field(description="上传场景")
    object_key: str = Field(description="OSS 对象 Key")
    file_url: str = Field(description="文件访问 URL")


class UploadConfirmResponseSchema(BaseModel):
    file_name: str
    origin_name: str | None = None
    file_path: str
    file_url: str
    object_key: str
    content_type: str | None = None
    scene: str
