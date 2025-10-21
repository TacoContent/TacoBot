"""Type system and schema building utilities for OpenAPI/Swagger.

This module handles:
- Type annotation parsing and schema generation
- Union type flattening and schema extraction
- Type alias discovery and resolution
- Generic type handling and TypeVar detection
- Model inheritance and base class extraction

Auto-generated from swagger_sync.py refactoring.
Do not manually edit this file - regenerate using do_refactoring.py if needed.
"""

from __future__ import annotations

import ast
import os
import pathlib
import re
from typing import Any, Dict, List, Optional, Tuple

# Import from other swagger_sync modules
try:
    from .constants import DEFAULT_MODELS_ROOT
    from .utils import (
        _decorator_identifier,
        _extract_constant,
        _extract_constant_dict,
        _safe_unparse,
        _normalize_extension_key,
        _extract_literal_schema,
    )
except ImportError:
    # Fallback for script execution
    import sys
    _scripts_dir = pathlib.Path(__file__).parent.parent
    if str(_scripts_dir) not in sys.path:
        sys.path.insert(0, str(_scripts_dir))
    from swagger_sync.constants import DEFAULT_MODELS_ROOT
    from swagger_sync.utils import (
        _decorator_identifier,
        _extract_constant,
        _extract_constant_dict,
        _safe_unparse,
        _normalize_extension_key,
        _extract_literal_schema,
    )

# Sentinel value for missing defaults
MISSING = object()

# Global caches for type aliases
TYPE_ALIAS_CACHE: Dict[pathlib.Path, Dict[str, str]] = {}
TYPE_ALIAS_METADATA: Dict[str, Dict[str, Any]] = {}
GLOBAL_TYPE_ALIASES: Dict[str, str] = {}


def _build_schema_from_annotation(anno_str: str) -> Dict[str, Any]:
    schema = _extract_literal_schema(anno_str) or {}
    if schema:
        return schema

    # Unwrap Optional to detect nullable unions
    unwrapped, is_nullable = _unwrap_optional(anno_str)

    # Check for Union types (typing.Union or | operator)
    union_schema = _extract_union_schema(unwrapped, nullable=is_nullable)
    if union_schema:
        return union_schema

    lower = anno_str.lower()
    if 'list' in anno_str or 'List' in anno_str:
        schema = {'type': 'array', 'items': {'type': 'string'}}
    elif 'dict' in lower or 'mapping' in lower:
        schema = {'type': 'object'}
    elif 'int' in anno_str:
        schema = {'type': 'integer'}
    elif 'bool' in anno_str:
        schema = {'type': 'boolean'}
    elif 'float' in anno_str or 'double' in lower:
        schema = {'type': 'number'}
    else:
        # Attempt to detect model references for alias definitions
        model_pattern = r'\b([A-Z][A-Za-z0-9_]*)\b'
        matches = re.findall(model_pattern, anno_str)
        typing_keywords = {'Optional', 'Union', 'List', 'Dict', 'Any', 'Type', 'Callable', 'Tuple', 'Set', 'Literal'}
        potential_models = [m for m in matches if m not in typing_keywords]
        if potential_models:
            schema = {'$ref': f"#/components/schemas/{potential_models[0]}"}
        else:
            schema = {'type': 'string'}
    return schema


