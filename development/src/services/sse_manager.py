"""
SSE Manager - Server-Sent Events for Sprint Execution Narration

Manages real-time event streams for sprint execution. Allows orchestrator to emit
team activity messages (Mike/Alex/Jordan) that appear in the UI without being
stored in chat history or sent to LLMs.

Architecture:
- Single global SSE stream for ALL sprint executions
- All sprint events flow through the same stream (like printing to one printer)
- Events include sprint_id in payload for filtering if needed
- Events are ephemeral (not stored, display-only)
"""
from __future__ import annotations
import asyncio
import logging
from typing import List, Any, Dict
from datetime import datetime

logger = logging.getLogger(__name__)


class SSEManager:
    """Manages Server-Sent Event streams for sprint execution narration."""
    
    def __init__(self):
        # Single list of queues for ALL sprints (global stream)
        self.streams: List[asyncio.Queue] = []
        # Buffer early messages before any listeners connect
        self.message_buffer: List[Dict[str, Any]] = []
        self.max_buffer_size = 200  # Keep last 200 messages total
        logger.info("SSE Manager initialized (single global stream)")
    
    async def emit(self, sprint_id: str, event: Dict[str, Any]) -> None:
        """
        Emit an event to all listeners (global stream).
        If no listeners, buffer the message for when they connect.
        
        Args:
            sprint_id: Sprint identifier (e.g., "SP-001") - added to event payload
            event: Event data (must be JSON-serializable)
        """
        # Add timestamp and sprint_id to event
        if "timestamp" not in event:
            event["timestamp"] = datetime.utcnow().isoformat()
        if "sprint_id" not in event:
            event["sprint_id"] = sprint_id
        
        if len(self.streams) == 0:
            # No listeners yet - buffer the message
            self.message_buffer.append(event)
            
            # Keep buffer size manageable
            if len(self.message_buffer) > self.max_buffer_size:
                self.message_buffer.pop(0)
            
            logger.debug(f"No listeners, buffered message from {sprint_id} (buffer size: {len(self.message_buffer)})")
            return
        
        # Emit to all active listeners
        dead_queues = []
        for queue in self.streams:
            try:
                await queue.put(event)
            except Exception as e:
                logger.warning(f"Failed to emit to queue: {e}")
                dead_queues.append(queue)
        
        # Clean up dead queues
        for queue in dead_queues:
            self.streams.remove(queue)
        
        logger.debug(f"Emitted event from {sprint_id} to {len(self.streams)} listeners")
    
    async def add_listener(self, queue: asyncio.Queue) -> None:
        """
        Add a new SSE listener to the global stream.
        Sends any buffered messages immediately.
        
        Args:
            queue: Asyncio queue for this listener
        """
        self.streams.append(queue)
        logger.info(f"Added listener to global stream (total: {len(self.streams)})")
        
        # Send buffered messages to this new listener
        if self.message_buffer:
            logger.info(f"Sending {len(self.message_buffer)} buffered messages to new listener")
            for event in self.message_buffer:
                try:
                    await queue.put(event)
                except Exception as e:
                    logger.warning(f"Failed to send buffered message: {e}")
            
            # Clear buffer after sending (only if this is the first listener)
            if len(self.streams) == 1:
                self.message_buffer = []
    
    def remove_listener(self, queue: asyncio.Queue) -> None:
        """
        Remove an SSE listener from the global stream.
        
        Args:
            queue: Queue to remove
        """
        if queue in self.streams:
            self.streams.remove(queue)
            logger.info(f"Removed listener from global stream (remaining: {len(self.streams)})")
    
    def get_listener_count(self) -> int:
        """Get number of active listeners on the global stream."""
        return len(self.streams)
    
    async def close_sprint_stream(self, sprint_id: str) -> None:
        """
        Send sprint completion event (stream stays open for other sprints).
        
        Args:
            sprint_id: Sprint identifier
        """
        # Send completion event to all listeners
        await self.emit(sprint_id, {
            "type": "sprint_complete",
            "sprint_id": sprint_id
        })
        
        logger.info(f"Sent sprint_complete event for {sprint_id} to {len(self.streams)} listeners")


# Global singleton instance
sse_manager = SSEManager()
