"""
API Serializers for Request/Response handling
"""
from rest_framework import serializers


class ChatRequestSerializer(serializers.Serializer):
    """
    Request serializer for the chat endpoint.
    """
    message = serializers.CharField(
        required=True,
        max_length=2000,
        help_text="Natural language query from the customer"
    )
    session_id = serializers.CharField(
        required=False,
        max_length=100,
        help_text="Session ID for conversation continuity (optional, auto-generated if not provided)"
    )
    user_id = serializers.CharField(
        required=False,
        max_length=100,
        allow_null=True,
        help_text="User ID if customer is authenticated"
    )
    include_debug = serializers.BooleanField(
        required=False,
        default=False,
        help_text="Include debug information in response"
    )


class EntitySerializer(serializers.Serializer):
    """
    Serializer for extracted entities.
    """
    entity_type = serializers.CharField()
    value = serializers.CharField()
    confidence = serializers.FloatField()


class AgentResultSerializer(serializers.Serializer):
    """
    Serializer for individual agent results.
    """
    agent_name = serializers.CharField()
    success = serializers.BooleanField()
    data = serializers.JSONField()
    sql_query = serializers.CharField(allow_null=True)
    error = serializers.CharField(allow_null=True)
    execution_time_ms = serializers.IntegerField()


class ExecutionDetailsSerializer(serializers.Serializer):
    """
    Serializer for execution details.
    """
    agent_results = AgentResultSerializer(many=True)
    execution_time = serializers.DictField()
    entities_found = EntitySerializer(many=True)


class ChatResponseSerializer(serializers.Serializer):
    """
    Response serializer for the chat endpoint.
    """
    response = serializers.CharField(help_text="Natural language response to the customer")
    session_id = serializers.CharField(help_text="Session ID for future messages")
    agents_used = serializers.ListField(
        child=serializers.CharField(),
        help_text="List of agents that were consulted"
    )
    success = serializers.BooleanField(help_text="Whether the query was processed successfully")
    intent = serializers.CharField(allow_null=True, help_text="Detected intent")
    intent_confidence = serializers.FloatField(help_text="Confidence in intent detection")
    
    # Optional debug info
    execution_details = ExecutionDetailsSerializer(required=False)
    error = serializers.CharField(allow_null=True, required=False)


class DirectQueryRequestSerializer(serializers.Serializer):
    """
    Request serializer for direct agent queries.
    """
    agent = serializers.ChoiceField(
        choices=['shopcore', 'shipstream', 'payguard', 'caredesk'],
        help_text="Target agent to query"
    )
    query = serializers.CharField(
        max_length=2000,
        help_text="Natural language query for the agent"
    )
    context = serializers.DictField(
        required=False,
        default=dict,
        help_text="Additional context (e.g., user_id, order_id)"
    )


class DirectQueryResponseSerializer(serializers.Serializer):
    """
    Response serializer for direct agent queries.
    """
    agent = serializers.CharField()
    success = serializers.BooleanField()
    data = serializers.JSONField()
    sql_query = serializers.CharField(allow_null=True)
    error = serializers.CharField(allow_null=True)
    execution_time_ms = serializers.IntegerField()


class HealthCheckSerializer(serializers.Serializer):
    """
    Response serializer for health check.
    """
    status = serializers.CharField()
    version = serializers.CharField()
    database = serializers.CharField()
    agents = serializers.DictField()


class ConversationHistorySerializer(serializers.Serializer):
    """
    Serializer for conversation history items.
    """
    role = serializers.CharField()
    content = serializers.CharField()
    timestamp = serializers.DateTimeField()
    agents_used = serializers.ListField(child=serializers.CharField(), required=False)
