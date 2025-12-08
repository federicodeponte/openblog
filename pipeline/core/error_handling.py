"""
Comprehensive Error Handling and Resilience for Blog Generation Pipeline

Provides:
- Error categorization and classification
- Circuit breaker patterns for external services
- Automatic retry logic with exponential backoff
- Graceful degradation strategies
- Error reporting and monitoring
- Recovery mechanisms

Production-grade error handling for 5-30 minute generation processes.
"""

import asyncio
import logging
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Union
from functools import wraps

logger = logging.getLogger(__name__)


class ErrorCategory(Enum):
    """Error categories for classification and handling."""
    TRANSIENT = "transient"           # Temporary issues, retry recommended
    PERMANENT = "permanent"           # Permanent failures, don't retry
    RATE_LIMIT = "rate_limit"        # Rate limiting, retry with backoff
    AUTHENTICATION = "authentication" # Auth issues, manual intervention
    VALIDATION = "validation"         # Input validation errors
    TIMEOUT = "timeout"              # Request timeouts
    EXTERNAL_SERVICE = "external_service"  # External API failures
    INTERNAL = "internal"            # Internal system errors
    UNKNOWN = "unknown"              # Unclassified errors


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"                      # Non-critical, job can continue
    MEDIUM = "medium"                # Important but recoverable
    HIGH = "high"                    # Serious issue, affects quality
    CRITICAL = "critical"            # Fatal error, job must fail


