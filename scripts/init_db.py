"""初始化数据库脚本"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from src.infrastructure.persistence.database import Base
from src.infrastructure.config.settings import get_settings

settings = get_settings()


async def init_database() -> None:
    """初始化数据库表"""
    print("开始初始化数据库...")

    engine = create_async_engine(settings.database_url, echo=True)

    async with engine.begin() as conn:
        # 创建所有表
        await conn.run_sync(Base.metadata.create_all)

    await engine.dispose()

    print("数据库初始化完成！")


if __name__ == "__main__":
    asyncio.run(init_database())
