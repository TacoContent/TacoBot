import hashlib
import re
from typing import Any, Dict, Optional

def _escape_snbt_string(s: str) -> str:
    # Minimal JS style escaping for SNBT compatibility
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"'

def _to_snbt_value(val: Any) -> str:
    if isinstance(val, dict):
        # compound: sort keys for deterministic string
        items = sorted(val.items())
        return "{" + ",".join(f"{k}:{_to_snbt_value(v)}" for k, v in items) + "}"
    if isinstance(val, list):
        # simple list; keep element order stable
        return "[" + ",".join(_to_snbt_value(v) for v in val) + "]"
    if isinstance(val, bool):
        # Convert boolean to Byte 1 or 0 (common NBT practice)
        return "1b" if val else "0b"
    if isinstance(val, int):
        # Use default integer representation (no suffix). Count is handled explicitly by caller.
        return str(val)
    if isinstance(val, float):
        return str(val)
    if isinstance(val, str):
        # Choose double-quoted SNBT for strings
        return _escape_snbt_string(val)
    # Fallback to string
    return _escape_snbt_string(str(val))

def calculate_variant_id(item_id: str, nbt: Optional[Dict[str, Any]] = None) -> str:
    """
    Calculate variant id for an item by computing SHA-256 of a canonical SNBT-like string for the item.
    item_id: "minecraft:stone"
    nbt: nested dict with compound tags that will be placed under "tag" in the item.
    Returns hex SHA-256 string (lowercase), same shape as the Java method's result.
    """
    # Build canonical compound dict as saved by the Java ItemStack.save: id + Count + tag (optional)
    compound: Dict[str, Any] = {}
    compound['id'] = item_id
    # Force Count to 1 (byte). We render as "1b" in the SNBT representation.
    compound['Count'] = '1b'
    if nbt:
        compound['tag'] = nbt

    # Build deterministic string: sort compound keys lexicographically (to produce stable serialization).
    # While Java's NBT serialization ordering may differ, this produces a deterministic canonical representation.
    snbt = _to_snbt_value(compound)

    # Some people want to use a provided SNBT string directly; normalize "Count" if present.
    # This code uses the canonicalization above so it's not necessary, but it's provided for completeness.

    # Compute SHA-256 of the UTF-8 bytes of the SNBT string (same as Java's tag.toString().getBytes)
    digest = hashlib.sha256(snbt.encode('utf-8')).hexdigest()
    return digest

# Convenience helper if you already have a SNBT string:
def calculate_variant_id_from_snbt(snbt_str: str) -> str:
    """
    Given an SNBT string for the ItemStack, normalize Count:...b to Count:1b and hash.
    This is useful if you can export SNBT from the server and want to validate it in Python.
    """
    normalized = re.sub(r'(?i)Count\s*:\s*(-?\d+)b', 'Count:1b', snbt_str)
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()

# Example usage
# if __name__ == "__main__":
#     # Example item with a nested tag compound (name)
#     item = "minecraft:stone"
#     nbt_data = {"display": {"Name": '{"text":"My Stone"}'}}
#     print("Variant ID:", calculate_variant_id(item, nbt_data))
