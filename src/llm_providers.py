import os
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from enum import Enum
import openai
import anthropic
from google.generativeai import GenerativeModel
import google.generativeai as genai

logger = logging.getLogger(__name__)

class LLMProvider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"

class BaseLLMClient(ABC):
    """Abstract base class for LLM providers"""
    
    @abstractmethod
    async def chat_completion(
        self, 
        messages: List[Dict[str, str]], 
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = None,
        stream: bool = False,
        **kwargs
    ) -> Any:
        """Generate chat completion"""
        pass
    
    @abstractmethod
    def validate_api_key(self, api_key: str) -> bool:
        """Validate API key"""
        pass

class OpenAIClient(BaseLLMClient):
    """OpenAI API client implementation"""
    
    def __init__(self, api_key: str = None, base_url: str = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
        
        if base_url:
            self.client = openai.OpenAI(
                api_key=self.api_key,
                base_url=base_url
            )
        else:
            self.client = openai.OpenAI(
                api_key=self.api_key
            )
        self.default_model = "gpt-4o-mini"
    
    async def chat_completion(
        self, 
        messages: List[Dict[str, str]], 
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = None,
        stream: bool = False,
        **kwargs
    ) -> Any:
        """Generate OpenAI chat completion"""
        try:
            response = self.client.chat.completions.create(
                model=model or self.default_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=stream,
                **kwargs
            )
            return response
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise
    
    def validate_api_key(self, api_key: str) -> bool:
        """Validate OpenAI API key"""
        try:
            test_client = openai.OpenAI(api_key=api_key)
            # Make a minimal API call to test the key
            test_client.models.list()
            return True
        except Exception as e:
            logger.warning(f"Invalid OpenAI API key: {e}")
            return False

class AnthropicClient(BaseLLMClient):
    """Anthropic Claude API client implementation"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("Anthropic API key is required")
        
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.default_model = "claude-3-haiku-20240307"
    
    async def chat_completion(
        self, 
        messages: List[Dict[str, str]], 
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        stream: bool = False,
        **kwargs
    ) -> Any:
        """Generate Anthropic chat completion"""
        try:
            # Convert OpenAI format messages to Anthropic format
            system_message = ""
            claude_messages = []
            
            for msg in messages:
                if msg["role"] == "system":
                    system_message = msg["content"]
                else:
                    claude_messages.append(msg)
            
            response = self.client.messages.create(
                model=model or self.default_model,
                messages=claude_messages,
                system=system_message,
                temperature=temperature,
                max_tokens=max_tokens or 1024,
                stream=stream,
                **kwargs
            )
            return response
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            raise
    
    def validate_api_key(self, api_key: str) -> bool:
        """Validate Anthropic API key"""
        try:
            test_client = anthropic.Anthropic(api_key=api_key)
            # Make a minimal API call to test the key
            test_client.messages.create(
                model=self.default_model,
                max_tokens=10,
                messages=[{"role": "user", "content": "Hi"}]
            )
            return True
        except Exception as e:
            logger.warning(f"Invalid Anthropic API key: {e}")
            return False

class GoogleClient(BaseLLMClient):
    """Google Gemini API client implementation"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("Google API key is required")
        
        genai.configure(api_key=self.api_key)
        self.default_model = "gemini-pro"
    
    async def chat_completion(
        self, 
        messages: List[Dict[str, str]], 
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = None,
        stream: bool = False,
        **kwargs
    ) -> Any:
        """Generate Google Gemini chat completion"""
        try:
            model_instance = GenerativeModel(model or self.default_model)
            
            # Convert messages to Gemini format
            chat_history = []
            current_content = ""
            
            for msg in messages:
                if msg["role"] == "system":
                    # System messages can be prepended to the first user message
                    current_content = f"{msg['content']}\n\n"
                elif msg["role"] == "user":
                    current_content += msg["content"]
                    chat_history.append({"role": "user", "parts": [current_content]})
                    current_content = ""
                elif msg["role"] == "assistant":
                    chat_history.append({"role": "model", "parts": [msg["content"]]})
            
            chat = model_instance.start_chat(history=chat_history[:-1] if chat_history else [])
            
            # Get the last user message
            last_message = chat_history[-1]["parts"][0] if chat_history else "Hello"
            
            generation_config = {
                "temperature": temperature,
            }
            if max_tokens:
                generation_config["max_output_tokens"] = max_tokens
            
            if stream:
                response = chat.send_message(
                    last_message, 
                    generation_config=generation_config,
                    stream=True
                )
            else:
                response = chat.send_message(
                    last_message,
                    generation_config=generation_config
                )
            
            return response
        except Exception as e:
            logger.error(f"Google API error: {e}")
            raise
    
    def validate_api_key(self, api_key: str) -> bool:
        """Validate Google API key"""
        try:
            genai.configure(api_key=api_key)
            model = GenerativeModel("gemini-pro")
            model.generate_content("Hi", generation_config={"max_output_tokens": 10})
            return True
        except Exception as e:
            logger.warning(f"Invalid Google API key: {e}")
            return False

class LLMManager:
    """Manager for multiple LLM providers"""
    
    def __init__(self):
        self.providers: Dict[LLMProvider, BaseLLMClient] = {}
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Initialize available providers based on environment variables"""
        # OpenAI
        if os.getenv("OPENAI_API_KEY"):
            try:
                self.providers[LLMProvider.OPENAI] = OpenAIClient()
                logger.info("OpenAI provider initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI provider: {e}")
        
        # Anthropic
        if os.getenv("ANTHROPIC_API_KEY"):
            try:
                self.providers[LLMProvider.ANTHROPIC] = AnthropicClient()
                logger.info("Anthropic provider initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Anthropic provider: {e}")
        
        # Google
        if os.getenv("GOOGLE_API_KEY"):
            try:
                self.providers[LLMProvider.GOOGLE] = GoogleClient()
                logger.info("Google provider initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Google provider: {e}")
    
    def add_provider(self, provider_type: LLMProvider, api_key: str) -> bool:
        """Add a provider with API key"""
        try:
            if provider_type == LLMProvider.OPENAI:
                self.providers[provider_type] = OpenAIClient(api_key=api_key)
            elif provider_type == LLMProvider.ANTHROPIC:
                self.providers[provider_type] = AnthropicClient(api_key=api_key)
            elif provider_type == LLMProvider.GOOGLE:
                self.providers[provider_type] = GoogleClient(api_key=api_key)
            else:
                raise ValueError(f"Unknown provider type: {provider_type}")
            
            logger.info(f"Added {provider_type.value} provider")
            return True
        except Exception as e:
            logger.error(f"Failed to add {provider_type.value} provider: {e}")
            return False
    
    def get_provider(self, provider_type: LLMProvider) -> Optional[BaseLLMClient]:
        """Get a specific provider"""
        return self.providers.get(provider_type)
    
    def get_default_provider(self) -> Optional[BaseLLMClient]:
        """Get the default provider (OpenAI if available, otherwise first available)"""
        if LLMProvider.OPENAI in self.providers:
            return self.providers[LLMProvider.OPENAI]
        elif self.providers:
            return next(iter(self.providers.values()))
        return None
    
    def list_providers(self) -> List[LLMProvider]:
        """List available providers"""
        return list(self.providers.keys())
    
    async def chat_completion(
        self, 
        messages: List[Dict[str, str]],
        provider: LLMProvider = None,
        **kwargs
    ) -> Any:
        """Generate chat completion using specified or default provider"""
        if provider and provider in self.providers:
            client = self.providers[provider]
        else:
            client = self.get_default_provider()
        
        if not client:
            raise ValueError("No LLM provider available")
        
        return await client.chat_completion(messages, **kwargs)

# Global LLM manager instance
llm_manager = LLMManager()

def get_llm_manager() -> LLMManager:
    """Get the global LLM manager instance"""
    return llm_manager

def get_default_llm_client() -> Optional[BaseLLMClient]:
    """Get the default LLM client"""
    return llm_manager.get_default_provider()