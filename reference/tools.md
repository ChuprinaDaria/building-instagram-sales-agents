# Tools and MCP servers

## One tool

- One job. If the description needs "and", split it.
- Strict input schema. Optional filter = `X | None`, still listed as required.
- Output is structured JSON, small, only what the LLM needs to decide or to reference.
- Errors are structured: `{"error": "not_found", "hint": "no product matches 'blue coat'"}`. Never a stack trace, never an empty string.
- Unknown input is returned, not guessed: `{"unknown_terms": ["khaki-beige"]}`.
- The LLM sees refs like `№3`. Code keeps the map `№3 → product_id`. Raw ids, SKUs, UUIDs never reach the LLM.

## Description = the real prompt

The tool description is read every turn. Write it like docs for a new colleague: what it returns, when to call it, one example call. No business branching inside descriptions either.

## MCP server per domain

For multi-task agents, bundle related tools into one MCP server per domain (catalogue, vision, CRM, memory). Benefits: reuse across agents, isolation (vision server without network or secrets), independent deploy and tests.

Rules:
- Each server has its own tests on recorded inputs.
- The agent loop knows only the tool names and schemas, not server internals.
- Tenant/customer id is passed by the agent code, never chosen by the LLM.

## Loop without a framework

```python
def run_turn(client, messages, tools, handlers, max_steps: int):
    for step in range(max_steps):
        resp = client.call(messages=messages, tools=tools)   # provider SDK
        journal.step(step, resp)                             # tokens, cost, ms
        if not resp.tool_calls:
            return resp.output                               # strict Answer
        for call in resp.tool_calls:
            result = handlers[call.name](**call.args)        # validated by schema
            journal.tool(call, result)
            messages.append(tool_result(call, result))
    raise StepLimit(max_steps)                               # limit is actually wired
```

`max_steps` is passed in and used (rule 13).
