#!/usr/bin/env python3
"""
Remote OmniParser processing server
"""

import asyncio
import base64
import io
import json
import logging
import os
from typing import Any, Dict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from PIL import Image
import uvicorn

logger = logging.getLogger(__name__)

class AnalysisRequest(BaseModel):
    image: str  # base64 encoded
    task_description: str

class OmniParserServer:
    def __init__(self):
        self.app = FastAPI(title="OmniParser Server", version="0.1.0")
        self._omniparser = None
        self._setup_routes()
        self._setup_middleware()
    
    def _setup_middleware(self):
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    def _setup_routes(self):
        @self.app.get("/")
        async def health_check():
            return {"status": "healthy", "service": "omniparser-server"}
        
        @self.app.post("/analyze")
        async def analyze_image(request: AnalysisRequest):
            try:
                # Initialize OmniParser if needed
                if self._omniparser is None:
                    await self._initialize_omniparser()
                
                # Decode image
                image_data = base64.b64decode(request.image)
                image = Image.open(io.BytesIO(image_data))
                
                # Run analysis
                result = await asyncio.get_event_loop().run_in_executor(
                    None, self._run_analysis, image, request.task_description
                )
                
                return result
            
            except Exception as e:
                logger.error(f"Error analyzing image: {e}")
                raise HTTPException(status_code=500, detail=str(e))
    
    async def _initialize_omniparser(self):
        """Initialize OmniParser models"""
        try:
            import sys
            import os
            
            # Add OmniParser to path
            omniparser_path = os.path.join(os.path.dirname(__file__), '..', '..', 'OmniParser')
            if omniparser_path not in sys.path:
                sys.path.append(omniparser_path)
            
            from OmniParser.som import SoMModel
            from OmniParser.caption import CaptionModel
            
            # Get configuration from environment
            som_model_path = os.environ.get("SOM_MODEL_PATH")
            caption_model_name = os.environ.get("CAPTION_MODEL_NAME")
            caption_model_path = os.environ.get("CAPTION_MODEL_PATH")
            device = os.environ.get("OMNI_PARSER_DEVICE", "cpu")
            box_threshold = float(os.environ.get("BOX_THRESHOLD", "0.05"))
            
            # Initialize models
            som_model = SoMModel(
                model_path=som_model_path,
                device=device,
                box_threshold=box_threshold
            )
            
            caption_model = CaptionModel(
                model_name=caption_model_name,
                model_path=caption_model_path,
                device=device
            )
            
            self._omniparser = {
                'som': som_model,
                'caption': caption_model
            }
            
            logger.info("OmniParser models initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing OmniParser: {e}")
            raise
    
    def _run_analysis(self, image: Image.Image, task_description: str) -> Dict[str, Any]:
        """Run OmniParser analysis"""
        try:
            som_model = self._omniparser['som']
            caption_model = self._omniparser['caption']
            
            # Run SoM detection
            som_results = som_model.detect(image)
            
            # Generate captions for detected elements
            elements = []
            for i, (box, score) in enumerate(zip(som_results['boxes'], som_results['scores'])):
                x1, y1, x2, y2 = box
                element_image = image.crop((x1, y1, x2, y2))
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
            logger.error(f"Error running analysis: {e}")
            raise

async def serve():
    """Start the server"""
    server = OmniParserServer()
    
    host = os.environ.get("SSE_HOST", "127.0.0.1")
    port = int(os.environ.get("SSE_PORT", "8000"))
    
    config = uvicorn.Config(
        server.app,
        host=host,
        port=port,
        log_level="info"
    )
    
    server_instance = uvicorn.Server(config)
    await server_instance.serve()
