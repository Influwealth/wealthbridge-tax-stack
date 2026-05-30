"""
Caffeine Agent — Claude-powered reasoning layer for WealthBridge Tax Stack.

Wraps the Anthropic Messages API (claude-sonnet-4-6) with tax-domain tools.
Falls back gracefully when ANTHROPIC_API_KEY is not set or the SDK is missing.

Usage:
    agent = CaffeineAgent()
    result = agent.run(messages=[{"role": "user", "content": "What is the tax due for record 1?"}])
"""
import os
from typing import Optional
from tax_capsule.utils.logger import get_logger
from caffeine_agent.tools import TOOL_SCHEMAS

logger = get_logger("CaffeineAgent")

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 1024

SYSTEM_PROMPT = """You are WealthBridge Tax Assistant, an AI expert in US federal and state tax law.
You help accountants, business owners, and tax agents understand their tax obligations,
optimize R&D credits, and navigate IRS forms.

You have access to tools to query the WealthBridge database. Always use tools to fetch
real data before answering factual questions about specific records.

Be concise, accurate, and professional. Cite relevant IRC sections when applicable."""


class CaffeineAgent:
    def __init__(self, api_key: Optional[str] = None, model: str = MODEL):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        self.model = model
        self._client = None

    def _get_client(self):
        if self._client is not None:
            return self._client
        if not self.api_key:
            return None
        try:
            import anthropic
            self._client = anthropic.Anthropic(api_key=self.api_key)
            logger.info(f"Anthropic client initialized, model={self.model}")
            return self._client
        except ImportError:
            logger.warning("anthropic SDK not installed — agent unavailable")
            return None
        except Exception as e:
            logger.warning(f"Anthropic client init failed: {e}")
            return None

    def is_available(self) -> bool:
        return self._get_client() is not None

    def run(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        system: str | None = None,
    ) -> dict:
        """
        Run a single inference turn.

        Returns a dict with:
          response: str — assistant text response
          tool_calls_made: list — any tool calls the model made
          model: str — model used
          status: str — "OK" | "UNAVAILABLE" | "ERROR"
        """
        client = self._get_client()
        if client is None:
            return {
                "response": (
                    "Tax Assistant unavailable: ANTHROPIC_API_KEY not configured. "
                    "Set the ANTHROPIC_API_KEY environment variable to enable AI assistance."
                ),
                "tool_calls_made": [],
                "model": "none",
                "status": "UNAVAILABLE",
            }

        try:
            response = client.messages.create(
                model=self.model,
                max_tokens=MAX_TOKENS,
                system=system or SYSTEM_PROMPT,
                messages=messages,
                tools=tools or TOOL_SCHEMAS,
            )

            tool_calls_made = []
            text_parts = []

            for block in response.content:
                if hasattr(block, "type"):
                    if block.type == "text":
                        text_parts.append(block.text)
                    elif block.type == "tool_use":
                        tool_calls_made.append({
                            "name": block.name,
                            "input": block.input,
                            "id": block.id,
                        })

            logger.info(
                f"Agent response: model={response.model}, "
                f"tool_calls={len(tool_calls_made)}, stop={response.stop_reason}"
            )

            return {
                "response": " ".join(text_parts),
                "tool_calls_made": tool_calls_made,
                "model": response.model,
                "status": "OK",
                "stop_reason": response.stop_reason,
            }

        except Exception as e:
            logger.error(f"Agent inference failed: {e}", exc_info=True)
            return {
                "response": f"Agent error: {str(e)}",
                "tool_calls_made": [],
                "model": self.model,
                "status": "ERROR",
            }
