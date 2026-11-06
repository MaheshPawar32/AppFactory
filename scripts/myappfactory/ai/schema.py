"""Minimal JSON-schema validation for structured AI output (stdlib only)."""
from __future__ import annotations

TYPES = {"object": dict, "array": list, "string": str, "boolean": bool,
         "number": (int, float), "integer": int, "null": type(None)}


def validate(value, schema: dict, path="$") -> list[str]:
    """Return a list of violations; empty means valid. Supports the subset used by factory prompts."""
    errors = []
    expected = schema.get("type")
    if expected:
        options = expected if isinstance(expected, list) else [expected]
        ok = any(isinstance(value, TYPES[t]) and not (t in ("number", "integer") and isinstance(value, bool))
                 for t in options)
        if not ok:
            return [f"{path}: expected {expected}, got {type(value).__name__}"]
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: {value!r} not in {schema['enum']}")
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                errors.append(f"{path}: missing required '{key}'")
        properties = schema.get("properties", {})
        for key, item in value.items():
            if key in properties:
                errors += validate(item, properties[key], f"{path}.{key}")
            elif schema.get("additionalProperties") is False:
                errors.append(f"{path}: unexpected property '{key}'")
    if isinstance(value, list) and "items" in schema:
        for index, item in enumerate(value):
            errors += validate(item, schema["items"], f"{path}[{index}]")
        if "minItems" in schema and len(value) < schema["minItems"]:
            errors.append(f"{path}: fewer than {schema['minItems']} items")
    return errors


def strict(schema: dict) -> dict:
    """Copy of a schema with additionalProperties:false and all properties required on every object."""
    if not isinstance(schema, dict):
        return schema
    result = dict(schema)
    if result.get("type") == "object" and "properties" in result:
        result["properties"] = {k: strict(v) for k, v in result["properties"].items()}
        result.setdefault("required", list(result["properties"]))
        result["additionalProperties"] = False
    if result.get("type") == "array" and "items" in result:
        result["items"] = strict(result["items"])
    return result
