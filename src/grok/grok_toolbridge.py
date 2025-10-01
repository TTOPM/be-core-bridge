from typing import Dict, Any, Callable

# Generic function-calling style bridge for MCP tools / Concordium checks.
ToolFn = Callable[[Dict[str, Any]], Dict[str, Any]]

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, ToolFn] = {}

    def register(self, name: str, fn: ToolFn):
        self._tools[name] = fn

    def call(self, name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if name not in self._tools:
            raise ValueError(f"tool_missing:{name}")
        return self._tools[name](payload)

# Example built-ins (wire these to your MCP endpoints)
registry = ToolRegistry()

def verify_access(payload: Dict[str, Any]) -> Dict[str, Any]:
    # Call out to your MCP verify endpoint (or local check)
    # Keep it synchronous and return a minimal, signed structure
    return {"tool":"verify_access","compliance_status":"passed"}

def audit(payload: Dict[str, Any]) -> Dict[str, Any]:
    # Append to audit sink (see grok_observability)
    from .grok_observability import audit_log
    audit_log("tool.audit", payload)
    return {"tool":"audit","status":"ok"}

registry.register("verify_access_compliance", verify_access)
registry.register("audit", audit)

def function_call_dispatch(name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    return registry.call(name, payload)
