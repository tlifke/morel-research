from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class SdkTool:
    name: str
    description: str
    input_schema: Dict[str, Any]
    handler: Callable[[Dict[str, Any]], Any]


@dataclass
class SdkMcpServer:
    name: str
    version: str
    tools: Dict[str, SdkTool] = field(default_factory=dict)


def _normalize_schema(schema: Any) -> Dict[str, Any]:
    if isinstance(schema, dict) and schema.get("type") == "object":
        return schema
    if isinstance(schema, dict):
        properties: Dict[str, Any] = {}
        required: List[str] = []
        type_map = {int: "integer", float: "number", str: "string", bool: "boolean"}
        for key, val in schema.items():
            if isinstance(val, type):
                properties[key] = {"type": type_map.get(val, "string")}
                required.append(key)
            elif isinstance(val, dict):
                properties[key] = val
                required.append(key)
            else:
                properties[key] = {"type": "string"}
                required.append(key)
        return {"type": "object", "properties": properties, "required": required}
    return {"type": "object", "properties": {}, "required": []}


def tool(name: str, description: str, input_schema: Any):
    def decorator(fn: Callable[[Dict[str, Any]], Any]) -> SdkTool:
        return SdkTool(
            name=name,
            description=description,
            input_schema=_normalize_schema(input_schema),
            handler=fn,
        )
    return decorator


def create_sdk_mcp_server(
    name: str,
    version: str = "1.0.0",
    tools: Optional[List[SdkTool]] = None,
) -> SdkMcpServer:
    server = SdkMcpServer(name=name, version=version)
    for t in tools or []:
        server.tools[t.name] = t
    return server
