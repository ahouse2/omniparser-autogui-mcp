
def main():
    from mcp.server.fastmcp import FastMCP
    from .mcp_autogui_main import mcp_autogui_main
    mcp_main = FastMCP("omniparser_mcp")
    mcp_autogui_main(mcp_main)
    mcp_main.run()
