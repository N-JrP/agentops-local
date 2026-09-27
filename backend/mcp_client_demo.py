import asyncio
import os

from mcp import Client


async def main() -> None:
    server_url = os.getenv("MCP_SERVER_URL", "http://127.0.0.1:8001/mcp")

    async with Client(server_url) as client:
        listed = await client.list_tools()
        print("Available MCP tools:")
        for tool in listed.tools:
            print(f"- {tool.name}: {tool.description or ''}")

        incidents = await client.call_tool(
            "recent_public_incidents",
            {"query": "latest", "limit": 1},
        )
        print("\nrecent_public_incidents result:")
        print(incidents.structured_content or incidents.content)

        investigation = await client.call_tool(
            "investigate",
            {
                "question": (
                    "Investigate the latest GitHub incident. What happened, which "
                    "components were affected, and how was it resolved?"
                )
            },
        )
        print("\nFull AgentOps MCP investigation (includes plan/tool trace):")
        print(investigation.structured_content or investigation.content)


if __name__ == "__main__":
    asyncio.run(main())