def _unwrap_optional(anno_str: str) -> tuple[str, bool]:
    """Unwrap Optional wrapper and detect if type is nullable.

    Handles:
    - Optional[Union[A, B]] -> (Union[A, B], True)
    - typing.Optional[SomeType] -> (SomeType, True)
    - Union[A, B, None] -> (Union[A, B], True)
    - Regular types -> (type, False)

    Args:
        anno_str: The type annotation string to parse

    Returns:
        Tuple of (unwrapped_type_string, is_nullable)
    """
    if not anno_str:
        return anno_str, False

    anno_str = anno_str.strip()
    is_nullable = False

    # Pattern 1: Optional[...] wrapper
    optional_pattern = r'^(?:typing\.)?Optional\s*\[\s*(.+)\s*\]$'
    match = re.match(optional_pattern, anno_str)
    if match:
        inner_type = match.group(1).strip()
        return inner_type, True

    # Pattern 2: Union[..., None] - check if None is in the union
    union_pattern = r'^(?:typing\.)?Union\s*\[\s*(.+)\s*\]$'
    match = re.match(union_pattern, anno_str)
    if match:
        inner_types = match.group(1)
        type_list = _split_union_types(inner_types)

        # Check if None is one of the union members
        has_none = any(t.strip() == 'None' for t in type_list)
        if has_none:
            # Remove None from the list
            non_none_types = [t.strip() for t in type_list if t.strip() != 'None']
            if len(non_none_types) == 1:
                # Union[Type, None] -> just Type (nullable)
                return non_none_types[0], True
            elif len(non_none_types) > 1:
                # Union[A, B, None] -> Union[A, B] (nullable)
                reconstructed = f"Union[{', '.join(non_none_types)}]"
                return reconstructed, True

    # Pattern 3: Pipe union with None (e.g., A | B | None)
    if '|' in anno_str and 'None' in anno_str:
        parts = [p.strip() for p in anno_str.split('|')]
        has_none = 'None' in parts
        if has_none:
            non_none_parts = [p for p in parts if p != 'None']
            if len(non_none_parts) == 1:
                return non_none_parts[0], True
            elif len(non_none_parts) > 1:
                reconstructed = ' | '.join(non_none_parts)
                return reconstructed, True

    return anno_str, False


def _flatten_nested_unions(anno_str: str) -> str:
    """Flatten nested Union types to a single Union.

    Converts patterns like:
    - Union[Union[A, B], C] -> Union[A, B, C]
    - Union[A, Union[B, C]] -> Union[A, B, C]
    - Union[Union[A, B], Union[C, D]] -> Union[A, B, C, D]
    - A | (B | C) -> A | B | C (pipe syntax)

    Args:
        anno_str: The type annotation string potentially containing nested unions

    Returns:
        Flattened type annotation string
    """
    if not anno_str:
        return anno_str

    # Handle pipe syntax first (even if no Union keyword)
    if '|' in anno_str and '(' in anno_str:
        # Pattern to match (Type1 | Type2) where there are pipes inside parens
        pipe_group_pattern = r'\(([^()]+\|[^()]+)\)'
        max_paren_iterations = 10
        paren_iteration = 0

        while re.search(pipe_group_pattern, anno_str) and paren_iteration < max_paren_iterations:
            anno_str = re.sub(pipe_group_pattern, r'\1', anno_str)
            paren_iteration += 1

    # If no Union keyword, we're done
    if 'Union' not in anno_str:
        return anno_str

    # Recursive helper to extract all types from a Union, flattening nested ones
    def extract_all_types(content: str) -> list[str]:
        """Extract all types from Union content, recursively flattening nested Unions."""
        types = _split_union_types(content)
        flattened = []

        for t in types:
            t = t.strip()
            # Check if this is a nested Union
            nested_match = re.match(r'(?:typing\.)?Union\s*\[(.+)\]$', t, re.DOTALL)
            if nested_match:
                # Recursively flatten the nested union
                nested_content = nested_match.group(1)
                flattened.extend(extract_all_types(nested_content))
            else:
                flattened.append(t)

        return flattened

    # Keep flattening until no more nested unions are found
    max_iterations = 10
    iteration = 0

    while 'Union[' in anno_str and iteration < max_iterations:
        iteration += 1

        # Find the outermost Union
        outer_match = re.search(r'(?:typing\.)?Union\s*\[', anno_str)
        if not outer_match:
            break

        # Find the matching closing bracket for this Union
        start_pos = outer_match.end() - 1  # Position of '['
        bracket_count = 1
        end_pos = start_pos + 1

        while end_pos < len(anno_str) and bracket_count > 0:
            if anno_str[end_pos] == '[':
                bracket_count += 1
            elif anno_str[end_pos] == ']':
                bracket_count -= 1
            end_pos += 1

        if bracket_count != 0:
            # Malformed, give up
            break

        # Extract the full Union expression
        union_start = outer_match.start()
        full_union = anno_str[union_start:end_pos]
        inner_content = anno_str[start_pos + 1:end_pos - 1]

        # Check if there are nested unions
        if 'Union[' in inner_content:
            # Flatten all types
            all_types = extract_all_types(inner_content)
            flattened_content = ', '.join(all_types)

            # Determine if we need typing prefix
            prefix = 'typing.' if anno_str[union_start:union_start + 7] == 'typing.' else ''
            flattened_union = f'{prefix}Union[{flattened_content}]'

            # Replace the nested union with flattened version
            anno_str = anno_str[:union_start] + flattened_union + anno_str[end_pos:]
        else:
            # No more nested unions at this level
            break

    return anno_str


