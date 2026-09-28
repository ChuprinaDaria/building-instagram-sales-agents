# Slots and renderer

The LLM never types a fact. It writes a draft with slots; code fills them from the records the tools returned in this turn.

## Answer schema

```python
from typing import Literal
from pydantic import BaseModel

class Extracted(BaseModel):
    phone: str | None
    city: str | None
    size: str | None

class Reply(BaseModel):
    text: str                      # draft with slots: "Price {price:1}, sizes in stock {sizes:1}"
    kind: Literal["answer", "ask", "escalate"]
    mentioned: list[int]           # item refs №N used in text
    options: list[str] | None

class Answer(BaseModel):
    extracted: Extracted
    reply: Reply
```

Use it with the provider's strict structured output (`strict: true`, all fields required, optional = `X | None`).

## Renderer

```python
import re

SLOT = re.compile(r"\{(\w+)(?:\.(\w+))?:(\d+)\}")
TYPED_FACT = re.compile(r"\d{3,}|№\s*\d+|\+?\d[\d\s\-]{8,}")  # price, ref, phone typed by the LLM

class RenderError(Exception):
    pass

def render(text: str, items: dict[int, dict]) -> str:
    if TYPED_FACT.search(SLOT.sub("", text)):
        raise RenderError("LLM typed a fact instead of a slot")

    def fill(m):
        field, case, ref = m.group(1), m.group(2), int(m.group(3))
        item = items.get(ref)
        if item is None:
            raise RenderError(f"unknown ref №{ref}")
        key = f"{field}.{case}" if case else field
        if key not in item:
            raise RenderError(f"no value for {key} of №{ref}")
        return str(item[key])

    return SLOT.sub(fill, text)
```

This single `TYPED_FACT` check is the only regex over LLM text. Anything more semantic goes into the schema (rule 3).

## Turn loop

1. Call the LLM → `Answer`.
2. `render()`. On `RenderError` → one retry with the error text appended as a tool/system note.
3. Second failure → fixed fallback text + escalation card to a human with the draft and the error. Log both.

## Checks

- Unit test: a draft with a typed price raises `RenderError`.
- Unit test: an unknown ref raises `RenderError`.
- Journal: `render_error` count per 100 turns is a daily metric.