@dataclass
class ErrorContext:
    """Context information for error analysis."""
    error: Exception
    category: ErrorCategory
    severity: ErrorSeverity
    stage: Optional[str] = None
    job_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    retry_count: int = 0
    recoverable: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/storage."""
        return {
            "error_type": type(self.error).__name__,
            "error_message": str(self.error),
            "category": self.category.value,
            "severity": self.severity.value,
            "stage": self.stage,
            "job_id": self.job_id,
            "timestamp": self.timestamp.isoformat(),
            "retry_count": self.retry_count,
            "recoverable": self.recoverable,
            "metadata": self.metadata,
            "traceback": traceback.format_exception(type(self.error), self.error, self.error.__traceback__)
        }


class ErrorClassifier:
    """Classifies errors into categories and severity levels."""
    
    # Error patterns for classification
    TRANSIENT_PATTERNS = [
        "connection",
        "timeout", 
        "503",
        "502",
        "504",
        "temporarily unavailable",
        "network",
        "dns"
    ]
    
    RATE_LIMIT_PATTERNS = [
        "rate limit",
        "429",
        "quota exceeded",
        "too many requests",
        "throttle"
    ]
    
    AUTH_PATTERNS = [
        "401",
        "403",
        "unauthorized",
        "forbidden",
        "authentication",
        "api key",
        "invalid key"
    ]
    
    VALIDATION_PATTERNS = [
        "validation",
        "400",
        "bad request",
        "invalid input",
        "malformed",
        "schema"
    ]
    
    @classmethod
    def classify_error(cls, error: Exception, stage: Optional[str] = None) -> ErrorContext:
        """
        Classify an error into category and severity.
        
        Args:
            error: Exception to classify
            stage: Stage where error occurred
            
        Returns:
            ErrorContext with classification
        """
        error_str = str(error).lower()
        error_type = type(error).__name__.lower()
        
        # Determine category
        category = ErrorCategory.UNKNOWN
        severity = ErrorSeverity.MEDIUM
        recoverable = True
        
        # Authentication errors
        if any(pattern in error_str for pattern in cls.AUTH_PATTERNS):
            category = ErrorCategory.AUTHENTICATION
            severity = ErrorSeverity.CRITICAL
            recoverable = False
        
        # Validation errors
        elif any(pattern in error_str for pattern in cls.VALIDATION_PATTERNS):
            category = ErrorCategory.VALIDATION
            severity = ErrorSeverity.HIGH
            recoverable = False
        
        # Rate limiting
        elif any(pattern in error_str for pattern in cls.RATE_LIMIT_PATTERNS):
            category = ErrorCategory.RATE_LIMIT
            severity = ErrorSeverity.MEDIUM
            recoverable = True
        
        # Transient errors
        elif any(pattern in error_str for pattern in cls.TRANSIENT_PATTERNS):
            category = ErrorCategory.TRANSIENT
            severity = ErrorSeverity.LOW
            recoverable = True
        
        # Timeout errors
        elif "timeout" in error_type or isinstance(error, asyncio.TimeoutError):
            category = ErrorCategory.TIMEOUT
            severity = ErrorSeverity.MEDIUM
            recoverable = True
        
        # External service errors
        elif stage and any(ext in stage for ext in ["gemini", "url_validator", "image"]):
            category = ErrorCategory.EXTERNAL_SERVICE
            severity = ErrorSeverity.MEDIUM
            recoverable = True
        
        # Internal errors
        else:
            category = ErrorCategory.INTERNAL
            severity = ErrorSeverity.HIGH
            recoverable = True
        
        # Adjust severity based on stage criticality
        if stage:
            critical_stages = ["stage_00", "stage_02", "stage_10", "stage_11"]
            if stage in critical_stages and category not in [ErrorCategory.AUTHENTICATION, ErrorCategory.VALIDATION]:
                severity = ErrorSeverity.HIGH
        
        return ErrorContext(
            error=error,
            category=category,
            severity=severity,
            stage=stage,
            recoverable=recoverable
        )


class CircuitBreaker:
    """
    Circuit breaker for external service calls.
    
    Prevents cascading failures by temporarily blocking calls to failing services.
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception
    ):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before trying again
            expected_exception: Exception type that triggers circuit
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open
        
    def __call__(self, func):
        """Decorator to wrap functions with circuit breaker."""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if self.state == "open":
                # Check if enough time has passed to try again
                if time.time() - self.last_failure_time < self.recovery_timeout:
                    raise Exception(f"Circuit breaker open for {func.__name__}")
                else:
                    self.state = "half-open"
            
            try:
                result = await func(*args, **kwargs)
                
                # Success - reset circuit
                if self.state == "half-open":
                    self.state = "closed"
                    self.failure_count = 0
                    logger.info(f"Circuit breaker closed for {func.__name__}")
                
                return result
                
            except self.expected_exception as e:
                self.failure_count += 1
                self.last_failure_time = time.time()
                
                if self.failure_count >= self.failure_threshold:
                    self.state = "open"
                    logger.warning(
                        f"Circuit breaker opened for {func.__name__} "
                        f"after {self.failure_count} failures"
                    )
                
                raise e
        
        return wrapper


class RetryConfig:
    """Configuration for retry logic."""
    
    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        backoff_multiplier: float = 2.0,
        max_delay: float = 60.0,
        jitter: bool = True
    ):
        """
        Initialize retry configuration.
        
        Args:
            max_retries: Maximum number of retry attempts
            initial_delay: Initial delay in seconds
            backoff_multiplier: Multiplier for exponential backoff
            max_delay: Maximum delay between retries
            jitter: Add random jitter to prevent thundering herd
        """
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.backoff_multiplier = backoff_multiplier
        self.max_delay = max_delay
        self.jitter = jitter