def _extract_union_schema(anno_str: str, anyof: bool = False, nullable: bool = False) -> Optional[Dict[str, Any]]:
    """Extract oneOf or anyOf schema from Union type annotations.

    Handles both typing.Union[A, B] and A | B syntax.
    Supports Optional[Union[...]] patterns with nullable flag.
    Automatically flattens nested unions before processing.

    Args:
        anno_str: The type annotation string to parse
        anyof: If True, generates anyOf instead of oneOf for Union types
        nullable: If True, adds nullable: true to the schema

    Returns:
        Dictionary with oneOf or anyOf key (and nullable if applicable), or None if not a Union type
    """
    if not anno_str:
        return None

    # Flatten nested unions first (Union[Union[A, B], C] -> Union[A, B, C])
    anno_str = _flatten_nested_unions(anno_str)

    # Determine composition key based on anyof flag
    composition_key = 'anyOf' if anyof else 'oneOf'

    # Pattern 1: typing.Union[Type1, Type2, ...]
    union_pattern = r'(?:typing\.)?Union\s*\[\s*([^\]]+)\s*\]'
    match = re.search(union_pattern, anno_str)

    if match:
        inner_types = match.group(1)
        type_list = _split_union_types(inner_types)
        refs = _extract_refs_from_types(type_list)
        if refs:
            schema: Dict[str, Any] = {composition_key: refs}
            if nullable:
                schema['nullable'] = True
            return schema

    # Pattern 2: Type1 | Type2 | ... (Python 3.10+ union syntax)
    # Only process if we see the pipe operator and it looks like a type union
    if '|' in anno_str and not any(kw in anno_str for kw in ['List[', 'Dict[', 'Tuple[', 'Set[']):
        # Remove parentheses if present
        cleaned = anno_str.strip()
        if cleaned.startswith('(') and cleaned.endswith(')'):
            cleaned = cleaned[1:-1].strip()

        # Split by pipe operator
        type_list = [t.strip() for t in cleaned.split('|')]
        refs = _extract_refs_from_types(type_list)
        if refs:
            schema: Dict[str, Any] = {composition_key: refs}
            if nullable:
                schema['nullable'] = True
            return schema

    return None


def _split_union_types(inner_types: str) -> list[str]:
    """Split Union type arguments, respecting nested brackets."""
    types: list[str] = []
    current = []
    depth = 0

    for char in inner_types:
        if char == '[':
            depth += 1
            current.append(char)
        elif char == ']':
            depth -= 1
            current.append(char)
        elif char == ',' and depth == 0:
            types.append(''.join(current).strip())
            current = []
        else:
            current.append(char)

    if current:
        types.append(''.join(current).strip())

    return [t for t in types if t]


def _extract_refs_from_types(type_list: list[str]) -> list[Dict[str, str]]:
    """Extract $ref objects from a list of type strings.

    Returns a list of {$ref: ...} dicts for model class types.
    Filters out None, Optional wrappers, and primitive types.
    """
    refs: list[Dict[str, str]] = []
    typing_keywords = {'Optional', 'Union', 'List', 'Dict', 'Any', 'Type', 'Callable', 'Tuple', 'Set', 'Literal', 'None'}

    for type_str in type_list:
        type_str = type_str.strip()

        # Skip None type
        if type_str == 'None' or not type_str:
            continue

        # Unwrap Optional[Type] -> Type
        if type_str.startswith('Optional[') and type_str.endswith(']'):
            type_str = type_str[9:-1].strip()

        # Extract model class name (CamelCase pattern)
        model_pattern = r'\b([A-Z][A-Za-z0-9_]*)\b'
        matches = re.findall(model_pattern, type_str)

        # Filter out typing keywords
        potential_models = [m for m in matches if m not in typing_keywords]

        if potential_models:
            # Use the first model class found (should be the only one for simple refs)
            refs.append({'$ref': f'#/components/schemas/{potential_models[0]}'})

    return refs


