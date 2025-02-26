# omniparser-autogui-mcp

This is an [MCP server](https://modelcontextprotocol.io/introduction) that analyzes the screen with [OmniParser](https://github.com/microsoft/OmniParser) and automatically operates the GUI.  
Confirmed on Windows.

## License notes

This is MIT license, but Excluding submodules and sub packages.  
OmniParser's repository is CC-BY-4.0.  
Each OmniParser model has a different license ([reference](https://github.com/microsoft/OmniParser?tab=readme-ov-file#model-weights-license)).

## Installation

1. Please do the following:

```
git clone --recursive https://github.com/NON906/omniparser-autogui-mcp.git
cd omniparser-autogui-mcp
uv sync
uv run download_models.py
```

(If you want ``langchain_example.py`` to work, ``uv sync --extra langchain`` instead.)

2. Add this to your ``claude_desktop_config.json``:

```claude_desktop_config.json
{
  "mcpServers": {
    "omniparser_autogui_mcp": {
      "command": "uv",
      "args": [
        "--directory",
        "D:\\CLONED_PATH\\omniparser-autogui-mcp",
        "run",
        "omniparser-autogui-mcp"
      ],
      "env": {
        "PYTHONIOENCODING": "utf-8"
      }
    }
  }
}
```

(Replace ``D:\\CLONED_PATH\\omniparser-autogui-mcp`` with the directory you cloned.)

## Usage Examples

- Search for "MCP server" in the on-screen browser.

etc.