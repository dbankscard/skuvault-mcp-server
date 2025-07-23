"""
Request queue for managing bulk operations and preventing rate limit issues.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Callable, Tuple
from dataclasses import dataclass
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


@dataclass
class QueuedRequest:
    """Represents a queued API request."""
    id: str
    endpoint: str
    params: Dict[str, Any]
    callback: Optional[Callable] = None
    priority: int = 5  # 1-10, higher = more important
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if not self.id:
            self.id = str(uuid.uuid4())


class RequestQueue:
    """
    Manages queued requests to prevent overwhelming the API.
    """
    
    def __init__(self, max_concurrent: int = 2):
        """
        Initialize request queue.
        
        Args:
            max_concurrent: Maximum concurrent requests
        """
        self.queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self.max_concurrent = max_concurrent
        self.active_requests = 0
        self.results: Dict[str, Any] = {}
        self.processing = False
        self._process_task: Optional[asyncio.Task] = None
    
    async def add_request(
        self,
        endpoint: str,
        params: Dict[str, Any],
        priority: int = 5,
        callback: Optional[Callable] = None
    ) -> str:
        """
        Add a request to the queue.
        
        Args:
            endpoint: API endpoint
            params: Request parameters
            priority: Priority (1-10, higher = more important)
            callback: Optional callback for result
            
        Returns:
            Request ID
        """
        request = QueuedRequest(
            id=str(uuid.uuid4()),
            endpoint=endpoint,
            params=params,
            priority=priority,
            callback=callback
        )
        
        # Use negative priority for max heap behavior
        await self.queue.put((-priority, request.created_at, request))
        
        logger.debug(f"Queued request {request.id} for {endpoint}")
        
        # Start processing if not already running
        if not self.processing:
            await self.start_processing()
        
        return request.id
    
    async def add_bulk_requests(
        self,
        endpoint: str,
        params_list: List[Dict[str, Any]],
        priority: int = 5
    ) -> List[str]:
        """
        Add multiple requests for the same endpoint.
        
        Returns:
            List of request IDs
        """
        request_ids = []
        
        for params in params_list:
            request_id = await self.add_request(endpoint, params, priority)
            request_ids.append(request_id)
        
        return request_ids
    
    async def start_processing(self):
        """Start processing queued requests."""
        if not self.processing:
            self.processing = True
            self._process_task = asyncio.create_task(self._process_queue())
            logger.info("Started request queue processing")
    
    async def stop_processing(self):
        """Stop processing requests."""
        self.processing = False
        if self._process_task:
            self._process_task.cancel()
            try:
                await self._process_task
            except asyncio.CancelledError:
                pass
        logger.info("Stopped request queue processing")
    
    async def _process_queue(self):
        """Process requests from the queue."""
        from ..api_client import get_client
        
        while self.processing:
            if self.active_requests >= self.max_concurrent:
                # Wait a bit if we're at max concurrent
                await asyncio.sleep(0.1)
                continue
            
            try:
                # Wait for item with timeout
                priority, created_at, request = await asyncio.wait_for(
                    self.queue.get(),
                    timeout=1.0
                )
                
                # Process the request
                self.active_requests += 1
                asyncio.create_task(self._process_request(request))
                
            except asyncio.TimeoutError:
                # No items in queue, continue
                continue
            except Exception as e:
                logger.error(f"Error processing queue: {e}")
    
    async def _process_request(self, request: QueuedRequest):
        """Process a single request."""
        try:
            # Get API client
            from ..server import get_client
            client = get_client()
            
            # Make the API call
            result = await client.call_endpoint(request.endpoint, **request.params)
            
            # Store result
            self.results[request.id] = {
                "status": "success",
                "result": result,
                "completed_at": datetime.now()
            }
            
            # Call callback if provided
            if request.callback:
                try:
                    await request.callback(request.id, result)
                except Exception as e:
                    logger.error(f"Error in callback for {request.id}: {e}")
            
            logger.debug(f"Completed request {request.id}")
            
        except Exception as e:
            logger.error(f"Error processing request {request.id}: {e}")
            self.results[request.id] = {
                "status": "error",
                "error": str(e),
                "completed_at": datetime.now()
            }
        finally:
            self.active_requests -= 1
    
    async def get_result(self, request_id: str, timeout: float = 30.0) -> Any:
        """
        Get result for a request, waiting if necessary.
        
        Args:
            request_id: Request ID
            timeout: Maximum time to wait
            
        Returns:
            Request result
        """
        start_time = asyncio.get_event_loop().time()
        
        while asyncio.get_event_loop().time() - start_time < timeout:
            if request_id in self.results:
                result_data = self.results[request_id]
                if result_data["status"] == "success":
                    return result_data["result"]
                else:
                    raise Exception(result_data.get("error", "Unknown error"))
            
            await asyncio.sleep(0.1)
        
        raise TimeoutError(f"Timeout waiting for result of {request_id}")
    
    async def get_bulk_results(
        self,
        request_ids: List[str],
        timeout: float = 60.0
    ) -> Dict[str, Any]:
        """
        Get results for multiple requests.
        
        Returns:
            Dict mapping request ID to result
        """
        results = {}
        
        # Use asyncio.gather with timeout
        tasks = [
            self.get_result(req_id, timeout)
            for req_id in request_ids
        ]
        
        try:
            gathered_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for req_id, result in zip(request_ids, gathered_results):
                if isinstance(result, Exception):
                    results[req_id] = {"error": str(result)}
                else:
                    results[req_id] = result
                    
        except Exception as e:
            logger.error(f"Error getting bulk results: {e}")
        
        return results
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        return {
            "queued_requests": self.queue.qsize(),
            "active_requests": self.active_requests,
            "completed_requests": len(self.results),
            "max_concurrent": self.max_concurrent,
            "processing": self.processing
        }


# Global request queue instance
global_request_queue = RequestQueue()