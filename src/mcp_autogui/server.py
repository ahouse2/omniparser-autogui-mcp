#!/usr/bin/env python3
"""
MCP server for automatic GUI operations using OmniParser
"""

import asyncio
import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional

import mcp.types as types
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server

from .gui_controller import GUIController
from .omniparser_client import OmniParserClient

logger = logging.getLogger(__name__)

class MCPAutoGUIServer:
    def __init__(self):
        self.gui_controller = GUIController()
        self.omniparser_client = OmniParserClient()
        self.server = Server("omniparser-autogui-mcp")
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup MCP server handlers"""
        
        @self.server.list_tools()
        async def handle_list_tools() -> List[types.Tool]:
            """List available tools"""
            return [
                types.Tool(
                    name="take_screenshot",
                    description="Take a screenshot of the current screen or specified window",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "window_name": {
                                "type": "string",
                                "description": "Name of the window to capture (optional, captures full screen if not specified)"
                            }
                        }
                    }
                ),
                types.Tool(
                    name="analyze_screen",
                    description="Analyze the current screen using OmniParser to identify GUI elements",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "window_name": {
                                "type": "string",
                                "description": "Name of the window to analyze (optional)"
                            },
                            "task_description": {
                                "type": "string",
                                "description": "Description of what you want to find or do on the screen"
                            }
                        },
                        "required": ["task_description"]
                    }
                ),
                types.Tool(
                    name="click_element",
                    description="Click on a GUI element identified by coordinates or description",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "x": {
                                "type": "number",
                                "description": "X coordinate to click"
                            },
                            "y": {
                                "type": "number",
                                "description": "Y coordinate to click"
                            },
                            "element_description": {
                                "type": "string",
                                "description": "Description of the element to click (alternative to coordinates)"
                            },
                            "click_type": {
                                "type": "string",
                                "enum": ["left", "right", "double"],
                                "default": "left",
                                "description": "Type of click to perform"
                            }
                        }
                    }
                ),
                types.Tool(
                    name="type_text",
                    description="Type text into the currently focused input field",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "text": {
                                "type": "string",
                                "description": "Text to type"
                            },
                            "clear_first": {
                                "type": "boolean",
                                "default": False,
                                "description": "Whether to clear the field before typing"
                            }
                        },
                        "required": ["text"]
                    }
                ),
                types.Tool(
                    name="press_key",
                    description="Press a keyboard key or key combination",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "key": {
                                "type": "string",
                                "description": "Key or key combination to press (e.g., 'enter', 'ctrl+c', 'alt+tab')"
                            }
                        },
                        "required": ["key"]
                    }
                ),
                types.Tool(
                    name="get_window_list",
                    description="Get a list of currently open windows",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                types.Tool(
                    name="focus_window",
                    description="Focus on a specific window",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "window_name": {
                                "type": "string",
                                "description": "Name of the window to focus"
                            }
                        },
                        "required": ["window_name"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def handle_call_tool(
            name: str, arguments: dict
        ) -> List[types.TextContent]:
            """Handle tool calls"""
            try:
                if name == "take_screenshot":
                    result = await self.gui_controller.take_screenshot(
                        arguments.get("window_name")
                    )
                    return [types.TextContent(type="text", text=json.dumps(result))]
                
                elif name == "analyze_screen":
                    result = await self.omniparser_client.analyze_screen(
                        task_description=arguments["task_description"],
                        window_name=arguments.get("window_name")
                    )
                    return [types.TextContent(type="text", text=json.dumps(result))]
                
                elif name == "click_element":
                    if "x" in arguments and "y" in arguments:
                        result = await self.gui_controller.click_coordinates(
                            arguments["x"], arguments["y"], 
                            arguments.get("click_type", "left")
                        )
                    elif "element_description" in arguments:
                        result = await self.gui_controller.click_element_by_description(
                            arguments["element_description"],
                            arguments.get("click_type", "left")
                        )
                    else:
                        raise ValueError("Either coordinates (x, y) or element_description must be provided")
                    return [types.TextContent(type="text", text=json.dumps(result))]
                
                elif name == "type_text":
                    result = await self.gui_controller.type_text(
                        arguments["text"], arguments.get("clear_first", False)
                    )
                    return [types.TextContent(type="text", text=json.dumps(result))]
                
                elif name == "press_key":
                    result = await self.gui_controller.press_key(arguments["key"])
                    return [types.TextContent(type="text", text=json.dumps(result))]
                
                elif name == "get_window_list":
                    result = await self.gui_controller.get_window_list()
                    return [types.TextContent(type="text", text=json.dumps(result))]
                
                elif name == "focus_window":
                    result = await self.gui_controller.focus_window(arguments["window_name"])
                    return [types.TextContent(type="text", text=json.dumps(result))]
                
                else:
                    raise ValueError(f"Unknown tool: {name}")
            
            except Exception as e:
                logger.error(f"Error handling tool call {name}: {e}")
                return [types.TextContent(
                    type="text", 
                    text=json.dumps({"error": str(e), "success": False})
                )]


async def serve():
    """Main server function"""
    server_instance = MCPAutoGUIServer()
    
    # Check if we should use SSE instead of stdio
    if "SSE_HOST" in os.environ and "SSE_PORT" in os.environ:
        # SSE server setup would go here
        # For now, fall back to stdio
        pass
    
    async with stdio_server() as (read_stream, write_stream):
        await server_instance.server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="omniparser-autogui-mcp",
                server_version="0.1.0",
                capabilities=server_instance.server.get_capabilities(
                    notification_options=None,
                    experimental_capabilities={}
                )
            )
        )
