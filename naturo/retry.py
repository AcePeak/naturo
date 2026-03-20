"""Retry policies and decorator — aligned with Peekaboo's RetryPolicy.

Provides exponential-backoff retry logic with configurable policies.
Use as a decorator or context manager.
"""

from __future__ import annotations

import functools
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Set, TypeVar

from naturo.errors import ErrorCode, NaturoError

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


@dataclass
class RetryPolicy:
    """Retry configuration aligned with Peekaboo's RetryPolicy.

    Attributes:
        max_attempts: Maximum number of attempts (including the first).
        initial_delay: Seconds to wait before the first retry.
        delay_multiplier: Factor to multiply delay each retry.
        max_delay: Upper bound on delay between retries.
        retryable_codes: Error codes that are eligible for retry.
    """

    max_attempts: int = 3
    initial_delay: float = 0.1
    delay_multiplier: float = 2.0
    max_delay: float = 5.0
    retryable_codes: set[str] = field(default_factory=lambda: {
        ErrorCode.TIMEOUT,
        ErrorCode.CAPTURE_FAILED,
        ErrorCode.INTERACTION_FAILED,
        ErrorCode.FILE_IO_ERROR,
        ErrorCode.AI_PROVIDER_UNAVAILABLE,
    })

    def is_retryable(self, error: NaturoError) -> bool:
        """Check if an error is retryable under this policy."""
        return error.code in self.retryable_codes and error.is_recoverable

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for a given attempt (0-indexed)."""
        delay = self.initial_delay * (self.delay_multiplier ** attempt)
        return min(delay, self.max_delay)


# ── Presets matching Peekaboo ────────────────────────────────────────────────

STANDARD = RetryPolicy()

AGGRESSIVE = RetryPolicy(
    max_attempts=5,
    initial_delay=0.05,
    delay_multiplier=2.0,
    max_delay=5.0,
)

CONSERVATIVE = RetryPolicy(
    max_attempts=2,
    initial_delay=0.5,
    delay_multiplier=2.0,
    max_delay=10.0,
)

NO_RETRY = RetryPolicy(
    max_attempts=1,
    initial_delay=0.0,
    delay_multiplier=1.0,
    max_delay=0.0,
)

# Attach presets as class attributes for convenience
RetryPolicy.STANDARD = STANDARD  # type: ignore[attr-defined]
RetryPolicy.AGGRESSIVE = AGGRESSIVE  # type: ignore[attr-defined]
RetryPolicy.CONSERVATIVE = CONSERVATIVE  # type: ignore[attr-defined]
RetryPolicy.NO_RETRY = NO_RETRY  # type: ignore[attr-defined]


@dataclass
class RetryResult:
    """Outcome of a retried operation.

    Attributes:
        success: Whether the operation ultimately succeeded.
        result: Return value on success, None on failure.
        attempts: Total number of attempts made.
        total_time: Wall-clock seconds spent (including delays).
        last_error: The last error encountered (None on first-attempt success).
    """

    success: bool
    result: Any = None
    attempts: int = 1
    total_time: float = 0.0
    last_error: NaturoError | None = None


def execute_with_retry(
    fn: Callable[..., Any],
    policy: RetryPolicy | None = None,
    *args: Any,
    **kwargs: Any,
) -> RetryResult:
    """Execute *fn* with retry logic according to *policy*.

    Args:
        fn: Callable to execute.
        policy: Retry policy. Defaults to STANDARD.
        *args: Positional arguments forwarded to *fn*.
        **kwargs: Keyword arguments forwarded to *fn*.

    Returns:
        RetryResult with the outcome.
    """
    if policy is None:
        policy = STANDARD

    start = time.monotonic()
    last_error: NaturoError | None = None

    for attempt in range(policy.max_attempts):
        try:
            result = fn(*args, **kwargs)
            return RetryResult(
                success=True,
                result=result,
                attempts=attempt + 1,
                total_time=time.monotonic() - start,
                last_error=last_error,
            )
        except NaturoError as exc:
            last_error = exc
            if attempt + 1 >= policy.max_attempts:
                break
            if not policy.is_retryable(exc):
                break
            delay = policy.get_delay(attempt)
            logger.debug(
                "Retry %d/%d after %.2fs (code=%s): %s",
                attempt + 1, policy.max_attempts, delay, exc.code, exc.message,
            )
            time.sleep(delay)

    return RetryResult(
        success=False,
        result=None,
        attempts=min(attempt + 1, policy.max_attempts),  # type: ignore[possibly-undefined]
        total_time=time.monotonic() - start,
        last_error=last_error,
    )


def with_retry(policy: RetryPolicy | None = None) -> Callable[[F], F]:
    """Decorator that wraps a function with retry logic.

    Args:
        policy: Retry policy. Defaults to STANDARD.

    Example::

        @with_retry(RetryPolicy.AGGRESSIVE)
        def flaky_operation():
            ...
    """
    if policy is None:
        policy = STANDARD

    def decorator(fn: F) -> F:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            result = execute_with_retry(fn, policy, *args, **kwargs)
            if result.success:
                return result.result
            if result.last_error:
                raise result.last_error
            raise NaturoError("Retry exhausted with no error captured")

        return wrapper  # type: ignore[return-value]

    return decorator
