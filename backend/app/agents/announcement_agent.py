import asyncio
import json
import logging
from collections.abc import Mapping
from typing import Any, Protocol

from pydantic import ValidationError

from app.agents.prompts import SYSTEM_PROMPT, build_analysis_material
from app.core.config import Settings
from app.core.exceptions import AnalysisProviderError, AnalysisValidationError
from app.schemas.analysis import (
    AnalysisInput,
    AnnouncementAnalysis,
    GetPriceReactionArguments,
)
from app.schemas.domain import PriceReaction
from app.services.price_service import PriceService

logger = logging.getLogger(__name__)
PRICE_TOOL_NAME = "get_price_reaction"


class ResponsesEndpoint(Protocol):
    async def create(self, **kwargs: Any) -> Any: ...


class OpenAIClient(Protocol):
    responses: ResponsesEndpoint


class AnnouncementAgent:
    def __init__(
        self,
        settings: Settings,
        client: OpenAIClient,
        price_service: PriceService,
    ) -> None:
        self._settings = settings
        self._client = client
        self._price_service = price_service

    async def analyze(self, analysis_input: AnalysisInput) -> AnnouncementAnalysis:
        input_items: list[Any] = [
            {
                "role": "user",
                "content": build_analysis_material(
                    source_json=analysis_input.source.model_dump_json(),
                    pages=[(page.page_number, page.text) for page in analysis_input.pages],
                    warnings=analysis_input.extraction_warnings,
                    announcement_date=analysis_input.announcement_date.isoformat(),
                    max_characters=self._settings.analysis_max_document_chars,
                ),
            }
        ]
        tool_calls_used = 0
        authoritative_price: PriceReaction | None = None

        while True:
            response = await self._create_response(input_items)
            output_items = list(getattr(response, "output", []))
            function_calls = [
                item for item in output_items if getattr(item, "type", None) == "function_call"
            ]
            if not function_calls:
                output_text = getattr(response, "output_text", "")
                analysis = self._validate_final_output(output_text)
                final_price = authoritative_price or PriceReaction(
                    status="unavailable",
                    note="Price-reaction tool was not called; no market movement was inferred",
                )
                return analysis.model_copy(
                    update={
                        "source": analysis_input.source,
                        "price_reaction": final_price,
                    }
                )

            if tool_calls_used + len(function_calls) > self._settings.analysis_max_tool_calls:
                raise AnalysisValidationError("Analysis exceeded the allowed price-tool calls")
            input_items.extend(output_items)
            for tool_call in function_calls:
                authoritative_price = await self._handle_tool_call(tool_call, analysis_input)
                tool_calls_used += 1
                input_items.append(
                    {
                        "type": "function_call_output",
                        "call_id": getattr(tool_call, "call_id", ""),
                        "output": authoritative_price.model_dump_json(),
                    }
                )

    async def _create_response(self, input_items: list[Any]) -> Any:
        try:
            return await asyncio.wait_for(
                self._client.responses.create(
                    model=self._settings.openai_model,
                    instructions=SYSTEM_PROMPT,
                    input=input_items,
                    tools=[_price_tool_schema()],
                    tool_choice="auto",
                    parallel_tool_calls=False,
                    text={
                        "format": {
                            "type": "json_schema",
                            "name": "announcement_analysis",
                            "strict": True,
                            "schema": _strict_schema(AnnouncementAnalysis.model_json_schema()),
                        },
                        "verbosity": "medium",
                    },
                    store=False,
                ),
                timeout=self._settings.analysis_timeout_seconds,
            )
        except TimeoutError as error:
            raise AnalysisProviderError("OpenAI analysis timed out") from error
        except Exception as error:
            logger.exception("OpenAI Responses API call failed")
            raise AnalysisProviderError("OpenAI analysis provider failed") from error

    async def _handle_tool_call(
        self,
        tool_call: Any,
        analysis_input: AnalysisInput,
    ) -> PriceReaction:
        if getattr(tool_call, "name", None) != PRICE_TOOL_NAME:
            raise AnalysisValidationError("The model requested an unsupported tool")
        if not isinstance(getattr(tool_call, "call_id", None), str) or not tool_call.call_id:
            raise AnalysisValidationError("The model returned a malformed tool call")
        try:
            raw_arguments = json.loads(getattr(tool_call, "arguments", ""))
            arguments = GetPriceReactionArguments.model_validate(raw_arguments)
        except (json.JSONDecodeError, ValidationError) as error:
            raise AnalysisValidationError(
                "The model returned invalid price-tool arguments"
            ) from error
        expected_symbol = (
            analysis_input.source.security_code
            if analysis_input.source.exchange == "BSE"
            else analysis_input.source.symbol
        )
        if (
            arguments.symbol != expected_symbol
            or arguments.exchange != analysis_input.source.exchange
            or arguments.announcement_date != analysis_input.announcement_date
        ):
            raise AnalysisValidationError(
                "The model attempted to change authoritative tool metadata"
            )
        return await self._price_service.get_price_reaction(
            arguments.symbol,
            arguments.exchange,
            arguments.announcement_date,
        )

    @staticmethod
    def _validate_final_output(output_text: str) -> AnnouncementAnalysis:
        if not output_text.strip():
            raise AnalysisValidationError("The model returned no final structured analysis")
        try:
            return AnnouncementAnalysis.model_validate_json(output_text)
        except ValidationError as error:
            raise AnalysisValidationError(
                "The model returned an invalid analysis schema"
            ) from error


def _price_tool_schema() -> dict[str, Any]:
    return {
        "type": "function",
        "name": PRICE_TOOL_NAME,
        "description": (
            "Return deterministic previous/next trading-session closes and nearby percentage "
            "reaction. Returns unavailable rather than substituting a ticker or guessing."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": ["string", "null"],
                    "description": "Authoritative NSE symbol or six-digit BSE security code.",
                },
                "exchange": {"type": "string", "enum": ["BSE", "NSE"]},
                "announcement_date": {"type": "string", "format": "date"},
            },
            "required": ["symbol", "exchange", "announcement_date"],
            "additionalProperties": False,
        },
        "strict": True,
    }


def _strict_schema(schema: Mapping[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key, value in schema.items():
        if key == "default":
            continue
        if isinstance(value, Mapping):
            normalized[key] = _strict_schema(value)
        elif isinstance(value, list):
            normalized[key] = [
                _strict_schema(item) if isinstance(item, Mapping) else item for item in value
            ]
        else:
            normalized[key] = value
    if normalized.get("type") == "object" and "properties" in normalized:
        normalized["additionalProperties"] = False
        normalized["required"] = list(normalized["properties"])
    return normalized
