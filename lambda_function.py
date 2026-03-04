"""
Main Lambda handler for AI News processing.

This module orchestrates the complete workflow:
1. Fetch latest AI news from AlphaSignal API
2. Convert HTML content to Markdown
3. Use LLM to summarize the news content
4. Send the summary via email using Resend

Environment Variables (see src/config.py for full list):
    - DEEPSEEK_API_KEY: API key for Volcengine LLM service
    - LLM_MODEL: Model identifier (e.g., volcengine/ep-xxx)
    - RESEND_API_KEY: API key for Resend email service
    - EMAIL_FROM: Sender email address
    - EMAIL_TO: Recipient email address(es)

Workflow:
    1. Lambda triggered (scheduled or API)
    2. Fetch campaign from AlphaSignal
    3. Convert HTML -> Markdown
    4. Send to LLM for summarization (with HTML output)
    5. Send HTML via Resend to subscribers
    6. Return success/failure status
"""

import json
import logging
import os
from typing import Any, Dict

# Configure logging for CloudWatch
logging.basicConfig(
    level=logging.INFO,
    format='{"time": "%(asctime)s", "level": "%(levelname)s", "module": "%(module)s", "message": "%(message)s"}',
)
logger = logging.getLogger(__name__)

# Import project modules
from src.config import get_config
from src.api_client import AlphaSignalClient, ApiClientError
from src.converter import HtmlToMarkdownConverter
from src.llm import LLMService, LLMError
from src.email_sender import EmailSender, EmailSenderError


def create_response(status_code: int, message: str, data: Any = None) -> Dict[str, Any]:
    """Create a Lambda-compatible HTTP response.

    Args:
        status_code: HTTP status code
        message: Response message
        data: Optional data to include in response body

    Returns:
        Lambda-compatible response dictionary
    """
    body = {"message": message}
    if data:
        body["data"] = data

    return {
        "statusCode": status_code,
        "body": json.dumps(body),
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
    }


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """AWS Lambda handler function.

    This function is the entry point for the Lambda function. It orchestrates
    the complete workflow of fetching news, processing with LLM, and sending emails.

    Args:
        event: Lambda event object (can be from CloudWatch, API Gateway, etc.)
        context: Lambda context object

    Returns:
        Lambda-compatible response dictionary
    """
    # Log Lambda invocation
    logger.info(f"Lambda invoked: {context.function_name}")
    request_id = getattr(context, "request_id", "unknown")
    logger.info(f"Request ID: {request_id}")
    logger.info(f"Event: {json.dumps(event)}")

    try:
        # Initialize configuration (validates required environment variables)
        config = get_config()
        logger.info(f"Configuration loaded: {json.dumps(config.to_dict())}")

        # Step 1: Fetch latest campaign from AlphaSignal
        logger.info("Step 1: Fetching campaign from AlphaSignal...")
        alpha_client = AlphaSignalClient()
        campaign = alpha_client.get_last_campaign()

        campaign_id = campaign.get("_id", "unknown")
        subject = campaign.get("subject", "AI News Update")
        html_content = campaign.get("html", "")

        logger.info(f"Campaign fetched: {campaign_id}, subject: {subject}")

        if not html_content:
            logger.warning("Campaign has no HTML content, skipping processing")
            return create_response(
                200, "No content to process", {"campaign_id": campaign_id}
            )

        # Step 2: Convert HTML to Markdown
        logger.info("Step 2: Converting HTML to Markdown...")
        converter = HtmlToMarkdownConverter(
            ignore_images=True,
            ignore_links=False,
        )
        markdown_content = converter.convert(html_content)

        logger.info(f"Converted to Markdown: {len(markdown_content)} chars")

        # Step 3: Summarize content using LLM
        logger.info("Step 3: Summarizing content with LLM...")
        llm_service = LLMService()

        # The original URL would be from AlphaSignal - using a placeholder
        # In production, this could be extracted from the campaign or configured
        original_url = "https://alphasignal.ai"

        html_summary = llm_service.summarize_news(
            markdown_content=markdown_content,
            original_url=original_url,
            subject=subject,
        )

        logger.info(f"LLM summarization complete: {len(html_summary)} chars")

        # Step 4: Send email via Resend
        logger.info("Step 4: Sending email via Resend...")
        email_sender = EmailSender()

        result = email_sender.send_campaign(
            subject=subject,
            html=html_summary,
        )

        logger.info(f"Email sent successfully: {result}")

        # Return success response
        return create_response(
            200,
            "News processed and email sent successfully",
            {
                "campaign_id": campaign_id,
                "email_result": result,
            },
        )

    # Handle specific error types
    except ApiClientError as e:
        logger.error(f"API client error: {e}")
        return create_response(502, f"External API error: {e}")

    except LLMError as e:
        logger.error(f"LLM error: {e}")
        return create_response(502, f"LLM service error: {e}")

    except EmailSenderError as e:
        logger.error(f"Email sender error: {e}")
        return create_response(502, f"Email service error: {e}")

    except ValueError as e:
        # Configuration errors (missing environment variables)
        logger.error(f"Configuration error: {e}")
        return create_response(500, f"Configuration error: {e}")

    except Exception as e:
        # Unexpected errors - log full traceback
        logger.exception(f"Unexpected error: {e}")
        return create_response(500, f"Internal error: {e}")


def test_workflow() -> Dict[str, Any]:
    """Test function for local development.

    This function can be called locally to test the complete workflow
    without invoking the Lambda function.

    Returns:
        Dictionary containing test results
    """
    logger.info("Starting local workflow test...")

    # Check for test mode environment variable
    test_mode = os.environ.get("TEST_MODE", "false").lower() == "true"

    if not test_mode:
        return {"status": "skipped", "message": "Set TEST_MODE=true to run local test"}

    try:
        result = lambda_handler(
            {},
            type(
                "Context",
                (),
                {"function_name": "test-function", "request_id": "test-123"},
            )(),
        )
        return {"status": "success", "result": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}


if __name__ == "__main__":
    # For local testing
    import sys

    result = test_workflow()
    print(json.dumps(result, indent=2))
    sys.exit(0 if result.get("status") == "success" else 1)
