import logging
from contextlib import asynccontextmanager

from mcp.client.session import ClientSession
from mcp.client.sse import sse_client

logger = logging.getLogger(__name__)


@asynccontextmanager
async def mcp_session(url: str):
    async with sse_client(url) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        yield session