def _discover_attribute_aliases(models_root: pathlib.Path) -> Dict[str, Tuple[Optional[str], Any]]:
    alias_map: Dict[str, Tuple[Optional[str], Any]] = {}
    candidates: List[pathlib.Path] = []
    # Check both openapi.py (main module) and core.py (refactored location)
    for filename in ['openapi/openapi.py', 'openapi/core.py']:
        potential = (models_root / filename).resolve()
        candidates.append(potential)
        default_candidate = (DEFAULT_MODELS_ROOT / filename).resolve()
        if default_candidate not in candidates:
            candidates.append(default_candidate)
    for candidate in candidates:
        if not candidate.exists():
            continue
        try:
            src = candidate.read_text(encoding='utf-8')
        except Exception:
            continue
        try:
            module = ast.parse(src, filename=str(candidate))
        except SyntaxError:
            continue
        for node in module.body:
            if not isinstance(node, ast.FunctionDef):
                continue
            ret_value: Optional[ast.AST] = None
            for stmt in node.body:
                if isinstance(stmt, ast.Return):
                    ret_value = stmt.value
                    break
            if not isinstance(ret_value, ast.AST):
                continue
            if isinstance(ret_value, ast.Expr):
                ret_value = ret_value.value  # pragma: no cover
            if not isinstance(ret_value, ast.Call):
                continue
            decorator_name = _decorator_identifier(ret_value.func)
            if decorator_name != 'attribute':
                continue
            attr_name: Optional[str] = None
            attr_value: Any = MISSING
            if ret_value.args:
                maybe_name = _extract_constant(ret_value.args[0])
                if isinstance(maybe_name, str):
                    attr_name = maybe_name
            if ret_value.args and len(ret_value.args) > 1:
                attr_value = _extract_constant(ret_value.args[1])
            for kw in ret_value.keywords or []:
                if kw.arg == 'name':
                    maybe_kw_name = _extract_constant(kw.value)
                    if isinstance(maybe_kw_name, str):
                        attr_name = maybe_kw_name
                elif kw.arg == 'value':
                    attr_value = _extract_constant(kw.value)
            alias_map[node.name] = (attr_name, attr_value)
        if alias_map:
            break
    return alias_map


def _is_type_alias_annotation(node: Optional[ast.AST]) -> bool:
    if node is None:
        return False
    if isinstance(node, ast.Name):
        return node.id == 'TypeAlias'
    if isinstance(node, ast.Attribute):
        return node.attr == 'TypeAlias'
    return False


def _module_name_to_path(module_name: Optional[str], current_file: pathlib.Path, level: int) -> Optional[pathlib.Path]:
    current_file = current_file.resolve()
    if level > 0:
        base = current_file.parent
        for _ in range(level - 1):
            base = base.parent
        if module_name:
            relative = module_name.replace('.', os.sep)
            base = base / relative
        if base.is_dir():
            pkg_init = (base / '__init__.py').resolve()
            if pkg_init.exists():
                return pkg_init
        candidate = base if base.suffix == '.py' else base.with_suffix('.py')
        if candidate.exists():
            return candidate.resolve()
        maybe_pkg = (base / '__init__.py') if not base.name == '__init__' else base
        if maybe_pkg.exists():
            return maybe_pkg.resolve()
        return None
    if not module_name:
        return None
    relative = module_name.replace('.', os.sep)
    repo_root = pathlib.Path('.').resolve()
    candidate = (repo_root / f"{relative}.py").resolve()
    if candidate.exists():
        return candidate
    candidate_pkg = (repo_root / relative / '__init__.py').resolve()
    if candidate_pkg.exists():
        return candidate_pkg
    for parent in current_file.parents:
        fallback = (parent / f"{relative}.py").resolve()
        if fallback.exists():
            return fallback
        fallback_pkg = (parent / relative / '__init__.py').resolve()
        if fallback_pkg.exists():
            return fallback_pkg
    return None


