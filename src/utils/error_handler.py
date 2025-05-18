"""
Error handling utilities for data collection services.

This module provides advanced error handling capabilities for data collection services,
including circuit breakers, exponential backoff, and fallback mechanisms.
"""

import os
import time
import json
import random
import logging
import functools
from typing import Any, Callable, Dict, Optional, TypeVar, cast
from datetime import datetime, timedelta

# Type variable for function return type
T = TypeVar('T')

# Configure logger
logger = logging.getLogger(__name__)

class CircuitBreaker:
    """
    Circuit breaker pattern implementation to prevent repeated calls to failing services.
    
    When a service repeatedly fails, the circuit breaker "opens" and prevents further calls
    until a reset timeout has elapsed, after which it allows a test call to see if the service
    has recovered.
    """
    
    def __init__(self, failure_threshold: int = 5, reset_timeout: int = 60):
        """
        Initialize the circuit breaker.
        
        Args:
            failure_threshold: Number of consecutive failures before opening the circuit
            reset_timeout: Time in seconds to wait before allowing a test call
        """
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF-OPEN
    
    def record_failure(self) -> None:
        """Record a failure and potentially open the circuit."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            logger.warning(f"Circuit breaker opened after {self.failure_count} consecutive failures")
    
    def record_success(self) -> None:
        """Record a success and reset the circuit."""
        self.failure_count = 0
        self.state = "CLOSED"
        logger.info("Circuit breaker closed after successful operation")
    
    def allow_request(self) -> bool:
        """
        Determine if a request should be allowed.
        
        Returns:
            bool: True if the request should be allowed, False otherwise
        """
        if self.state == "CLOSED":
            return True
        
        if self.state == "OPEN":
            # Check if reset timeout has elapsed
            if self.last_failure_time and datetime.now() - self.last_failure_time > timedelta(seconds=self.reset_timeout):
                logger.info("Circuit breaker transitioning to HALF-OPEN state")
                self.state = "HALF-OPEN"
                return True
            return False
        
        # HALF-OPEN state allows one test request
        return True


class RetryWithBackoff:
    """
    Implements retry logic with exponential backoff and jitter.
    """
    
    def __init__(
        self, 
        max_retries: int = 3, 
        base_delay: float = 1.0,
        backoff_factor: float = 2.0,
        jitter: bool = True,
        max_delay: float = 60.0
    ):
        """
        Initialize the retry handler.
        
        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Initial delay between retries in seconds
            backoff_factor: Multiplier for the delay after each retry
            jitter: Whether to add randomness to the delay
            max_delay: Maximum delay between retries in seconds
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.backoff_factor = backoff_factor
        self.jitter = jitter
        self.max_delay = max_delay
    
    def get_delay(self, attempt: int) -> float:
        """
        Calculate the delay for a specific retry attempt.
        
        Args:
            attempt: The current retry attempt number (0-based)
            
        Returns:
            float: The delay in seconds before the next retry
        """
        delay = min(self.base_delay * (self.backoff_factor ** attempt), self.max_delay)
        
        if self.jitter:
            # Add jitter (±20%)
            jitter_factor = 1 + random.uniform(-0.2, 0.2)
            delay *= jitter_factor
        
        return delay


class FallbackHandler:
    """
    Provides fallback mechanisms when primary operations fail.
    """
    
    def __init__(
        self,
        use_cached_data: bool = True,
        cache_ttl: int = 3600,
        generate_synthetic_data: bool = False
    ):
        """
        Initialize the fallback handler.
        
        Args:
            use_cached_data: Whether to use cached data as fallback
            cache_ttl: Time-to-live for cached data in seconds
            generate_synthetic_data: Whether to generate synthetic data when no cache is available
        """
        self.use_cached_data = use_cached_data
        self.cache_ttl = cache_ttl
        self.generate_synthetic_data = generate_synthetic_data
        self.cache = {}
    
    def cache_data(self, key: str, data: Any) -> None:
        """
        Cache data for potential future fallback.
        
        Args:
            key: Cache key
            data: Data to cache
        """
        self.cache[key] = {
            'data': data,
            'timestamp': datetime.now()
        }
    
    def get_fallback_data(self, key: str, data_generator: Optional[Callable[[], Any]] = None) -> Optional[Any]:
        """
        Get fallback data when primary operation fails.
        
        Args:
            key: Cache key
            data_generator: Function to generate synthetic data if needed
            
        Returns:
            Any: Fallback data or None if no fallback is available
        """
        # Try to use cached data first
        if self.use_cached_data and key in self.cache:
            cache_entry = self.cache[key]
            cache_age = (datetime.now() - cache_entry['timestamp']).total_seconds()
            
            if cache_age <= self.cache_ttl:
                logger.info(f"Using cached data for {key} (age: {cache_age:.1f}s)")
                return cache_entry['data']
            else:
                logger.info(f"Cached data for {key} expired (age: {cache_age:.1f}s > TTL: {self.cache_ttl}s)")
        
        # Generate synthetic data if enabled and generator is provided
        if self.generate_synthetic_data and data_generator:
            logger.info(f"Generating synthetic data for {key}")
            return data_generator()
        
        return None


