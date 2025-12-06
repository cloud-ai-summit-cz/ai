"""Rate limit retry middleware for Microsoft Agent Framework.

This module provides ChatMiddleware implementations for handling 429 rate limit
errors from Azure OpenAI and other AI services with exponential backoff.

Based on Microsoft Agent Framework middleware patterns:
https://learn.microsoft.com/en-us/agent-framework/user-guide/agents/agent-middleware

Usage:
    from retry_middleware import RateLimitRetryMiddleware
    
    # Create the retry middleware
    retry_middleware = RateLimitRetryMiddleware(
        max_retries=5,
        initial_delay=1.0,
        max_delay=60.0,
        exponential_base=2.0,
        jitter=True,
    )
    
    # Use with ChatAgent
    agent = ChatAgent(
        chat_client=client,
        middleware=[retry_middleware],
        ...
    )
"""

import asyncio
import logging
import random
from collections.abc import AsyncIterable, Awaitable, Callable
from typing import Any

from agent_framework import ChatContext, ChatMiddleware
from agent_framework.exceptions import ServiceResponseException

logger = logging.getLogger(__name__)


def _is_rate_limit_error(exception: Exception) -> bool:
    """Check if an exception is a rate limit (429) error.
    
    Args:
        exception: The exception to check.
        
    Returns:
        True if the exception indicates a rate limit error.
    """
    error_str = str(exception).lower()
    
    # Check for common rate limit indicators
    rate_limit_indicators = [
        "429",
        "rate limit",
        "rate_limit",
        "ratelimit",
        "too many requests",
        "too_many_requests",
        "toomanyrequest",
        "throttl",  # throttle, throttling, throttled
        "quota exceeded",
        "request rate too large",
    ]
    
    return any(indicator in error_str for indicator in rate_limit_indicators)