async def retry_with_backoff(
    func: Callable,
    config: RetryConfig,
    error_classifier: ErrorClassifier,
    stage: Optional[str] = None,
    **kwargs
) -> Any:
    """
    Execute function with retry logic and exponential backoff.
    
    Args:
        func: Async function to execute
        config: Retry configuration
        error_classifier: Error classifier for retry decisions
        stage: Stage name for error context
        **kwargs: Arguments to pass to func
        
    Returns:
        Function result
        
    Raises:
        Exception: If all retries exhausted
    """
    last_error = None
    delay = config.initial_delay
    
    for attempt in range(config.max_retries + 1):  # +1 for initial attempt
        try:
            if attempt > 0:
                logger.info(f"Retry attempt {attempt}/{config.max_retries} for {func.__name__}")
            
            return await func(**kwargs)
            
        except Exception as e:
            last_error = e
            error_context = error_classifier.classify_error(e, stage)
            
            # Don't retry non-recoverable errors
            if not error_context.recoverable:
                logger.error(f"Non-recoverable error in {func.__name__}: {e}")
                raise e
            
            # Don't retry on last attempt
            if attempt >= config.max_retries:
                logger.error(f"All retries exhausted for {func.__name__}: {e}")
                break
            
            # Calculate delay with jitter
            actual_delay = delay
            if config.jitter:
                import random
                actual_delay *= (0.5 + random.random() * 0.5)  # 50-100% of delay
            
            logger.warning(
                f"Attempt {attempt + 1} failed for {func.__name__}: {e}. "
                f"Retrying in {actual_delay:.1f}s..."
            )
            
            await asyncio.sleep(actual_delay)
            delay = min(delay * config.backoff_multiplier, config.max_delay)
    
    # All retries failed
    raise last_error


