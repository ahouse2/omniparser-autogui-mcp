#!/usr/bin/env python3
"""
OmniParser client for screen analysis
"""

import asyncio
import base64
import io
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

import requests
from PIL import Image

logger = logging.getLogger(__name__)

class OmniParserClient:
    """Client for OmniParser screen analysis"""
    
    def __init__(self):
        self.server_url = os.environ.get("OMNI_PARSER_SERVER")
        self.backend_load = os.environ.get("OMNI_PARSER_BACKEND_LOAD", "0") == "1"
        
        # OmniParser configuration
        self.som_model_path = os.environ.get("SOM_MODEL_PATH")
        self.caption_model_name = os.environ.get("CAPTION_MODEL_NAME")
        self.caption_model_path = os.environ.get("CAPTION_MODEL_PATH")
        self.device = os.environ.get("OMNI_PARSER_DEVICE", "cpu")
        self.box_threshold = float(os.environ.get("BOX_THRESHOLD", "0.05"))
        
        self._omniparser = None
        
        logger.info(f"OmniParserClient initialized. Server: {self.server_url}, Backend load: {self.backend_load}")
    
    async def analyze_screen(self, task_description: str, window_name: Optional[str] = None) -> Dict[str, Any]:
        """Analyze the screen using OmniParser"""
        try:
            # Import here to avoid loading if not needed
            from .gui_controller import GUIController
            
            # Take screenshot first
            gui_controller = GUIController()
            screenshot_result = await gui_controller.take_screenshot(window_name)
            
            if not screenshot_result["success"]:
                return screenshot_result
            
            screenshot_b64 = screenshot_result["screenshot"]
            
            # If we have a remote server, use it
            if self.server_url:
                return await self._analyze_remote(screenshot_b64, task_description)
            else:
                return await self._analyze_local(screenshot_b64, task_description)
        
        except Exception as e:
            logger.error(f"Error analyzing screen: {e}")
            return {"success": False, "error": str(e)}
    
    async def _analyze_remote(self, screenshot_b64: str, task_description: str) -> Dict[str, Any]:
        """Analyze screenshot using remote OmniParser server"""
        try:
            payload = {
                "image": screenshot_b64,
                "task_description": task_description
            }
            
            response = requests.post(
                f"http://{self.server_url}/analyze",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "analysis": result,
                    "task_description": task_description,
                    "timestamp": time.time()
                }
            else:
                return {
                    "success": False,
                    "error": f"Server returned status {response.status_code}: {response.text}"
                }
        
        except Exception as e:
            logger.error(f"Error in remote analysis: {e}")
            return {"success": False, "error": str(e)}
    
    async def _analyze_local(self, screenshot_b64: str, task_description: str) -> Dict[str, Any]:
        """Analyze screenshot using local OmniParser"""
        try:
            # Initialize OmniParser if not already done
            if self._omniparser is None:
                await self._initialize_omniparser()
            
            # Convert base64 to PIL Image
            image_data = base64.b64decode(screenshot_b64)
            image = Image.open(io.BytesIO(image_data))
            
            # Run OmniParser analysis
            result = await asyncio.get_event_loop().run_in_executor(
                None, self._run_omniparser_analysis, image, task_description
            )
            
            return {
                "success": True,
                "analysis": result,
                "task_description": task_description,
                "timestamp": time.time()
            }
        
        except Exception as e:
            logger.error(f"Error in local analysis: {e}")
            return {"success": False, "error": str(e)}
    
    async def _initialize_omniparser(self):
        """Initialize the local OmniParser instance"""
        try:
            # Import OmniParser modules
            import sys
            import os
            
            # Add OmniParser to path
            omniparser_path = os.path.join(os.path.dirname(__file__), '..', '..', 'OmniParser')
            if omniparser_path not in sys.path:
                sys.path.append(omniparser_path)
            
            from OmniParser.som import SoMModel
            from OmniParser.caption import CaptionModel
            
            # Initialize models
            som_model = SoMModel(
                model_path=self.som_model_path,
                device=self.device,
                box_threshold=self.box_threshold
            )
            
            caption_model = CaptionModel(
                model_name=self.caption_model_name,
                model_path=self.caption_model_path,
                device=self.device
            )
            
            self._omniparser = {
                'som': som_model,
                'caption': caption_model
            }
            
            logger.info("OmniParser models initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing OmniParser: {e}")
            raise
    
    def _run_omniparser_analysis(self, image: Image.Image, task_description: str) -> Dict[str, Any]:
        """Run OmniParser analysis on the image"""
        try:
            if not self._omniparser:
                raise RuntimeError("OmniParser not initialized")
            
            som_model = self._omniparser['som']
            caption_model = self._omniparser['caption']
            
            # Run SoM (Set of Marks) detection
            som_results = som_model.detect(image)
            
            # Run caption generation for detected elements
            elements = []
            for i, (box, score) in enumerate(zip(som_results['boxes'], som_results['scores'])):
                # Extract element region
                x1, y1, x2, y2 = box
                element_image = image.crop((x1, y1, x2, y2))
                
                # Generate caption
                caption = caption_model.generate_caption(element_image)
                
                elements.append({
                    'id': i,
                    'box': [int(x1), int(y1), int(x2), int(y2)],
                    'score': float(score),
                    'caption': caption,
                    'center': [int((x1 + x2) / 2), int((y1 + y2) / 2)]
                })
            
            return {
                'elements': elements,
                'total_elements': len(elements),
                'image_size': [image.width, image.height],
                'task_description': task_description
            }
        
        except Exception as e:
            logger.error(f"Error running OmniParser analysis: {e}")
            raise
    
    def find_element_by_description(self, analysis_result: Dict[str, Any], description: str) -> Optional[Dict[str, Any]]:
        """Find an element in the analysis result by description"""
        try:
            if not analysis_result.get('success') or 'analysis' not in analysis_result:
                return None
            
            elements = analysis_result['analysis'].get('elements', [])
            description_lower = description.lower()
            
            # Simple matching - could be enhanced with semantic similarity
            best_match = None
            best_score = 0
            
            for element in elements:
                caption = element.get('caption', '').lower()
                
                # Simple keyword matching
                if description_lower in caption:
                    score = len(description_lower) / len(caption) if caption else 0
                    if score > best_score:
                        best_score = score
                        best_match = element
            
            return best_match
        
        except Exception as e:
            logger.error(f"Error finding element by description: {e}")
            return None
