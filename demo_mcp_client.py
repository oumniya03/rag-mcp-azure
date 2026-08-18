import asyncio
from mcp.client.streamable_http import streamable_http_client
from mcp import ClientSession


async def demo():
    url = "https://rag-mcp-azure.redsand-f0795bb6.francecentral.azurecontainerapps.io/mcp-server/mcp"

    print(f"Connexion au serveur MCP : {url}\n")
    async with streamable_http_client(url) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("Session MCP initialisee avec succes.\n")

            tools = await session.list_tools()
            print(f"Outils disponibles : {[t.name for t in tools.tools]}\n")

            query = "duree maximale contrat interimaire"
            print(f"Appel de search_documents avec query='{query}'\n")
            result = await session.call_tool("search_documents", {"query": query})

            print("Resultat retourne par le serveur MCP :\n")
            for content in result.content:
                if hasattr(content, "text"):
                    print(content.text)


if __name__ == "__main__":
    asyncio.run(demo())