def _extract_retry_after(exception: Exception) -> float | None:
    """Extract retry-after value from exception if available.
    
    Args:
        exception: The exception that may contain retry-after information.
        
    Returns:
        The retry-after value in seconds, or None if not found.
    """
    error_str = str(exception)
    
    # Try to extract "retry after X seconds" pattern
    import re
    patterns = [
        r"retry[- ]?after[:\s]*(\d+(?:\.\d+)?)",
        r"try again in (\d+(?:\.\d+)?)\s*second",
        r"wait (\d+(?:\.\d+)?)\s*second",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, error_str, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass
    
    return None


class RateLimitRetryMiddleware(ChatMiddleware):
    """Chat middleware that retries on rate limit (429) errors with exponential backoff.
    
    This middleware intercepts calls to the AI service and automatically retries
    when rate limit errors are encountered. It uses exponential backoff with
    optional jitter to avoid thundering herd problems.
    
    Based on Microsoft recommended retry patterns:
    - https://learn.microsoft.com/en-us/azure/architecture/patterns/retry
    - https://learn.microsoft.com/en-us/azure/ai-foundry/openai/supported-languages#error-handling
    
    Attributes:
        max_retries: Maximum number of retry attempts.
        initial_delay: Initial delay in seconds before first retry.
        max_delay: Maximum delay in seconds between retries.
        exponential_base: Base for exponential backoff calculation.
        jitter: Whether to add random jitter to delays.
        
    Example:
        >>> middleware = RateLimitRetryMiddleware(max_retries=5)
        >>> agent = ChatAgent(chat_client=client, middleware=[middleware])
    """
    
    def __init__(
        self,
        max_retries: int = 5,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
    ) -> None:
        """Initialize the retry middleware.
        
        Args:
            max_retries: Maximum number of retry attempts (default: 5).
            initial_delay: Initial delay in seconds before first retry (default: 1.0).
            max_delay: Maximum delay in seconds between retries (default: 60.0).
            exponential_base: Base for exponential backoff calculation (default: 2.0).
            jitter: Whether to add random jitter to delays (default: True).
        """
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
    
    def _calculate_delay(self, attempt: int, retry_after: float | None = None) -> float:
        """Calculate delay for the given retry attempt.
        
        Uses exponential backoff with optional jitter:
        delay = min(initial_delay * (base ^ attempt), max_delay)
        
        If retry_after is provided from the API response, it takes precedence.
        
        Args:
            attempt: The current retry attempt number (0-indexed).
            retry_after: Optional retry-after value from API response.
            
        Returns:
            The delay in seconds before the next retry.
        """
        if retry_after is not None and retry_after > 0:
            # Use API-provided retry-after, but cap at max_delay
            delay = min(retry_after, self.max_delay)
        else:
            # Calculate exponential backoff
            delay = self.initial_delay * (self.exponential_base ** attempt)
            delay = min(delay, self.max_delay)
        
        if self.jitter:
            # Add random jitter between 0% and 25% of the delay
            jitter_amount = delay * random.uniform(0, 0.25)
            delay += jitter_amount
        
        return delay
    
    async def process(
        self,
        context: ChatContext,
        next: Callable[[ChatContext], Awaitable[None]],
    ) -> None:
        """Process a chat request with retry logic for rate limits.
        
        This method intercepts chat requests and retries them on rate limit
        errors using exponential backoff.
        
        Args:
            context: Chat invocation context containing chat client, messages, and options.
            next: Function to call the next middleware or final chat execution.
        """
        last_exception: Exception | None = None
        
        for attempt in range(self.max_retries + 1):  # +1 for initial attempt
            try:
                # Attempt the chat request
                await next(context)
                
                # Success - return without error
                if attempt > 0:
                    logger.info(
                        "Chat request succeeded after %d retry attempt(s)",
                        attempt,
                    )
                return
                
            except ServiceResponseException as exc:
                last_exception = exc
                
                # Check if this is a rate limit error
                if not _is_rate_limit_error(exc):
                    # Not a rate limit error - re-raise immediately
                    logger.warning(
                        "Non-rate-limit error encountered: %s",
                        str(exc)[:200],
                    )
                    raise
                
                # Check if we have retries left
                if attempt >= self.max_retries:
                    logger.error(
                        "Max retries (%d) exceeded for rate limit error: %s",
                        self.max_retries,
                        str(exc)[:200],
                    )
                    raise
                
                # Extract retry-after from exception if available
                retry_after = _extract_retry_after(exc)
                delay = self._calculate_delay(attempt, retry_after)
                
                logger.warning(
                    "Rate limit (429) encountered. Retry %d/%d in %.1f seconds. Error: %s",
                    attempt + 1,
                    self.max_retries,
                    delay,
                    str(exc)[:100],
                )
                
                # Wait before retrying
                await asyncio.sleep(delay)
                
            except Exception as exc:
                # For other exceptions, check if they might be rate limit related
                if _is_rate_limit_error(exc):
                    last_exception = exc
                    
                    if attempt >= self.max_retries:
                        logger.error(
                            "Max retries (%d) exceeded for rate limit error: %s",
                            self.max_retries,
                            str(exc)[:200],
                        )
                        raise
                    
                    retry_after = _extract_retry_after(exc)
                    delay = self._calculate_delay(attempt, retry_after)
                    
                    logger.warning(
                        "Rate limit detected in exception. Retry %d/%d in %.1f seconds. Error: %s",
                        attempt + 1,
                        self.max_retries,
                        delay,
                        str(exc)[:100],
                    )
                    
                    await asyncio.sleep(delay)
                else:
                    # Not a rate limit error - re-raise immediately
                    raise
        
        # If we get here, we've exhausted all retries
        if last_exception is not None:
            raise last_exception


class AgentRetryMiddleware:
    """Agent middleware that retries on rate limit errors.
    
    This is an alternative implementation using agent-level middleware
    instead of chat middleware. Use this when you want to retry the
    entire agent run rather than individual chat calls.
    
    Note: For most cases, RateLimitRetryMiddleware (chat middleware) is
    preferred as it retries at a more granular level.
    """
    
    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 2.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
    ) -> None:
        """Initialize the agent retry middleware.
        
        Args:
            max_retries: Maximum number of retry attempts.
            initial_delay: Initial delay in seconds.
            max_delay: Maximum delay in seconds.
            exponential_base: Base for exponential backoff.
            jitter: Whether to add random jitter.
        """
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
    
    async def __call__(
        self,
        context: Any,
        next: Callable[[Any], Awaitable[None]],
    ) -> None:
        """Process an agent run with retry logic."""
        from agent_framework import AgentRunContext
        
        if not isinstance(context, AgentRunContext):
            # Not an agent context - pass through
            await next(context)
            return
        
        last_exception: Exception | None = None
        
        for attempt in range(self.max_retries + 1):
            try:
                await next(context)
                if attempt > 0:
                    logger.info(
                        "Agent run succeeded after %d retry attempt(s)",
                        attempt,
                    )
                return
                
            except Exception as exc:
                if not _is_rate_limit_error(exc):
                    raise
                
                last_exception = exc
                
                if attempt >= self.max_retries:
                    logger.error(
                        "Max retries (%d) exceeded for agent run: %s",
                        self.max_retries,
                        str(exc)[:200],
                    )
                    raise
                
                # Calculate delay with exponential backoff
                delay = self.initial_delay * (self.exponential_base ** attempt)
                delay = min(delay, self.max_delay)
                
                if self.jitter:
                    delay += delay * random.uniform(0, 0.25)
                
                retry_after = _extract_retry_after(exc)
                if retry_after and retry_after > delay:
                    delay = min(retry_after, self.max_delay)
                
                logger.warning(
                    "Rate limit in agent run. Retry %d/%d in %.1f seconds.",
                    attempt + 1,
                    self.max_retries,
                    delay,
                )
                
                await asyncio.sleep(delay)
        
        if last_exception is not None:
            raise last_exception
