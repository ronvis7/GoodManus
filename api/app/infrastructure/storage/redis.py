import logging
from core.config import get_settings,Settings
from redis.asyncio import Redis
from functools import lru_cache

logger = logging.getLogger(__name__)


class RedisClient:
    """Redis客户端，用于连接Redis缓存连接&使用"""

    def __init__(self):
        """构造函数，完成Redis客户端的创建"""
        self._client: Redis | None = None
        self._settings: Settings = get_settings()

    async def init(self)->None:
        """初始化Redis客户端"""
        # 1.判断客户端是否存在，如果Redis客户端已存在，则无需重复初始化
        if self._client:
            logger.warning("Redis客户端已存在，无需重复初始化")
            return
        
        try:
            # 2.创建Redis客户端并连接
            self._client = Redis(
                host=self._settings.redis_host,
                port=self._settings.redis_port,
                db=self._settings.redis_db,
                password=self._settings.redis_password,
                decode_responses=True,
            )
            # 3.测试连接是否成功
            await self._client.ping()
            logger.info("Redis客户端初始化成功")
        except Exception as e:
            logger.error(f"初始化Redis客户端失败: {str(e)}")
            raise e


    async def shutdown(self)->None:
        """关闭Redis客户端"""
        # 1.客户端存在则关闭客户端并提示
        if self._client is not None:
            await self._client.aclose()
            self._client = None
            logger.info("Redis客户端关闭成功")


    @property
    def client(self) -> Redis:
        """只读属性，返回 redis 客户端"""
        if self._client is None:
            raise RuntimeError("Redis客户端未初始化")
        return self._client


@lru_cache()
def get_redis() -> RedisClient:
    """获取Redis客户端实例，使用lru_cache缓存，避免重复创建"""
    return RedisClient()
