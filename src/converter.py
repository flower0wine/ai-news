"""
HTML to Markdown converter module.

This module provides functionality to convert HTML content to Markdown format,
which reduces token count when sending content to LLMs.

The converter uses the 'markdownify' library which provides:
    - Simple and reliable conversion
    - Customizable through conversion functions
    - Built on BeautifulSoup for robust parsing
"""

import logging
import re
from typing import Optional

import markdownify
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class HtmlToMarkdownConverter:
    """Converter that transforms HTML content to Markdown format.

    This converter is designed to reduce token count when preparing
    content for LLM processing while maintaining readability.

    Example:
        >>> converter = HtmlToMarkdownConverter()
        >>> markdown = converter.convert("<h1>Title</h1><p>Content</p>")
        >>> print(markdown)
        # Title

        Content
    """

    def __init__(
        self,
        strip_tags: Optional[list[str]] = None,
        ignore_links: bool = False,
        ignore_images: bool = True,
    ) -> None:
        """Initialize the converter with optional configuration.

        Args:
            strip_tags: List of HTML tags to remove during conversion
            ignore_links: Whether to ignore/link conversion (keep URLs as text)
            ignore_images: Whether to ignore image tags (skip images)
        """
        self.strip_tags = strip_tags or [
            "script",
            "style",
            "nav",
            "footer",
            "header",
            "aside",
        ]
        self.ignore_links = ignore_links
        self.ignore_images = ignore_images

    def convert(self, html_content: str) -> str:
        """Convert HTML content to Markdown format.

        Args:
            html_content: Raw HTML string to convert

        Returns:
            Markdown formatted string

        Raises:
            ValueError: If HTML content is empty or None
        """
        if not html_content or not html_content.strip():
            logger.warning("Empty HTML content provided, returning empty string")
            return ""

        logger.info(f"Converting HTML to Markdown ({len(html_content)} chars)")

        try:
            # Extract body content first
            html_content = self._extract_body(html_content)

            # Use markdownify with keyword arguments
            markdown = markdownify.markdownify(
                html_content,
                # Strip these tags entirely
                strip=self.strip_tags,
                # Skip images
                skip_images=self.ignore_images,
                # Use * for bold/italic
                strong_em_symbol=markdownify.ASTERISK,
                # Use # for headings
                heading_style=markdownify.ATX,
            )

            # Clean up excessive whitespace
            markdown = self._cleanup_whitespace(markdown)

            logger.info(f"Converted to Markdown ({len(markdown)} chars)")
            return markdown

        except Exception as e:
            logger.error(f"Error converting HTML to Markdown: {e}")
            # Return original content as fallback if conversion fails
            logger.warning("Returning raw content as fallback")
            return html_content

    def _extract_body(self, html_content: str) -> str:
        """Extract content from the body tag if present.

        Args:
            html_content: Raw HTML string

        Returns:
            HTML content extracted from body, or original content if no body tag
        """
        soup = BeautifulSoup(html_content, "html.parser")
        body = soup.find("body")
        if body:
            logger.info("Extracted content from <body> tag")
            return str(body)
        logger.info("No <body> tag found, using original content")
        return html_content

    @staticmethod
    def _cleanup_whitespace(markdown: str) -> str:
        """Clean up excessive whitespace in Markdown content.

        Args:
            markdown: Markdown string to clean

        Returns:
            Cleaned Markdown string
        """
        # Remove multiple consecutive blank lines (keep max 2)
        lines = markdown.split("\n")
        cleaned_lines: list[str] = []
        blank_count = 0

        for line in lines:
            stripped = line.rstrip()
            if not stripped:
                blank_count += 1
                if blank_count <= 2:
                    cleaned_lines.append("")
            else:
                blank_count = 0
                cleaned_lines.append(stripped)

        # Remove trailing whitespace from each line
        result = "\n".join(cleaned_lines)
        return result.strip()
