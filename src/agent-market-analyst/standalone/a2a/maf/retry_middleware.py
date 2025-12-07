"""Rate limit retry middleware for Microsoft Agent Framework.

This module provides ChatMiddleware implementations for handling 429 rate limit
errors from Azure OpenAI and other AI services with exponential backoff.

Based on Microsoft Agent Framework middleware patterns:
https://learn.microsoft.com/en-us/agent-framework/user-guide/agents/agent-middleware
"""

import asyncio
import logging
import random
import re
from collections.abc import Awaitable, Callable

from agent_framework import ChatContext, ChatMiddleware
from agent_framework.exceptions import ServiceResponseException

logger = logging.getLogger(__name__)


def _is_rate_limit_error(exception: Exception) -> bool:
    """Check if an exception is a rate limit (429) error."""
    error_str = str(exception).lower()
    rate_limit_indicators = [
        "429", "rate limit", "rate_limit", "ratelimit",
        "too many requests", "too_many_requests", "throttl",
        "quota exceeded", "request rate too large",
    ]
    return any(indicator in error_str for indicator in rate_limit_indicators)


def _extract_retry_after(exception: Exception) -> float | None:
    """Extract retry-after value from exception if available."""
    error_str = str(exception)
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
    """Chat middleware that retries on rate limit (429) errors with exponential backoff."""

    def __init__(
        self,
        max_retries: int = 5,
        initial_delay: float = 2.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
    ) -> None:
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter

    def _calculate_delay(self, attempt: int, retry_after: float | None = None) -> float:
        if retry_after is not None and retry_after > 0:
            delay = min(retry_after, self.max_delay)
        else:
            delay = self.initial_delay * (self.exponential_base ** attempt)
            delay = min(delay, self.max_delay)
        if self.jitter:
            delay += delay * random.uniform(0, 0.25)
        return delay

    async def process(
        self,
        context: ChatContext,
        next: Callable[[ChatContext], Awaitable[None]],
    ) -> None:
        last_exception: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                await next(context)
                if attempt > 0:
                    logger.info("Chat request succeeded after %d retry attempt(s)", attempt)
                return
            except ServiceResponseException as exc:
                last_exception = exc
                if not _is_rate_limit_error(exc):
                    raise
                if attempt >= self.max_retries:
                    logger.error("Max retries (%d) exceeded for rate limit error", self.max_retries)
                    raise
                retry_after = _extract_retry_after(exc)
                delay = self._calculate_delay(attempt, retry_after)
                logger.warning(
                    "Rate limit (429) encountered. Retry %d/%d in %.1f seconds.",
                    attempt + 1, self.max_retries, delay,
                )
                await asyncio.sleep(delay)
            except Exception as exc:
                if _is_rate_limit_error(exc):
                    last_exception = exc
                    if attempt >= self.max_retries:
                        raise
                    delay = self._calculate_delay(attempt, _extract_retry_after(exc))
                    logger.warning(
                        "Rate limit detected. Retry %d/%d in %.1f seconds.",
                        attempt + 1, self.max_retries, delay,
                    )
                    await asyncio.sleep(delay)
                else:
                    raise

        if last_exception is not None:
            raise last_exception
