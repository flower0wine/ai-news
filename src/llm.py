"""
LLM (Large Language Model) module using Litellm.

This module provides a unified interface for interacting with various LLM providers
through Litellm, currently configured for Volcengine (火山引擎) ARK service.

Features:
    - Unified API for multiple LLM providers
    - Streaming and non-streaming responses
    - Configurable model, temperature, and token limits
    - Automatic retry logic via Litellm

Model Configuration:
    The model is configured via the LLM_MODEL environment variable.
    Format: provider/model-name (e.g., volcengine/ep-xxxx)

Example:
    >>> llm = LLMService()
    >>> response = llm.complete("Hello, how are you?")
    >>> print(response.content)

    # Streaming:
    >>> for chunk in llm.complete_stream("Tell me a story"):
    ...     print(chunk.content, end="")
"""

import os
import logging
from typing import Dict, Any, Optional, Iterator, AsyncIterator

import litellm
from litellm import completion, acompletion
from litellm.main import ModelResponse

from src.config import get_config

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Custom exception for LLM service errors."""

    def __init__(
        self, message: str, original_error: Optional[Exception] = None
    ) -> None:
        """Initialize the exception.

        Args:
            message: Error message
            original_error: Original exception that caused this error
        """
        super().__init__(message)
        self.original_error = original_error


class LLMService:
    """LLM service using Litellm as the unified interface.

    This class provides methods for interacting with LLMs through Litellm,
    with support for Volcengine ARK and other providers.
    """

    def __init__(
        self,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> None:
        """Initialize the LLM service.

        All parameters can be overridden, otherwise config values are used.

        Args:
            model: Model identifier (e.g., volcengine/ep-xxxx). Uses config if None.
            temperature: Sampling temperature. Uses config if None.
            max_tokens: Maximum tokens in response. Uses config if None.
        """
        self.config = get_config()

        # Use provided values or fall back to config
        self.model = model or self.config.llm_model
        self.temperature = (
            temperature if temperature is not None else self.config.llm_temperature
        )
        self.max_tokens = (
            max_tokens if max_tokens is not None else self.config.llm_max_tokens
        )

        # Set API key for Volcengine
        # Litellm checks multiple env vars: DEEPSEEK_API_KEY, ARK_API_KEY
        os.environ["DEEPSEEK_API_KEY"] = self.config.llm_api_key

        # Configure Litellm settings
        litellm.drop_params = True
        litellm.set_verbose = False

        logger.info(f"LLM Service initialized with model: {self.model}")

    def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> ModelResponse:
        """Send a completion request to the LLM (non-streaming).

        Args:
            prompt: User prompt/message
            system_prompt: Optional system prompt
            temperature: Override default temperature
            max_tokens: Override default max_tokens

        Returns:
            ModelResponse object containing the LLM's response

        Raises:
            LLMError: If the request fails
        """
        messages = self._build_messages(prompt, system_prompt)

        try:
            logger.info(f"Sending completion request to {self.model}")

            response = completion(
                model=self.model,
                messages=messages,
                temperature=temperature or self.temperature,
                max_tokens=max_tokens or self.max_tokens,
                stream=False,
            )

            logger.info(f"Completion successful: {response.usage}")
            return response

        except Exception as e:
            logger.error(f"LLM completion failed: {e}")
            raise LLMError(f"Completion failed: {e}", original_error=e) from e

    def complete_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Iterator[ModelResponse]:
        """Send a completion request with streaming response.

        Args:
            prompt: User prompt/message
            system_prompt: Optional system prompt
            temperature: Override default temperature
            max_tokens: Override default max_tokens

        Yields:
            ModelResponse chunks containing partial responses

        Raises:
            LLMError: If the request fails
        """
        messages = self._build_messages(prompt, system_prompt)

        try:
            logger.info(f"Sending streaming request to {self.model}")

            response = completion(
                model=self.model,
                messages=messages,
                temperature=temperature or self.temperature,
                max_tokens=max_tokens or self.max_tokens,
                stream=True,
            )

            for chunk in response:
                yield chunk

        except Exception as e:
            logger.error(f"LLM streaming failed: {e}")
            raise LLMError(f"Streaming failed: {e}", original_error=e) from e

    def summarize_news(
        self,
        markdown_content: str,
        original_url: str,
        subject: str,
    ) -> str:
        """Summarize news content using the LLM.

        This method formats the content and requests a summary in HTML format,
        suitable for email newsletters.

        Args:
            markdown_content: The Markdown content to summarize
            original_url: URL to the original article (will be added to summary)
            subject: Subject line of the campaign

        Returns:
            HTML formatted summary

        Raises:
            LLMError: If summarization fails
        """
        system_prompt = """你是一位热门信息转述者，你知道用户想看的是什么，你会将页面上的所有信息都进行分析总结，并将最优质的内容传达给用户。
# 任务
- 阅读提供的信息，将其翻译为中文并转换为 HTML 格式。
- HTML 使用内置样式进行适当美化排版，让用户阅读起来视觉顺畅。
- 不要过度总结，最大化保留信息内容。
- 如果有消息对应的 URL，应将 URL 与消息对应。

# 用户需求
- 想看最新的消息，不希望信息被遗漏。
- 希望信息干净整洁，易于阅读。
- 用户身份为中文阅读者。

HTML 格式要求：
- 使用语义化 HTML 标签 (<h1>, <h2>, <p>, <ul>, <li>, <a>)。
- 保持 HTML 代码简单，并兼容电子邮件格式。
- 在不同新闻条目之间添加 <hr/> 分隔线。
- 在底部添加一个“阅读更多”链接，指向：{original_url}。
- 使用中文进行展示。
- 输出不少于 8000 token。

请勿包含任何 Markdown 格式 —— 仅输出纯 HTML 代码。"""

        # Replace placeholder with actual URL
        system_prompt = system_prompt.format(original_url=original_url)

        user_prompt = f"""Please summarize the following AI news:

Subject: {subject}

Content:
{markdown_content}

Provide a well-structured HTML summary."""

        try:
            response = self.complete(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=1,
                max_tokens=self.max_tokens,
            )

            content = response.choices[0].message.content.replace("```html", "").replace("```", "")
            logger.info(f"Summarization complete: {len(content)} chars")
            
            with open("output.html", "w", encoding="utf-8") as f:
                f.write(content)

            return content

        except LLMError as e:
            logger.error(f"Failed to summarize news: {e}")
            raise

    def _build_messages(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> list[Dict[str, str]]:
        """Build the messages list for LLM request.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt

        Returns:
            List of message dictionaries
        """
        messages: list[Dict[str, str]] = []

        if system_prompt:
            messages.append(
                {
                    "role": "system",
                    "content": system_prompt,
                }
            )

        messages.append(
            {
                "role": "user",
                "content": prompt,
            }
        )

        return messages
