"""In-house MCP server exposing read-only portfolio tools over Streamable HTTP.

The backend's agent connects as a client. ``user_id`` is injected as MCP
request metadata by the backend's ``process_tool_call`` hook  -  the LLM
never sees or submits it.
"""
