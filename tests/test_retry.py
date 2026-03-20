"""Tests for naturo.retry — retry policies, exponential backoff, retryable/non-retryable."""
import time
import pytest
from naturo.retry import (
    RetryPolicy, RetryResult, execute_with_retry, with_retry,
    STANDARD, AGGRESSIVE, CONSERVATIVE, NO_RETRY,
)
from naturo.errors import (
    NaturoError, ErrorCode, CaptureFailedError,
    InvalidInputError, TimeoutError, InteractionFailedError,
)


class TestRetryPolicy:
    def test_default_values(self):
        p = RetryPolicy()
        assert p.max_attempts == 3
        assert p.initial_delay == 0.1
        assert p.delay_multiplier == 2.0
        assert p.max_delay == 5.0
        assert ErrorCode.TIMEOUT in p.retryable_codes

    def test_presets_exist(self):
        assert RetryPolicy.STANDARD is STANDARD
        assert RetryPolicy.AGGRESSIVE is AGGRESSIVE
        assert RetryPolicy.CONSERVATIVE is CONSERVATIVE
        assert RetryPolicy.NO_RETRY is NO_RETRY

    def test_standard_preset(self):
        p = STANDARD
        assert p.max_attempts == 3
        assert p.initial_delay == 0.1

    def test_aggressive_preset(self):
        p = AGGRESSIVE
        assert p.max_attempts == 5
        assert p.initial_delay == 0.05

    def test_conservative_preset(self):
        p = CONSERVATIVE
        assert p.max_attempts == 2
        assert p.initial_delay == 0.5

    def test_no_retry_preset(self):
        p = NO_RETRY
        assert p.max_attempts == 1

    def test_is_retryable_recoverable(self):
        p = RetryPolicy()
        err = CaptureFailedError("test")
        assert p.is_retryable(err) is True

    def test_is_retryable_non_recoverable(self):
        p = RetryPolicy()
        err = InvalidInputError("test")
        assert p.is_retryable(err) is False

    def test_is_retryable_wrong_code(self):
        p = RetryPolicy()
        err = NaturoError("test", code="NOT_IN_SET", is_recoverable=True)
        assert p.is_retryable(err) is False

    def test_get_delay_exponential(self):
        p = RetryPolicy(initial_delay=0.1, delay_multiplier=2.0, max_delay=10.0)
        assert p.get_delay(0) == pytest.approx(0.1)
        assert p.get_delay(1) == pytest.approx(0.2)
        assert p.get_delay(2) == pytest.approx(0.4)
        assert p.get_delay(3) == pytest.approx(0.8)

    def test_get_delay_capped(self):
        p = RetryPolicy(initial_delay=1.0, delay_multiplier=10.0, max_delay=5.0)
        assert p.get_delay(0) == 1.0
        assert p.get_delay(1) == 5.0  # capped
        assert p.get_delay(5) == 5.0  # capped


class TestExecuteWithRetry:
    def test_success_first_try(self):
        result = execute_with_retry(lambda: 42)
        assert result.success is True
        assert result.result == 42
        assert result.attempts == 1
        assert result.last_error is None

    def test_success_after_retries(self):
        counter = [0]

        def flaky():
            counter[0] += 1
            if counter[0] < 3:
                raise CaptureFailedError("flaky")
            return "ok"

        policy = RetryPolicy(max_attempts=5, initial_delay=0.01, delay_multiplier=1.0)
        result = execute_with_retry(flaky, policy)
        assert result.success is True
        assert result.result == "ok"
        assert result.attempts == 3

    def test_all_retries_fail(self):
        def always_fails():
            raise CaptureFailedError("always fails")

        policy = RetryPolicy(max_attempts=3, initial_delay=0.01, delay_multiplier=1.0)
        result = execute_with_retry(always_fails, policy)
        assert result.success is False
        assert result.result is None
        assert result.attempts == 3
        assert isinstance(result.last_error, CaptureFailedError)

    def test_non_retryable_stops_immediately(self):
        counter = [0]

        def non_retryable():
            counter[0] += 1
            raise InvalidInputError("bad input")

        policy = RetryPolicy(max_attempts=5, initial_delay=0.01)
        result = execute_with_retry(non_retryable, policy)
        assert result.success is False
        assert result.attempts == 1  # stopped immediately
        assert counter[0] == 1

    def test_no_retry_policy(self):
        counter = [0]

        def fail():
            counter[0] += 1
            raise CaptureFailedError("fail")

        result = execute_with_retry(fail, NO_RETRY)
        assert result.success is False
        assert counter[0] == 1

    def test_total_time_tracked(self):
        def slow():
            raise TimeoutError("slow", timeout=1.0)

        policy = RetryPolicy(max_attempts=2, initial_delay=0.05, delay_multiplier=1.0)
        result = execute_with_retry(slow, policy)
        assert result.total_time >= 0.04  # at least one delay

    def test_default_policy_used(self):
        result = execute_with_retry(lambda: "default")
        assert result.success is True
        assert result.result == "default"


class TestWithRetryDecorator:
    def test_decorator_success(self):
        @with_retry(RetryPolicy(max_attempts=3, initial_delay=0.01))
        def good():
            return "success"

        assert good() == "success"

    def test_decorator_retries_then_succeeds(self):
        counter = [0]

        @with_retry(RetryPolicy(max_attempts=3, initial_delay=0.01, delay_multiplier=1.0))
        def flaky():
            counter[0] += 1
            if counter[0] < 2:
                raise InteractionFailedError("flaky")
            return "recovered"

        assert flaky() == "recovered"
        assert counter[0] == 2

    def test_decorator_raises_on_exhaustion(self):
        @with_retry(RetryPolicy(max_attempts=2, initial_delay=0.01, delay_multiplier=1.0))
        def always_fail():
            raise CaptureFailedError("nope")

        with pytest.raises(CaptureFailedError):
            always_fail()

    def test_decorator_default_policy(self):
        @with_retry()
        def ok():
            return 123

        assert ok() == 123

    def test_decorator_preserves_function_name(self):
        @with_retry()
        def my_function():
            """My docstring."""
            pass

        assert my_function.__name__ == "my_function"
        assert my_function.__doc__ == "My docstring."
