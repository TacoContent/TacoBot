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
    # Build a top-level mapping and delegate to _to_snbt_value which sorts keys
    top_level = {}
    if nbt:
        # copy provided NBT fields into top-level
        for k, v in nbt.items():
            top_level[k] = v
    # add count and id as top-level fields
    top_level["count"] = 1
    top_level["id"] = item_id
    snbt = _to_snbt_value(top_level)

    # Some people want to use a provided SNBT string directly; normalize "Count" if present.
    # This code uses the canonicalization above so it's not necessary, but it's provided for completeness.

    # Compute SHA-256 of the UTF-8 bytes of the SNBT string (same as Java's tag.toString().getBytes)
    digest = hashlib.sha256(snbt.encode('utf-8')).hexdigest()
    return digest


def _normalize_compound_str(item_id: str, s: str, ensure_id: bool = True) -> str:
    """Normalize a compound SNBT string by sorting top-level keys and recursively
    normalizing nested compounds. Missing `id` will be set to `item_id`, and
    top-level `count` is normalized to `1`.
    """
    normalized = s.strip()
    if not normalized.startswith('{'):
        normalized = '{' + normalized + '}'
    inner = normalized[1:-1]
    parts = []
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
            parts.append(''.join(cur).strip())
            cur = []
        else:
            cur.append(ch)
    if cur:
        parts.append(''.join(cur).strip())

    mapping2: dict[str, str] = {}
    saw_id2 = False
    # helper to split the first top-level colon (ignore colons inside quotes or nested compounds)
    def _split_key_val(pair: str) -> tuple[str, str]:
        in_quote = False
        quote_char = ''
        depth2 = 0
        for i, ch in enumerate(pair):
            if ch in ('"', "'"):
                if not in_quote:
                    in_quote = True
                    quote_char = ch
                elif ch == quote_char:
                    in_quote = False
            elif ch == '{' and not in_quote:
                depth2 += 1
            elif ch == '}' and not in_quote:
                depth2 -= 1
            elif ch == ':' and not in_quote and depth2 == 0:
                return pair[:i], pair[i + 1 :]
        return pair, ''
    for p in parts:
        if not p:
            continue
        if ':' in p:
            key, val = _split_key_val(p)
            key_stripped = key.strip().strip('"').strip("'")
            val_str = val.strip()
            # recursively normalize nested compounds
            if val_str.startswith('{') and val_str.endswith('}'):
                # don't inject top-level only fields (like id/count) into nested compounds
                val_str = _normalize_compound_str(item_id, val_str, ensure_id=False)
            if key_stripped.lower() == 'count':
                if ensure_id:
                    mapping2['count'] = '1'
                    continue
            if key_stripped.lower() == 'id':
                saw_id2 = True
                mapping2['id'] = val_str
                continue
            mapping2[key_stripped] = val_str
        else:
            mapping2[p] = p

    if ensure_id and not saw_id2:
        mapping2['id'] = _to_snbt_value(item_id)

    def _format_key2(k: str) -> str:
        if re.fullmatch(r"[A-Za-z0-9_]+", k):
            return k
        return _escape_snbt_string(k)

    items_sorted2 = sorted(mapping2.items(), key=lambda kv: kv[0])
    return '{' + ','.join(f"{_format_key2(k)}:{v}" for k, v in items_sorted2) + '}'


def calculate_variant_id_from_snbt(item_id: str, snbt: Optional[str] = None) -> str:
    """Given an SNBT string for the ItemStack, normalize Count:... to Count:1 and hash.
    This is useful if you can export SNBT from the server and want to validate it in Python.
    """
    # If the provided SNBT string is empty or just an empty compound, use a basic
    # default representation for the item with a single unit: {count:1,id:"<item_id>"}
    if not snbt or snbt.strip() == "{}":
        snbt = '{count:1,id:' + _to_snbt_value(item_id) + '}'
        return hashlib.sha256(snbt.encode('utf-8')).hexdigest()

    normalized = snbt.strip()
    if not normalized.startswith('{'):
        normalized = '{' + normalized + '}'

    inner = normalized[1:-1]
    final = _normalize_compound_str(item_id, '{' + inner + '}')
    return hashlib.sha256(final.encode('utf-8')).hexdigest()


def canonicalize_snbt(item_id: str, snbt: Optional[str]) -> str:
    """Return the normalized, canonical SNBT string for the provided SNBT or item_id.

    This mirrors the normalization performed before hashing in
    calculate_variant_id_from_snbt and is useful for testing and debugging.
    """
    if not snbt or snbt.strip() == "{}":
        return '{count:1,id:' + _to_snbt_value(item_id) + '}'
    normalized = snbt.strip()
    if not normalized.startswith('{'):
        normalized = '{' + normalized + '}'
    inner = normalized[1:-1]
    return _normalize_compound_str(item_id, '{' + inner + '}')
