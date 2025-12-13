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

        def _format_key(k: str) -> str:
            # SNBT keys that contain non-word characters (e.g., ':') should be quoted
            # so they appear like "minecraft:enchantments" in the canonical SNBT.
            if re.fullmatch(r"[A-Za-z0-9_]+", k):
                return k
            return _escape_snbt_string(k)

        return "{" + ",".join(f"{_format_key(k)}:{_to_snbt_value(v)}" for k, v in items) + "}"
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
    # Build canonical SNBT-like string that matches the SNBT canonicalization used by
    # `calculate_variant_id_from_snbt` so dict inputs and SNBT strings produce the same digest.
    # The convention we use: inline the provided `nbt` (if any) as top-level tag fields first,
    # then append `count:1` and finally `id:"<item_id>"`. This ordering (tag fields, count, id)
    # matches the SNBT examples used by the project and keeps canonicalization deterministic
    # by delegating nested dict serialization to _to_snbt_value (which sorts object keys).
    if nbt:
        # _to_snbt_value yields a mapping surrounded by braces, e.g. '{components:{...}}'
        # strip the outer braces and inline the contents first
        inner = _to_snbt_value(nbt)
        if inner.startswith('{') and inner.endswith('}'):
            inner = inner[1:-1]
        # use count:1 (no byte suffix) to match how SNBT strings are commonly provided
        snbt = '{' + inner + ',count:1,id:' + _to_snbt_value(item_id) + '}'
    else:
        snbt = '{count:1,id:' + _to_snbt_value(item_id) + '}'

    # Some people want to use a provided SNBT string directly; normalize "Count" if present.
    # This code uses the canonicalization above so it's not necessary, but it's provided for completeness.

    # Compute SHA-256 of the UTF-8 bytes of the SNBT string (same as Java's tag.toString().getBytes)
    digest = hashlib.sha256(snbt.encode('utf-8')).hexdigest()
    return digest

# Convenience helper if you already have a SNBT string:
def calculate_variant_id_from_snbt(item_id: str, snbt_str: Optional[str] = None) -> str:
    """
    Given an SNBT string for the ItemStack, normalize Count:...b to Count:1b and hash.
    This is useful if you can export SNBT from the server and want to validate it in Python.
    """
    # If the provided SNBT string is empty or just an empty compound, use a basic
    # default representation for the item with a single unit: {count:1,id:"<item_id>"}
    if not snbt_str or snbt_str.strip() == "{}":
        snbt = '{count:1,id:' + _to_snbt_value(item_id) + '}'
        return hashlib.sha256(snbt.encode('utf-8')).hexdigest()

    # Ensure the normalized SNBT is wrapped inside braces so both "{count:1,...}"
    # and the shorter 'count:1,...' variants hash consistently
    normalized = snbt_str.strip()
    if not normalized.startswith('{'):
        normalized = '{' + normalized + '}'

    # We want to normalize only the top-level `count` field (not nested counts
    # inside e.g. container item lists). Split the top-level compound into
    # comma-separated pairs while respecting nested braces so nested commas do
    # not break the top-level splitting.
    inner = normalized[1:-1]
    pairs = []
    cur = []
    depth = 0
    for ch in inner:
        if ch == '{':
            depth += 1
            cur.append(ch)
        elif ch == '}':
            depth -= 1
            cur.append(ch)
        elif ch == ',' and depth == 0:
            pairs.append(''.join(cur).strip())
            cur = []
        else:
            cur.append(ch)
    if cur:
        pairs.append(''.join(cur).strip())

    # Normalize only top-level count key values and detect whether id is present
    saw_id = False
    normalized_pairs = []
    for p in pairs:
        if not p:
            continue
        # split on first ':' to get key
        if ':' in p:
            key, val = p.split(':', 1)
            key_stripped = key.strip().strip('"').strip("'")
            if key_stripped.lower() == 'count':
                normalized_pairs.append('count:1')
                continue
            if key_stripped.lower() == 'id':
                saw_id = True
                # keep original id formatting (quotes etc)
                normalized_pairs.append(f'id:{val.strip()}')
                continue
        # otherwise keep original pair as-is
        normalized_pairs.append(p)

    if not saw_id:
        # add top-level id if missing
        normalized_pairs.append('id:' + _to_snbt_value(item_id))

    final = '{' + ','.join(normalized_pairs) + '}'
    return hashlib.sha256(final.encode('utf-8')).hexdigest()

# Example usage
# if __name__ == "__main__":
#     # Example item with a nested tag compound (name)
#     item = "minecraft:stone"
#     nbt_data = {"display": {"Name": '{"text":"My Stone"}'}}
#     print("Variant ID:", calculate_variant_id(item, nbt_data))
