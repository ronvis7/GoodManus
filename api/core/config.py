from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """GoodManus后端中控配置信息，从.env或者环境变量中加载数据"""

    # 项目基础配置
    env: str = "development"
    log_level: str = "INFO"
    app_config_filepath: str = "config.yaml"

    # 数据库相关配置
    postgres_host: str = Field(default="localhost", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")
    postgres_user: str = Field(default="postgres", alias="POSTGRES_USER")
    postgres_password: str = Field(default="postgres", alias="POSTGRES_PASSWORD")
    postgres_db: str = Field(default="manus", alias="POSTGRES_DB")

    @property
    def sqlalchemy_database_uri(self) -> str:
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    # Redis缓存配置
    redis_host: str = Field(default="localhost", alias="REDIS_HOST")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")
    redis_db: int = Field(default=0, alias="REDIS_DB")
    redis_password: Optional[str] = Field(default=None, alias="REDIS_PASSWORD")

    # Cos腾讯云对象存储配置
    cos_secret_id: str = Field(default="", alias="COS_SECRET_ID")
    cos_secret_key: str = Field(default="", alias="COS_SECRET_KEY")
    cos_region: str = Field(default="", alias="COS_REGION")
    cos_scheme: str = Field(default="https", alias="COS_SCHEME")
    cos_bucket: str = Field(default="", alias="COS_BUCKET")
    cos_domain: str = Field(default="", alias="COS_DOMAIN")

    # Sandbox配置
    sandbox_address: Optional[str] = Field(default=None, alias="SANDBOX_ADDRESS")
    sandbox_image: Optional[str] = Field(default=None, alias="SANDBOX_IMAGE")
    sandbox_name_prefix: Optional[str] = Field(default=None, alias="SANDBOX_NAME_PREFIX")
    sandbox_ttl_minutes: Optional[int] = Field(default=60, alias="SANDBOX_TTL_MINUTES")
    sandbox_network: Optional[str] = Field(default=None, alias="SANDBOX_NETWORK")
    sandbox_chrome_args: Optional[str] = Field(default="", alias="SANDBOX_CHROME_ARGS")
    sandbox_https_proxy: Optional[str] = Field(default=None, alias="SANDBOX_HTTPS_PROXY")
    sandbox_http_proxy: Optional[str] = Field(default=None, alias="SANDBOX_HTTP_PROXY")
    sandbox_no_proxy: Optional[str] = Field(default=None, alias="SANDBOX_NO_PROXY")

    # 使用pydantic v2的写法来完成环境变量信息的告知
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )


@lru_cache()
def get_settings() -> Settings:
    """获取当前GoodManus项目的配置信息，并对内容进行缓存，避免重复读取"""
    settings = Settings()
    return settings
