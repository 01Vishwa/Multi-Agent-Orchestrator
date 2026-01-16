"""
Custom exceptions for OmniLife Multi-Agent Orchestrator
"""


class OmniLifeException(Exception):
    """Base exception for all OmniLife errors"""
    def __init__(self, message: str, code: str = "OMNILIFE_ERROR"):
        self.message = message
        self.code = code
        super().__init__(self.message)


class AgentException(OmniLifeException):
    """Exception raised by agents during execution"""
    def __init__(self, agent_name: str, message: str):
        self.agent_name = agent_name
        super().__init__(
            message=f"[{agent_name}] {message}",
            code="AGENT_ERROR"
        )


class SQLGenerationException(AgentException):
    """Exception raised when SQL generation fails"""
    def __init__(self, agent_name: str, query: str, reason: str):
        self.query = query
        self.reason = reason
        super().__init__(
            agent_name=agent_name,
            message=f"Failed to generate SQL for query '{query}': {reason}"
        )


class SQLExecutionException(AgentException):
    """Exception raised when SQL execution fails"""
    def __init__(self, agent_name: str, sql: str, error: str):
        self.sql = sql
        self.error = error
        super().__init__(
            agent_name=agent_name,
            message=f"SQL execution failed: {error}"
        )


class OrchestratorException(OmniLifeException):
    """Exception raised by the orchestrator"""
    def __init__(self, message: str, stage: str = "unknown"):
        self.stage = stage
        super().__init__(
            message=f"Orchestrator error at {stage}: {message}",
            code="ORCHESTRATOR_ERROR"
        )


class DependencyResolutionException(OrchestratorException):
    """Exception raised when dependency resolution fails"""
    def __init__(self, message: str, missing_deps: list = None):
        self.missing_deps = missing_deps or []
        super().__init__(message=message, stage="dependency_resolution")


class LLMException(OmniLifeException):
    """Exception raised when LLM calls fail"""
    def __init__(self, message: str, model: str = None):
        self.model = model
        super().__init__(
            message=f"LLM error: {message}",
            code="LLM_ERROR"
        )


class ValidationException(OmniLifeException):
    """Exception raised for validation errors"""
    def __init__(self, message: str, field: str = None):
        self.field = field
        super().__init__(
            message=message,
            code="VALIDATION_ERROR"
        )