def _load_type_aliases_for_path(path: pathlib.Path) -> Dict[str, str]:
    resolved = path.resolve()
    cached = TYPE_ALIAS_CACHE.get(resolved)
    if cached is not None:
        return cached
    TYPE_ALIAS_CACHE[resolved] = {}
    try:
        src = resolved.read_text(encoding='utf-8')
    except Exception:
        return TYPE_ALIAS_CACHE[resolved]
    try:
        module = ast.parse(src, filename=str(resolved))
    except SyntaxError:
        return TYPE_ALIAS_CACHE[resolved]
    alias_map = _collect_type_aliases_from_ast(module, resolved)
    TYPE_ALIAS_CACHE[resolved] = alias_map
    return alias_map


def _load_type_aliases_for_module(module_name: Optional[str], level: int, current_file: pathlib.Path) -> Dict[str, str]:
    target = _module_name_to_path(module_name, current_file, level)
    if not target:
        return {}
    return _load_type_aliases_for_path(target)


def _collect_typevars_from_ast(module: ast.AST) -> set[str]:
    """Collect TypeVar names defined in a module.

    Returns:
        Set of TypeVar names (e.g., {'T', 'K', 'V'})
    """
    typevars: set[str] = set()
    for node in getattr(module, 'body', []):
        # Look for assignments like: T = TypeVar('T')
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    # Check if the value is a TypeVar() call
                    if isinstance(node.value, ast.Call):
                        func_name = _decorator_identifier(node.value.func)
                        if func_name == 'TypeVar':
                            typevars.add(target.id)
    return typevars


def _extract_openapi_base_classes(cls: ast.ClassDef, module_typevars: set[str]) -> list[str]:
    """Extract base class names that could be OpenAPI model components.

    Filters out:
    - Generic type parameters (Generic[T])
    - TypeVars
    - Common base classes (object, ABC, etc.)
    - Built-in typing classes (Dict, List, etc.)

    Returns:
        List of potential OpenAPI model base class names
    """
    base_classes: list[str] = []
    for base in cls.bases:
        base_name = _safe_unparse(base)
        if not base_name:
            continue

        # Skip Generic[T] pattern
        if 'Generic[' in base_name or base_name == 'Generic':
            continue

        # Extract simple class name (e.g., "PagedResults" from "PagedResults" or module.PagedResults)
        # Handle subscripted generics like PagedResults[T]
        if '[' in base_name:
            base_name = base_name.split('[')[0].strip()

        # Get the last component if it's a qualified name
        if '.' in base_name:
            base_name = base_name.split('.')[-1]

        # Skip if it's a TypeVar
        if base_name in module_typevars:
            continue

        # Skip common base classes
        if base_name in ('object', 'ABC', 'ABCMeta', 'type', 'Protocol'):
            continue

        # Skip built-in typing classes (these should be handled via additionalProperties, not allOf)
        if base_name in ('Dict', 'List', 'Tuple', 'Set', 'Mapping', 'Sequence', 'Iterable'):
            continue

        # Only include if it looks like a class name (starts with uppercase)
        if base_name and base_name[0].isupper():
            base_classes.append(base_name)

    return base_classes


def _extract_dict_inheritance_schema(cls: ast.ClassDef) -> Optional[Dict[str, Any]]:
    """Extract additionalProperties schema from Dict[K, V] base class.

    When a class inherits from typing.Dict[str, ValueType] or dict[str, ValueType],
    this extracts the value type and generates an OpenAPI schema with additionalProperties.

    Args:
        cls: The class definition AST node

    Returns:
        Schema dict with additionalProperties if Dict inheritance detected, None otherwise

    Examples:
        class Foo(typing.Dict[str, int]): ... → {'type': 'object', 'additionalProperties': {'type': 'integer'}}
        class Bar(Dict[str, MyModel]): ... → {'type': 'object', 'additionalProperties': {'$ref': '...'}}
        class Baz(dict[str, float]): ... → {'type': 'object', 'additionalProperties': {'type': 'number'}}
    """
    from .decorator_parser import _extract_dict_schema

    for base in cls.bases:
        base_str = _safe_unparse(base)
        if not base_str:
            continue

        # Check if base is Dict/dict or typing.Dict with type arguments
        # Match both uppercase Dict[...] and lowercase dict[...]
        if 'Dict[' in base_str or 'dict[' in base_str:
            # Parse the subscript to extract value type
            # Handle typing.Dict[K, V], Dict[K, V], and dict[K, V]
            try:
                # Parse the base as an expression to get AST node
                import ast as ast_module
                base_expr = ast_module.parse(base_str, mode='eval').body
                
                # Check if it's a subscript (Dict[...] or dict[...])
                if isinstance(base_expr, ast_module.Subscript):
                    # Extract the schema using existing decorator parser logic
                    # This handles Dict[str, T] → additionalProperties: T
                    schema = _extract_dict_schema(base_expr.slice)
                    return schema
            except Exception:
                # If parsing fails, fall through
                pass

    return None


