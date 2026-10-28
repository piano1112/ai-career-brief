"""테스트용 가짜 Claude. 미리 정해 둔 응답을 순서대로 돌려준다."""

from anthropic.types.beta import BetaMessage, BetaTextBlock, BetaToolUseBlock, BetaUsage

from app.llm.client import Final, TextDelta


def text_message(text: str, stop_reason: str = "end_turn") -> BetaMessage:
    return _message([BetaTextBlock(type="text", text=text)], stop_reason)


def tool_message(name: str, tool_input: dict, tool_id: str = "toolu_1") -> BetaMessage:
    block = BetaToolUseBlock(type="tool_use", id=tool_id, name=name, input=tool_input)
    return _message([block], "tool_use")


def _message(content: list, stop_reason: str) -> BetaMessage:
    return BetaMessage(
        id="msg_test",
        type="message",
        role="assistant",
        model="claude-opus-5-5",
        content=content,
        stop_reason=stop_reason,
        stop_sequence=None,
        usage=BetaUsage(input_tokens=10, output_tokens=5),
    )


class FakeLlm:
    def __init__(self, *responses: BetaMessage) -> None:
        self.responses = list(responses)
        self.requests: list[dict] = []  # Claude에 보낸 요청 기록 (검증용)

    def __call__(self, *, purpose, system, messages, tools):
        self.requests.append({"system": system, "messages": messages, "tools": tools})
        message = self.responses.pop(0)
        for block in message.content:
            if block.type == "text":
                yield TextDelta(block.text)
        yield Final(message)