def load_error_handling_config() -> Dict[str, Any]:
    """
    Load error handling configuration from test_mode.json.
    
    Returns:
        Dict[str, Any]: Error handling configuration
    """
    # 프로젝트 루트 경로 가져오기
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    config_path = os.environ.get('TEST_CONFIG_PATH', os.path.join(project_root, 'config', 'test_mode.json'))
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Return error handling config or default empty dict
        return config.get('error_handling', {})
    except Exception as e:
        logger.warning(f"Failed to load error handling config: {e}")
        return {}


def with_circuit_breaker(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator to apply circuit breaker pattern to a function.
    
    Args:
        func: Function to wrap with circuit breaker
        
    Returns:
        Callable: Wrapped function
    """
    config = load_error_handling_config()
    cb_config = config.get('circuit_breaker', {})
    
    if not cb_config.get('enabled', False):
        return func
    
    circuit_breaker = CircuitBreaker(
        failure_threshold=cb_config.get('failure_threshold', 5),
        reset_timeout=cb_config.get('reset_timeout', 60)
    )
    
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        if not circuit_breaker.allow_request():
            logger.warning(f"Circuit breaker open, skipping call to {func.__name__}")
            raise RuntimeError(f"Circuit breaker open for {func.__name__}")
        
        try:
            result = func(*args, **kwargs)
            circuit_breaker.record_success()
            return result
        except Exception as e:
            circuit_breaker.record_failure()
            raise e
    
    return wrapper


def with_retry(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator to apply retry with exponential backoff to a function.
    
    Args:
        func: Function to wrap with retry logic
        
    Returns:
        Callable: Wrapped function
    """
    config = load_error_handling_config()
    
    retry_handler = RetryWithBackoff(
        max_retries=int(os.environ.get('MAX_RETRIES', config.get('max_retries', 3))),
        base_delay=float(os.environ.get('RETRY_INTERVAL', config.get('retry_interval', 1.0))),
        backoff_factor=float(config.get('backoff_factor', 2.0)),
        jitter=bool(config.get('jitter', True))
    )
    
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        last_exception = None
        
        for attempt in range(retry_handler.max_retries + 1):
            try:
                if attempt > 0:
                    logger.info(f"Retry attempt {attempt}/{retry_handler.max_retries} for {func.__name__}")
                
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                
                if attempt < retry_handler.max_retries:
                    delay = retry_handler.get_delay(attempt)
                    logger.warning(f"Error in {func.__name__}: {e}. Retrying in {delay:.2f}s...")
                    time.sleep(delay)
                else:
                    logger.error(f"Failed after {retry_handler.max_retries} retries: {e}")
        
        # If we get here, all retries failed
        assert last_exception is not None
        raise last_exception
    
    return wrapper


def with_fallback(fallback_generator: Optional[Callable[..., T]] = None) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator to apply fallback mechanism to a function.
    
    Args:
        fallback_generator: Function to generate fallback data
        
    Returns:
        Callable: Decorator function
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        config = load_error_handling_config()
        fallback_config = config.get('fallback', {})
        
        if not fallback_config.get('enabled', False):
            return func
        
        fallback_handler = FallbackHandler(
            use_cached_data=fallback_config.get('use_cached_data', True),
            cache_ttl=fallback_config.get('cache_ttl', 3600),
            generate_synthetic_data=fallback_config.get('generate_synthetic_data', False)
        )
        
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            # Generate a cache key based on function name and arguments
            key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            
            try:
                result = func(*args, **kwargs)
                # Cache successful result for potential future fallback
                fallback_handler.cache_data(key, result)
                return result
            except Exception as e:
                logger.warning(f"Error in {func.__name__}: {e}. Attempting fallback...")
                
                # Try to get fallback data
                fallback_data = fallback_handler.get_fallback_data(
                    key, 
                    lambda: fallback_generator(*args, **kwargs) if fallback_generator else None
                )
                
                if fallback_data is not None:
                    return cast(T, fallback_data)
                
                # If no fallback is available, re-raise the exception
                raise
        
        return wrapper
    
    return decorator


def robust_operation(
    circuit_breaker: bool = True,
    retry: bool = True,
    fallback: bool = True,
    fallback_generator: Optional[Callable[..., T]] = None
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Combined decorator for robust operations with circuit breaker, retry, and fallback.
    
    Args:
        circuit_breaker: Whether to apply circuit breaker
        retry: Whether to apply retry logic
        fallback: Whether to apply fallback mechanism
        fallback_generator: Function to generate fallback data
        
    Returns:
        Callable: Decorator function
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        wrapped_func = func
        
        # Apply decorators in reverse order (innermost first)
        if fallback:
            wrapped_func = with_fallback(fallback_generator)(wrapped_func)
        
        if retry:
            wrapped_func = with_retry(wrapped_func)
        
        if circuit_breaker:
            wrapped_func = with_circuit_breaker(wrapped_func)
        
        return wrapped_func
    
    return decorator