def _collect_type_aliases_from_ast(module: ast.AST, file_path: pathlib.Path) -> Dict[str, str]:
    global TYPE_ALIAS_METADATA, GLOBAL_TYPE_ALIASES
    alias_map: Dict[str, str] = {}

    # First pass: collect TypeAlias assignments (both inline decorator and plain assignments)
    for node in getattr(module, 'body', []):
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if not _is_type_alias_annotation(node.annotation):
                continue
            alias_name = node.target.id
            value_node = node.value

            # Pattern 1: alias: TypeAlias = openapi.type_alias(...)(value)
            if isinstance(value_node, ast.Call) and isinstance(value_node.func, ast.Call):
                factory_call = value_node.func
                decorator_name = _decorator_identifier(factory_call.func)
                if decorator_name == 'type_alias':
                    component_name: Optional[str] = None
                    description: Optional[str] = None
                    default_value: Any = MISSING
                    managed_flag = False
                    anyof_flag = False
                    attr_map: Dict[str, Any] = {}
                    if factory_call.args:
                        maybe_name = _extract_constant(factory_call.args[0])
                        if isinstance(maybe_name, str):
                            component_name = maybe_name
                    for kw in factory_call.keywords or []:
                        if kw.arg == 'name':
                            maybe_name = _extract_constant(kw.value)
                            if isinstance(maybe_name, str):
                                component_name = maybe_name
                        elif kw.arg == 'description':
                            maybe_desc = _extract_constant(kw.value)
                            if isinstance(maybe_desc, str):
                                description = maybe_desc
                        elif kw.arg == 'default':
                            default_value = _extract_constant(kw.value)
                        elif kw.arg == 'managed':
                            maybe_managed = _extract_constant(kw.value)
                            if isinstance(maybe_managed, bool):
                                managed_flag = maybe_managed
                        elif kw.arg == 'anyof':
                            maybe_anyof = _extract_constant(kw.value)
                            if isinstance(maybe_anyof, bool):
                                anyof_flag = maybe_anyof
                        elif kw.arg == 'attributes':
                            extracted = _extract_constant_dict(kw.value)
                            if extracted is not None:
                                attr_map = extracted
                    component_name = component_name or alias_name
                    alias_value_node = value_node.args[0] if value_node.args else None
                    alias_value_str = _safe_unparse(alias_value_node) or ''
                    if alias_value_str:
                        alias_map[alias_name] = alias_value_str
                    meta: Dict[str, Any] = {
                        'alias': alias_name,
                        'component': component_name,
                        'annotation': alias_value_str,
                        'path': str(file_path.resolve()),
                    }
                    if description is not None:
                        meta['description'] = description
                    if default_value is not MISSING:
                        meta['default'] = default_value
                    if anyof_flag:
                        meta['anyof'] = True
                    extensions: Dict[str, Any] = {}
                    if managed_flag:
                        extensions['x-tacobot-managed'] = True
                    for k, v in attr_map.items():
                        extensions[_normalize_extension_key(k)] = v
                    if extensions:
                        meta['extensions'] = extensions
                    TYPE_ALIAS_METADATA[alias_name] = meta
                    continue

            # Pattern 2: alias: TypeAlias = Union[...] (plain assignment, decorator comes later)
            value_str = _safe_unparse(node.value)
            if value_str:
                alias_map[alias_name] = value_str

    # Second pass: look for standalone openapi.type_alias()() calls that reference TypeAlias names
    for node in getattr(module, 'body', []):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            call_node = node.value
            # Check for pattern: openapi.type_alias(...)(cast(Any, alias_name))
            if isinstance(call_node.func, ast.Call):
                factory_call = call_node.func
                decorator_name = _decorator_identifier(factory_call.func)
                if decorator_name == 'type_alias':
                    # Extract metadata from decorator call
                    component_name: Optional[str] = None
                    description: Optional[str] = None
                    default_value: Any = MISSING
                    managed_flag = False
                    anyof_flag = False
                    attr_map: Dict[str, Any] = {}

                    if factory_call.args:
                        maybe_name = _extract_constant(factory_call.args[0])
                        if isinstance(maybe_name, str):
                            component_name = maybe_name

                    for kw in factory_call.keywords or []:
                        if kw.arg == 'name':
                            maybe_name = _extract_constant(kw.value)
                            if isinstance(maybe_name, str):
                                component_name = maybe_name
                        elif kw.arg == 'description':
                            maybe_desc = _extract_constant(kw.value)
                            if isinstance(maybe_desc, str):
                                description = maybe_desc
                        elif kw.arg == 'default':
                            default_value = _extract_constant(kw.value)
                        elif kw.arg == 'managed':
                            maybe_managed = _extract_constant(kw.value)
                            if isinstance(maybe_managed, bool):
                                managed_flag = maybe_managed
                        elif kw.arg == 'anyof':
                            maybe_anyof = _extract_constant(kw.value)
                            if isinstance(maybe_anyof, bool):
                                anyof_flag = maybe_anyof
                        elif kw.arg == 'attributes':
                            extracted = _extract_constant_dict(kw.value)
                            if extracted is not None:
                                attr_map = extracted

                    # Extract alias name from cast(..., alias_name) call
                    alias_name: Optional[str] = None
                    if call_node.args:
                        cast_arg = call_node.args[0]
                        # Handle cast(Any, alias_name)
                        if isinstance(cast_arg, ast.Call):
                            cast_func_id = _decorator_identifier(cast_arg.func)
                            if cast_func_id == 'cast' and len(cast_arg.args) >= 2:
                                if isinstance(cast_arg.args[1], ast.Name):
                                    alias_name = cast_arg.args[1].id
                        # Handle direct name reference
                        elif isinstance(cast_arg, ast.Name):
                            alias_name = cast_arg.id

                    # If we found an alias name and it exists in alias_map, register metadata
                    if alias_name and alias_name in alias_map:
                        component_name = component_name or alias_name
                        annotation_str = alias_map[alias_name]

                        meta: Dict[str, Any] = {
                            'alias': alias_name,
                            'component': component_name,
                            'annotation': annotation_str,
                            'path': str(file_path.resolve()),
                        }
                        if description is not None:
                            meta['description'] = description
                        if default_value is not MISSING:
                            meta['default'] = default_value
                        if anyof_flag:
                            meta['anyof'] = True

                        extensions: Dict[str, Any] = {}
                        if managed_flag:
                            extensions['x-tacobot-managed'] = True
                        for k, v in attr_map.items():
                            extensions[_normalize_extension_key(k)] = v
                        if extensions:
                            meta['extensions'] = extensions

                        TYPE_ALIAS_METADATA[alias_name] = meta
    for node in getattr(module, 'body', []):
        if isinstance(node, ast.ImportFrom):
            remote_aliases = _load_type_aliases_for_module(node.module, node.level, file_path)
            if not remote_aliases:
                continue
            for alias in node.names:
                if alias.name == '*':
                    continue
                local_name = alias.asname or alias.name
                if local_name in alias_map:
                    continue
                remote = remote_aliases.get(alias.name)
                if remote:
                    alias_map[local_name] = remote
    if alias_map:
        GLOBAL_TYPE_ALIASES.update(alias_map)
    return alias_map


def _register_type_aliases(py_file: pathlib.Path, module: ast.Module) -> Dict[str, str]:
    resolved = py_file.resolve()
    cached = TYPE_ALIAS_CACHE.get(resolved)
    if cached is not None:
        return cached
    alias_map = _collect_type_aliases_from_ast(module, resolved)
    TYPE_ALIAS_CACHE[resolved] = alias_map
    return alias_map


def _expand_type_aliases(annotation: str, alias_map: Dict[str, str]) -> str:
    if not alias_map or not annotation:
        return annotation
    expanded = annotation
    for _ in range(5):
        previous = expanded
        for alias_name, alias_value in alias_map.items():
            if not alias_value:
                continue
            pattern = r'\b' + re.escape(alias_name) + r'\b'
            expanded = re.sub(pattern, f'({alias_value})', expanded)
        if expanded == previous:
            break
    return expanded
