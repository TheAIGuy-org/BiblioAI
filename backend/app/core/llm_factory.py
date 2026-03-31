"""
LLM Factory: Central hub for initializing and managing LLM instances.
Uses Azure OpenAI models.
"""
from langchain_openai import AzureChatOpenAI
from langchain_core.language_models.chat_models import BaseChatModel
from app.config import settings


class LLMFactory:
    """Factory for creating configured LLM instances."""
    
    @staticmethod
    def get_gatekeeper_llm() -> BaseChatModel:
        """Get LLM for Scope Gatekeeper (requires zero temperature)."""
        return AzureChatOpenAI(
            azure_deployment=settings.AZURE_OPENAI_MODEL,
            temperature=settings.GATEKEEPER_TEMPERATURE,
            api_key=settings.AZURE_OPENAI_KEY,
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            api_version=settings.AZURE_OPENAI_API_VERSION,
            max_tokens=1000
        )
    
    @staticmethod
    def get_architect_llm() -> BaseChatModel:
        """Get LLM for The Architect (requires reasoning capability)."""
        return AzureChatOpenAI(
            azure_deployment=settings.AZURE_OPENAI_MODEL,
            temperature=settings.ARCHITECT_TEMPERATURE,
            api_key=settings.AZURE_OPENAI_KEY,
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            api_version=settings.AZURE_OPENAI_API_VERSION,
            max_tokens=4000
        )
    
    @staticmethod
    def get_builder_llm() -> BaseChatModel:
        """Get LLM for The Builder (code generation specialist)."""
        return AzureChatOpenAI(
            azure_deployment=settings.AZURE_OPENAI_MODEL,
            temperature=settings.BUILDER_TEMPERATURE,
            api_key=settings.AZURE_OPENAI_KEY,
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            api_version=settings.AZURE_OPENAI_API_VERSION,
            max_tokens=8000
        )
    
    @staticmethod
    def get_auditor_llm() -> BaseChatModel:
        """Get LLM for The Auditor and Syntax Guard (validation and surgical fixes)."""
        return AzureChatOpenAI(
            azure_deployment=settings.AZURE_OPENAI_MODEL,
            temperature=settings.AUDITOR_TEMPERATURE,
            api_key=settings.AZURE_OPENAI_KEY,
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            api_version=settings.AZURE_OPENAI_API_VERSION,
            max_tokens=16000
        )


# Singleton instances
llm_factory = LLMFactory()