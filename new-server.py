# Add lifespan support for startup/shutdown with strong typing
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from dataclasses import dataclass

from mcp.server.fastmcp import Context, FastMCP

from libs.bunq_lib import BunqLib
from libs.share_lib import ShareLibOptions, ShareLib
from bunq import ApiEnvironmentType

# Specify dependencies for deployment and development


@dataclass
class AppContext:
    bunq: BunqLib
    environment_type: ApiEnvironmentType


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """Manage application lifecycle with type-safe context"""
    # Initialize on startup
    try:
        all_option = ShareLibOptions()
        environment_type = ShareLib.determine_environment_type_from_all_option(
            all_option
        )
        bunq_instance = BunqLib(environment_type)
        yield AppContext(bunq=bunq_instance, environment_type=environment_type)
    finally:
        # Cleanup on shutdown
        pass


# Pass lifespan to server
mcp = FastMCP("Bunq", dependencies=["bunq_sdk"], lifespan=app_lifespan)


# Access type-safe lifespan context in tools
@mcp.tool("bunq://hello")
def hello(ctx: Context) -> str:
    bunq_client = ctx.request_context.lifespan_context.bunq
    print(bunq_client)
    return "Hello"
