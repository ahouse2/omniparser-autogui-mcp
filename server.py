from mcp.server.fastmcp import FastMCP

from src.mcp_autogui.mcp_autogui_main import mcp_autogui_main

mcp_main = FastMCP("omniparser_mcp")
mcp_autogui_main(mcp_main)

if __name__ == "__main__":
    mcp_main.run()