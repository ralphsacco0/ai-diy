"""
Chat API endpoint for triggering persona responses.
"""

import logging
from typing import Dict, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# Import AI gateway functionality
from services.ai_gateway import call_openrouter_api, load_personas
from core.models_config import ModelsConfig

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["chat"])

# DEPRECATED: Old polling-based system messages removed
# Sprint execution now uses SSE streaming via /api/sprints/{sprint_id}/stream

class ChatRequest(BaseModel):
    message: str
    room: str = "general"
    personas: List[str] = ["QA", "DEVELOPER"]

class ChatResponse(BaseModel):
    success: bool
    responses: Dict[str, str]

@router.post("/chat", response_model=ChatResponse)
async def send_chat_message(request: ChatRequest):
    """
    Send a chat message and get persona responses.
    Used by Alex to trigger Jordan after completing changes.
    """
    try:
        # Log full payload to file for debugging
        logger.info(f"=== CHAT REQUEST PAYLOAD ===")
        logger.info(f"Room: {request.room}")
        logger.info(f"Message: {request.message}")
        logger.info(f"Personas: {request.personas}")
        logger.info(f"Full request: {request.dict()}")
        logger.info(f"=== END PAYLOAD ===")
        
        # Load personas
        personas = load_personas()
        responses = {}
        
        # Call each requested persona
        for persona_key in request.personas:
            try:
                if persona_key not in personas:
                    logger.warning(f"Persona {persona_key} not found")
                    continue
                    
                persona_config = personas[persona_key]
                persona_name = persona_config["name"]
                system_prompt = persona_config["system_prompt"]
                
                # Create messages for the persona
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": request.message}
                ]
                
                # Get configured model instead of hardcoded one
                models_config = ModelsConfig()
                favorites, default_model, meta, last_session_name = models_config.load_config()
                model = default_model
                
                # Iterate through async generator to get final response
                response_content = None
                async for chunk in call_openrouter_api(messages, model, persona_name, persona_key):
                    if "content" in chunk:
                        response_content = chunk["content"]
                        break
                
                if response_content:
                    responses[persona_key] = response_content
                    logger.info(f"Chat response from {persona_key}: {len(response_content)} chars")
                    
                    # Note: Individual message processing removed - using turn-based system below
                    
            except Exception as e:
                logger.error(f"Error calling persona {persona_key}: {e}")
                responses[persona_key] = f"Error: {str(e)}"
        
        # Use new turn-based Scribe system for full conversation capture
        # But check if Scribe should be active during the current meeting
        try:
            from api.scribe import start_conversation_turn, add_persona_response, complete_conversation_turn
            import uuid
            
            # Check if any active persona has scribe_active_during_meeting: false
            scribe_disabled = False
            logger.info(f"Checking Scribe status for personas: {request.personas}")
            for persona_key in request.personas:
                if persona_key in personas:
                    persona_config = personas[persona_key]
                    scribe_flag = persona_config.get("scribe_active_during_meeting")
                    logger.info(f"Persona {persona_key}: scribe_active_during_meeting = {scribe_flag}")
                    # If this persona is in a meeting and has scribe disabled, skip Scribe
                    if scribe_flag == False:
                        scribe_disabled = True
                        logger.info(f"Scribe disabled for meeting with {persona_key}")
                        break
                else:
                    logger.warning(f"Persona {persona_key} not found in config")
            
            # Only call Scribe if not disabled
            if not scribe_disabled:
                # Generate unique turn ID
                turn_id = f"turn_{uuid.uuid4().hex[:8]}"
                
                # Start conversation turn with client message
                await start_conversation_turn(turn_id, request.message)
                
                # Add all persona responses to the turn
                for persona_key, response_content in responses.items():
                    if response_content and not response_content.startswith("Error:"):
                        await add_persona_response(turn_id, persona_key, response_content)
                
                # Complete and process the full conversation turn
                await complete_conversation_turn(turn_id)
            else:
                logger.info("Scribe skipped - disabled for this meeting")
            
        except Exception as scribe_error:
            logger.warning(f"Scribe conversation turn processing error: {scribe_error}")
        
        return ChatResponse(success=True, responses=responses)
        
    except Exception as e:
        logger.error(f"Chat endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