class ErrorReporter:
    """Centralized error reporting and monitoring."""
    
    def __init__(self):
        """Initialize error reporter."""
        self.error_counts: Dict[str, int] = {}
        self.last_errors: List[ErrorContext] = []
        self.max_error_history = 100
        
    def report_error(self, error_context: ErrorContext) -> None:
        """
        Report an error for monitoring and analysis.
        
        Args:
            error_context: Error context with classification
        """
        # Update error counts
        error_key = f"{error_context.category.value}:{error_context.stage or 'unknown'}"
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
        
        # Add to error history
        self.last_errors.append(error_context)
        if len(self.last_errors) > self.max_error_history:
            self.last_errors.pop(0)
        
        # Log error with structured data
        logger.error(
            f"Error reported: {error_context.category.value} "
            f"({error_context.severity.value}) in {error_context.stage}: "
            f"{error_context.error}",
            extra={"error_context": error_context.to_dict()}
        )
        
        # Alert on critical errors
        if error_context.severity == ErrorSeverity.CRITICAL:
            self._send_alert(error_context)
    
    def _send_alert(self, error_context: ErrorContext) -> None:
        """Send alert for critical errors."""
        # In production, this would send to monitoring service
        logger.critical(
            f"🚨 CRITICAL ERROR ALERT: {error_context.error} "
            f"in job {error_context.job_id}"
        )
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get error summary for monitoring."""
        return {
            "total_errors": len(self.last_errors),
            "error_counts": self.error_counts,
            "recent_errors": [
                {
                    "timestamp": err.timestamp.isoformat(),
                    "category": err.category.value,
                    "severity": err.severity.value,
                    "stage": err.stage,
                    "message": str(err.error)[:100]
                }
                for err in self.last_errors[-10:]  # Last 10 errors
            ]
        }


class GracefulDegradation:
    """Strategies for graceful degradation when services fail."""
    
    @staticmethod
    def mock_image_generation() -> str:
        """Fallback when image generation fails."""
        return "https://via.placeholder.com/1200x630/2563eb/ffffff?text=Blog+Article+Image"
    
    @staticmethod
    def fallback_citation(title: str) -> str:
        """Fallback citation when validation fails."""
        return f"https://www.google.com/search?q={title.replace(' ', '+')}"
    
    @staticmethod
    def simple_internal_links(keywords: List[str], base_url: str) -> List[Dict[str, str]]:
        """Simple internal link generation when advanced fails."""
        return [
            {
                "url": f"{base_url}/blog/{keyword.lower().replace(' ', '-')}",
                "text": keyword.title(),
                "description": f"Learn more about {keyword}"
            }
            for keyword in keywords[:3]
        ]
    
    @staticmethod
    def basic_meta_description(headline: str, content: str) -> str:
        """Generate basic meta description when AI fails."""
        # Extract first sentence from content
        sentences = content.split('. ')
        first_sentence = sentences[0] if sentences else headline
        
        # Truncate to meta description length
        meta_desc = first_sentence[:150]
        if len(first_sentence) > 150:
            meta_desc = meta_desc.rsplit(' ', 1)[0] + "..."
        
        return meta_desc


# Global error reporter instance
error_reporter = ErrorReporter()
error_classifier = ErrorClassifier()

# Predefined retry configurations
RETRY_CONFIGS = {
    "api_calls": RetryConfig(max_retries=3, initial_delay=2.0, max_delay=30.0),
    "url_validation": RetryConfig(max_retries=2, initial_delay=1.0, max_delay=10.0),
    "image_generation": RetryConfig(max_retries=2, initial_delay=5.0, max_delay=60.0),
    "critical_operations": RetryConfig(max_retries=5, initial_delay=1.0, max_delay=120.0),
}

# Circuit breakers for external services
# NOTE: Short recovery timeouts for serverless deployments (containers get recycled)
circuit_breakers = {
    "gemini_api": CircuitBreaker(failure_threshold=5, recovery_timeout=30),  # 30 seconds
    "image_api": CircuitBreaker(failure_threshold=3, recovery_timeout=30),
    "url_validation": CircuitBreaker(failure_threshold=10, recovery_timeout=15),
}


def with_error_handling(
    stage: str,
    retry_config: Optional[RetryConfig] = None,
    circuit_breaker: Optional[CircuitBreaker] = None,
    fallback: Optional[Callable] = None
):
    """
    Decorator for comprehensive error handling.
    
    Args:
        stage: Stage name for error reporting
        retry_config: Retry configuration
        circuit_breaker: Circuit breaker to use
        fallback: Fallback function if all else fails
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                # Apply circuit breaker if provided
                if circuit_breaker:
                    func_with_breaker = circuit_breaker(func)
                    actual_func = func_with_breaker
                else:
                    actual_func = func
                
                # Apply retry logic if provided
                if retry_config:
                    # Create a wrapper function that handles both args and kwargs
                    async def func_wrapper(**kwargs_only):
                        return await actual_func(*args, **kwargs_only)
                    
                    # Remove stage from kwargs to avoid duplicate parameter
                    retry_kwargs = kwargs.copy()
                    retry_kwargs.pop('stage', None)
                    
                    return await retry_with_backoff(
                        func_wrapper,
                        retry_config,
                        error_classifier,
                        stage=stage,
                        **retry_kwargs
                    )
                else:
                    return await actual_func(*args, **kwargs)
                
            except Exception as e:
                # Classify and report error
                error_context = error_classifier.classify_error(e, stage)
                error_context.job_id = kwargs.get('job_id') or getattr(args[0], 'job_id', None) if args else None
                
                error_reporter.report_error(error_context)
                
                # Try fallback if available
                if fallback and error_context.recoverable:
                    logger.warning(f"Using fallback for {func.__name__} after error: {e}")
                    try:
                        return fallback(*args, **kwargs)
                    except Exception as fallback_error:
                        logger.error(f"Fallback also failed: {fallback_error}")
                
                # Re-raise the original error
                raise e
        
        return wrapper
    return decorator


# Convenience decorators for common patterns
def with_api_retry(stage: str):
    """Decorator for API calls with standard retry logic."""
    return with_error_handling(
        stage=stage,
        retry_config=RETRY_CONFIGS["api_calls"],
        circuit_breaker=circuit_breakers.get("gemini_api")
    )


def with_url_validation_retry(stage: str):
    """Decorator for URL validation with retry logic."""
    return with_error_handling(
        stage=stage,
        retry_config=RETRY_CONFIGS["url_validation"],
        circuit_breaker=circuit_breakers.get("url_validation")
    )


def with_image_fallback(stage: str):
    """Decorator for image generation with fallback."""
    return with_error_handling(
        stage=stage,
        retry_config=RETRY_CONFIGS["image_generation"],
        circuit_breaker=circuit_breakers.get("image_api"),
        fallback=lambda *args, **kwargs: GracefulDegradation.mock_image_generation()  # Return string URL directly, not dict
    )