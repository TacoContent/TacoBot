"""Model component schema generation from decorated classes.

This module scans model files for classes decorated with @openapi.component
and automatically generates OpenAPI component schemas by analyzing class
structure, type annotations, and docstrings.

Features:
- AST-based analysis (no imports executed)
- Type annotation inference with type alias expansion
- Support for inheritance via allOf
- Property metadata from docstring YAML blocks
- Full schema override support
- Literal enum detection
- Extension attributes (x-tacobot-*)

Auto-generated from swagger_sync.py refactoring.
Do not manually edit this file - regenerate using refactoring process if needed.
"""

from __future__ import annotations

import ast
import pathlib
import re
from typing import Any, Dict, List, Optional, Tuple

# Import from other swagger_sync modules
try:
    from .constants import MISSING
    from .yaml_handler import yaml
    from .type_system import (
        TYPE_ALIAS_METADATA,
        GLOBAL_TYPE_ALIASES,
        _discover_attribute_aliases,
        _register_type_aliases,
        _collect_typevars_from_ast,
        _expand_type_aliases,
        _extract_openapi_base_classes,
        _build_schema_from_annotation,
        _unwrap_optional,
        _extract_union_schema,
    )
    from .utils import (
        _decorator_identifier,
        _extract_constant,
        _normalize_extension_key,
        _safe_unparse,
    )
except ImportError:
    # Fallback for script execution
    import sys
    _parent = pathlib.Path(__file__).parent
    if str(_parent) not in sys.path:
        sys.path.insert(0, str(_parent))
    from constants import MISSING
    from yaml_handler import yaml
    from type_system import (
        TYPE_ALIAS_METADATA,
        GLOBAL_TYPE_ALIASES,
        _discover_attribute_aliases,
        _register_type_aliases,
        _collect_typevars_from_ast,
        _expand_type_aliases,
        _extract_openapi_base_classes,
        _build_schema_from_annotation,
        _unwrap_optional,
        _extract_union_schema,
    )
    from utils import (
        _decorator_identifier,
        _extract_constant,
        _normalize_extension_key,
        _safe_unparse,
    )


def _resolve_hint_to_schema(hint_value: Any) -> Optional[Dict[str, Any]]:
    """Resolve a hint kwarg value to an OpenAPI schema.
    
    Supports:
    - Type objects (list, dict, str, int, bool, float)
    - Typing module types (List[Any], Dict[str, Any], etc.)
    - String annotations (e.g., "List[Dict[str, Any]]")
    
    Args:
        hint_value: The hint value from @openapi.property decorator
        
    Returns:
        OpenAPI schema dict if hint can be resolved, None otherwise
    """
    if hint_value is None:
        return None
        
    # Case 1: String annotation - enhanced processing for nested types
    if isinstance(hint_value, str):
        # Use existing _build_schema_from_annotation as base
        schema = _build_schema_from_annotation(hint_value)
        
        # Enhanced detection for List[Dict[...]] pattern
        if schema.get('type') == 'array':
            # Check if it's List[Dict[...]] or List[dict]
            lowered = hint_value.lower()
            if 'dict' in lowered or 'mapping' in lowered:
                # Override default string items with object
                schema['items'] = {'type': 'object'}
        
        return schema
    
    # Case 2: Type object (list, dict, str, int, bool, float)
    if isinstance(hint_value, type):
        type_name = hint_value.__name__.lower()
        if type_name == 'list':
            return {'type': 'array', 'items': {'type': 'string'}}
        elif type_name == 'dict':
            return {'type': 'object'}
        elif type_name in ['str', 'string']:
            return {'type': 'string'}
        elif type_name in ['int', 'integer']:
            return {'type': 'integer'}
        elif type_name == 'bool':
            return {'type': 'boolean'}
        elif type_name == 'float':
            return {'type': 'number'}
        else:
            # Unknown type - might be a model class
            # Check if it's CamelCase (likely a model)
            if type_name and type_name[0].isupper():
                return {'$ref': f'#/components/schemas/{hint_value.__name__}'}
            return None
    
    # Case 3: Typing module types (List[Any], Dict[str, Any], etc.)
    # These have a __module__ attribute and string repr we can parse
    if hasattr(hint_value, '__module__') and hint_value.__module__ == 'typing':
        # Convert to string representation and parse
        hint_str = str(hint_value)
        # Clean up typing. prefix if present
        hint_str = hint_str.replace('typing.', '')
        return _resolve_hint_to_schema(hint_str)  # Recursively process as string
    
    # Case 4: Try converting to string as last resort
    try:
        hint_str = str(hint_value)
        # Remove typing. prefix if present
        hint_str = hint_str.replace('typing.', '')
        return _resolve_hint_to_schema(hint_str)  # Recursively process as string
    except Exception:
        return None


def collect_model_components(models_root: pathlib.Path) -> tuple[Dict[str, Dict[str, Any]], set[str]]:
    """Collect model classes decorated with @openapi.component and derive naive schemas.

    Strategy (pure AST – no imports executed):
    * Find classes with an @openapi.component decorator.
    * Extract component name (first positional arg or class name fallback) and description kwarg.
    * Inside __init__, record any self.<attr> AnnAssign or Assign targets (skip private leading _).
    * Infer primitive types from annotations / literal defaults; mark non-optional as required.
    Limitations: nested / complex types collapsed to string; arrays default items.type=string.

    Args:
        models_root: Root directory to scan for model files

    Returns:
        Tuple of (components_dict, excluded_component_names_set)
    """
    components: Dict[str, Dict[str, Any]] = {}
    excluded_components: set[str] = set()
    if not models_root.exists():
        return components, excluded_components
    resolved_models_root = models_root.resolve()
    attribute_aliases = _discover_attribute_aliases(models_root)
    for py_file in models_root.rglob('*.py'):
        if py_file.name.startswith('_'):
            continue
        try:
            src = py_file.read_text(encoding='utf-8')
        except Exception:
            continue
        try:
            module = ast.parse(src, filename=str(py_file))
        except SyntaxError:
            continue
        type_alias_map = _register_type_aliases(py_file, module)
        module_typevars = _collect_typevars_from_ast(module)
        for cls in [n for n in module.body if isinstance(n, ast.ClassDef)]:
            comp_name: Optional[str] = None
            description: str = ''
            # Parse class docstring for optional openapi-model property metadata block or full schema override.
            raw_class_doc = ast.get_docstring(cls) or ''
            prop_meta: Dict[str, Dict[str, Any]] = {}
            full_schema_override: Optional[Dict[str, Any]] = None

            # Check for full schema definition in >>>openapi block
            if '>>>openapi' in raw_class_doc:
                unified_re = re.compile(r'(?:>>>openapi)\s*(.*?)\s*(?:<<<openapi)', re.DOTALL | re.IGNORECASE)
                for m_unified in unified_re.finditer(raw_class_doc):
                    raw_block = m_unified.group(1)
                    try:
                        loaded = yaml.load(raw_block) or {}
                        if isinstance(loaded, dict):
                            # Check if this is a full schema definition (has type but no properties)
                            # or if it has properties, treat as property metadata
                            if 'type' in loaded and 'properties' not in loaded:
                                # This is a full schema definition, not just property metadata
                                full_schema_override = loaded.copy()
                                break  # Use the first complete schema found
                            elif 'properties' in loaded and isinstance(loaded['properties'], dict):
                                # Property metadata mode
                                for k, v in loaded['properties'].items():
                                    if not isinstance(v, dict):
                                        continue
                                    existing = prop_meta.get(k)
                                    if existing is None:
                                        # New property metadata entirely from unified block.
                                        prop_meta[k] = v.copy()
                                    else:
                                        # Add only keys not already present (preserve legacy priority).
                                        for mk, mv in v.items():
                                            if mk not in existing:
                                                existing[mk] = mv
                    except Exception:
                        continue  # Try next block if present
            decorator_extensions: Dict[str, Any] = {}
            property_decorators: Dict[str, Dict[str, Any]] = {}  # Track @openapi.property decorators
            for deco in cls.decorator_list:
                deco_call: Optional[ast.Call] = deco if isinstance(deco, ast.Call) else None
                deco_name = None
                if isinstance(deco, ast.Call):
                    deco_name = _decorator_identifier(deco.func)
                else:
                    deco_name = _decorator_identifier(deco)
                if not deco_name:
                    continue
                if deco_name == 'property':
                    # Handle @openapi.property with multiple usage patterns:
                    # 1. Legacy: @openapi.property("prop", "name", "value")
                    # 2. New kwargs: @openapi.property("prop", description="...")
                    # 3. All kwargs: @openapi.property(property="prop", description="...")
                    if not deco_call:
                        continue

                    prop_name: Optional[str] = None
                    key_name: Optional[str] = None
                    key_value: Any = None
                    additional_kwargs: Dict[str, Any] = {}

                    # Handle positional arguments
                    if len(deco_call.args) >= 1:
                        # First positional arg is always the property name
                        prop_name = _extract_constant(deco_call.args[0])
                    
                    # Legacy 3-arg form: @openapi.property("prop", "name", "value")
                    if len(deco_call.args) >= 3:
                        key_name = _extract_constant(deco_call.args[1])
                        key_value = _extract_constant(deco_call.args[2])

                    # Check keyword arguments (may override positional property name)
                    for kw in deco_call.keywords or []:
                        if kw.arg == 'property':
                            # property kwarg overrides positional arg
                            prop_name = _extract_constant(kw.value)
                        elif kw.arg == 'name':
                            # Legacy form: name kwarg for attribute name
                            key_name = _extract_constant(kw.value)
                        elif kw.arg == 'value':
                            # Legacy form: value kwarg for attribute value
                            key_value = _extract_constant(kw.value)
                        elif kw.arg == 'hint':
                            # Special handling for hint kwarg - convert AST node to string
                            # hint can be a complex type expression (Dict[str, Any], List[Any], etc.)
                            hint_str = _safe_unparse(kw.value)
                            if hint_str:
                                # Store the unparsed string representation
                                additional_kwargs['hint'] = hint_str
                        elif kw.arg:  # Only process if kw.arg is not None
                            # Collect all other kwargs (description, minimum, maximum, etc.)
                            kwarg_value = _extract_constant(kw.value)
                            if kwarg_value is not None:
                                additional_kwargs[kw.arg] = kwarg_value

                    if not isinstance(prop_name, str):
                        continue
                    if prop_name not in property_decorators:
                        property_decorators[prop_name] = {}
                    
                    # Handle legacy name/value pair if present
                    if isinstance(key_name, str):
                        property_decorators[prop_name][key_name] = key_value
                    
                    # Add all additional kwargs (preferred form)
                    property_decorators[prop_name].update(additional_kwargs)
                elif deco_name == 'component':
                    if deco_call and deco_call.args:
                        first_arg = _extract_constant(deco_call.args[0])
                        if isinstance(first_arg, str):
                            comp_name = first_arg
                    elif not deco_call:
                        comp_name = cls.name
                    for kw in (deco_call.keywords if deco_call else []) or []:
                        if kw.arg == 'name':
                            kw_name = _extract_constant(kw.value)
                            if isinstance(kw_name, str):
                                comp_name = kw_name
                        elif kw.arg == 'description':
                            kw_desc = _extract_constant(kw.value)
                            if isinstance(kw_desc, str):
                                description = kw_desc
                elif deco_name == 'attribute':
                    if not deco_call:
                        continue
                    attr_name: Optional[str] = None
                    attr_value: Any = MISSING
                    if deco_call.args:
                        raw_name = _extract_constant(deco_call.args[0])
                        if isinstance(raw_name, str):
                            attr_name = raw_name
                    if deco_call.args and len(deco_call.args) > 1:
                        attr_value = _extract_constant(deco_call.args[1])
                    for kw in deco_call.keywords or []:
                        if kw.arg == 'name':
                            kw_name = _extract_constant(kw.value)
                            if isinstance(kw_name, str):
                                attr_name = kw_name
                        elif kw.arg == 'value':
                            attr_value = _extract_constant(kw.value)
                    if not attr_name:
                        continue
                    sanitized = _normalize_extension_key(attr_name)
                    if attr_value is MISSING:
                        attr_value = True
                    decorator_extensions[sanitized] = attr_value
                elif deco_name in attribute_aliases:
                    alias_name, alias_value = attribute_aliases[deco_name]
                    if not alias_name:
                        continue
                    sanitized = alias_name if alias_name.startswith('x-') else f"x-{alias_name}"
                    if alias_value is MISSING:
                        alias_value = True
                    decorator_extensions[sanitized] = alias_value
            if not comp_name:
                continue

            # Track models marked with openapi_exclude for removal from swagger
            if decorator_extensions.get('x-tacobot-exclude'):
                excluded_components.add(comp_name)
                continue

            # If we have a full schema override, use it directly
            if full_schema_override is not None:
                comp_schema = full_schema_override.copy()
                # Add description from decorator if not present in schema
                if description and 'description' not in comp_schema:
                    comp_schema['description'] = description
                if decorator_extensions:
                    comp_schema.update(decorator_extensions)
                components[comp_name] = comp_schema
                continue

            # Otherwise, proceed with object property extraction from __init__
            annotations: Dict[str, str] = {}
            for node in cls.body:
                if isinstance(node, ast.FunctionDef) and node.name == '__init__':
                    for stmt in node.body:
                        if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Attribute) and isinstance(stmt.target.value, ast.Name) and stmt.target.value.id == 'self':
                            attr = stmt.target.attr
                            if attr.startswith('_'): continue
                            anno = _safe_unparse(stmt.annotation) or ''
                            anno = _expand_type_aliases(anno, type_alias_map)
                            annotations[attr] = anno or 'string'
                        elif isinstance(stmt, ast.Assign):
                            for tgt in stmt.targets:
                                if isinstance(tgt, ast.Attribute) and isinstance(tgt.value, ast.Name) and tgt.value.id == 'self':
                                    attr = tgt.attr
                                    if attr.startswith('_'): continue
                                    if attr not in annotations:
                                        inferred = 'string'
                                        if isinstance(stmt.value, ast.Constant):
                                            if isinstance(stmt.value.value, bool): inferred = 'boolean'
                                            elif isinstance(stmt.value.value, int): inferred = 'integer'
                                            elif isinstance(stmt.value.value, float): inferred = 'number'
                                        annotations[attr] = inferred
            props: Dict[str, Any] = {}
            required: List[str] = []
            for attr, anno_str in annotations.items():
                anno_str = _expand_type_aliases(anno_str, type_alias_map)
                nullable = 'Optional' in anno_str or 'None' in anno_str
                typ = 'string'
                schema: Dict[str, Any] = {}

                # Check for Literal enum first (highest priority)
                if 'Literal[' in anno_str or 'typing.Literal[' in anno_str:
                    # Extract inside Literal[...] (greedy until closing ])
                    # Simple string parse; we avoid full AST of the annotation text.
                    lit_start = anno_str.find('Literal[')
                    if lit_start == -1:
                        lit_start = anno_str.find('typing.Literal[')
                    if lit_start != -1:
                        sub = anno_str[lit_start:]
                        # find matching closing bracket
                        end_idx = sub.find(']')
                        if end_idx != -1:
                            inner = sub[len('Literal['):end_idx]
                            # Split by comma, strip spaces/quotes
                            raw_vals = [v.strip() for v in inner.split(',') if v.strip()]
                            enum_vals: List[str] = []
                            for rv in raw_vals:
                                # Remove surrounding quotes if present
                                if (rv.startswith("'") and rv.endswith("'")) or (rv.startswith('"') and rv.endswith('"')):
                                    rv_clean = rv[1:-1]
                                else:
                                    rv_clean = rv
                                # Only include primitive literal strings (skip complex expressions)
                                if rv_clean and all(c.isalnum() or c in ('-','_','.') for c in rv_clean):
                                    enum_vals.append(rv_clean)
                            if enum_vals:
                                # If all literals are strings, ensure base type string
                                schema = {'type': 'string', 'enum': sorted(set(enum_vals))}

                # If not a Literal, check for primitive types (list first, then primitives)
                if not schema:  # Only if we haven't set a Literal enum schema
                    lower_anno = anno_str.lower()
                    if 'list' in anno_str or 'List' in anno_str:
                        typ = 'array'
                    elif 'dict' in lower_anno or 'mapping' in lower_anno:
                        typ = 'object'
                    elif 'int' in anno_str:
                        typ = 'integer'
                    elif 'bool' in anno_str:
                        typ = 'boolean'
                    elif 'float' in anno_str:
                        typ = 'number'
                    else:
                        # Check for standalone model class references (CamelCase classes)
                        # Extract potential class names from the annotation
                        model_pattern = r'\b([A-Z][A-Za-z0-9_]*)\b'
                        matches = re.findall(model_pattern, anno_str)

                        # Filter out common typing keywords and look for actual model class names
                        typing_keywords = {'Optional', 'Union', 'List', 'Dict', 'Any', 'Type', 'Callable', 'Tuple', 'Set', 'Literal'}
                        potential_models = [m for m in matches if m not in typing_keywords]

                        # If we found a potential model class name, use it as a $ref (unless it's a TypeVar)
                        if potential_models:
                            # Use the first potential model (most common case: single class reference)
                            model_name = potential_models[0]
                            # Check if this is a TypeVar - if so, check for hint, otherwise treat as object
                            if model_name in module_typevars:
                                # Check if property decorator has a 'hint' kwarg
                                hint_value = property_decorators.get(attr, {}).get('hint')
                                if hint_value is not None:
                                    # Resolve hint to schema
                                    hint_schema = _resolve_hint_to_schema(hint_value)
                                    if hint_schema:
                                        schema = hint_schema
                                    else:
                                        # Hint couldn't be resolved, fall back to object
                                        schema = {'type': 'object'}
                                else:
                                    # No hint provided, default to object
                                    schema = {'type': 'object'}
                            else:
                                schema = {'$ref': f'#/components/schemas/{model_name}'}
                        else:
                            # No TypeVar or model detected - default typ to 'string'
                            typ = 'string'
                            if typ == 'object':
                                schema = {'type': 'object'}
                            else:
                                # Default to string type
                                schema = {'type': typ}

                    # Only set type if we don't have a $ref and schema wasn't already set (e.g., from hint)
                    if not schema and '$ref' not in schema:
                        schema['type'] = typ
                if typ == 'array':
                    # Default item type is string, but upgrade to object if annotation implies list/dict of dicts
                    items_type = 'string'
                    lowered = anno_str.lower()
                    # Heuristic: presence of 'dict' inside the list annotation (e.g., List[Dict[str, Any]] or list[dict])
                    if 'dict' in lowered:
                        items_type = 'object'
                        schema['items'] = {'type': items_type}
                    else:
                        # Check for List[ModelClass] pattern to generate $ref
                        list_pattern = r'(?:List|list)\s*\[\s*([A-Za-z_][A-Za-z0-9_]*)\s*\]'
                        match = re.search(list_pattern, anno_str)
                        if match:
                            inner_type = match.group(1)
                            # Check if inner_type is a TypeVar - if so, check for hint, otherwise treat as object
                            if inner_type in module_typevars:
                                # Check if property decorator has a 'hint' kwarg
                                hint_value = property_decorators.get(attr, {}).get('hint')
                                if hint_value is not None:
                                    # Resolve hint to schema
                                    hint_schema = _resolve_hint_to_schema(hint_value)
                                    if hint_schema:
                                        # Extract items schema from hint if it's an array
                                        if hint_schema.get('type') == 'array' and 'items' in hint_schema:
                                            schema['items'] = hint_schema['items']
                                        else:
                                            # Hint is not an array, use it as items type
                                            schema['items'] = hint_schema
                                    else:
                                        # Hint couldn't be resolved, fall back to object
                                        schema['items'] = {'type': 'object'}
                                else:
                                    # No hint provided, default to object
                                    schema['items'] = {'type': 'object'}
                            # Check if this inner type will be or is a known component
                            # We need to look ahead in the processing or check if it's already processed
                            # For now, use heuristic: if it looks like a class name (CamelCase), assume it's a component
                            elif inner_type and inner_type[0].isupper():
                                schema['items'] = {'$ref': f'#/components/schemas/{inner_type}'}
                            else:
                                schema['items'] = {'type': items_type}
                        else:
                            schema['items'] = {'type': items_type}

                # Handle nullable properties - but not for $ref types (OpenAPI spec doesn't support nullable on $ref)
                if nullable and '$ref' not in schema:
                    schema['nullable'] = True
                # Merge in property metadata (currently description + future extensibility)
                meta = prop_meta.get(attr)
                if meta:
                    # Avoid overwriting core inferred keys unless explicitly different; description is additive
                    desc_val = meta.get('description') if isinstance(meta, dict) else None
                    if isinstance(desc_val, str):
                        schema['description'] = desc_val
                    # Allow enum override via metadata (if user wants manual control)
                    if 'enum' in meta and isinstance(meta['enum'], list):
                        schema['enum'] = meta['enum']
                    # Additional future keys can be shallow-copied if they don't collide.
                    for extra_k, extra_v in meta.items():
                        if extra_k not in schema:
                            schema[extra_k] = extra_v

                # Merge in @openapi.property decorator metadata
                # Skip 'hint' since it's only for type inference, not OpenAPI spec
                if attr in property_decorators:
                    for key, value in property_decorators[attr].items():
                        if key == 'hint':
                            continue  # hint is meta-attribute, not OpenAPI spec
                        if key not in schema or schema.get(key) is None:
                            schema[key] = value

                props[attr] = schema
                if not nullable:
                    required.append(attr)

            # Check for base classes to determine if we should use allOf
            openapi_base_classes = _extract_openapi_base_classes(cls, module_typevars)

            # Build the schema
            if openapi_base_classes:
                # Use allOf structure for inheritance
                comp_schema: Dict[str, Any] = {'allOf': []}

                # Add references to base class schemas
                for base_class_name in openapi_base_classes:
                    comp_schema['allOf'].append({'$ref': f'#/components/schemas/{base_class_name}'})

                # Add properties/required defined or overridden in this class
                subclass_schema: Dict[str, Any] = {}
                if props:
                    subclass_schema['properties'] = props
                if required:
                    subclass_schema['required'] = sorted(required)

                # Only add the subclass schema if it has content
                if subclass_schema:
                    comp_schema['allOf'].append(subclass_schema)

                # Add description and extensions at the top level (not inside allOf)
                if description:
                    comp_schema['description'] = description
                if decorator_extensions:
                    comp_schema.update(decorator_extensions)
            else:
                # No inheritance - use standard object schema
                comp_schema: Dict[str, Any] = {'type': 'object', 'properties': props}
                if required:
                    comp_schema['required'] = sorted(required)
                if description:
                    comp_schema['description'] = description
                if decorator_extensions:
                    comp_schema.update(decorator_extensions)

            components[comp_name] = comp_schema
    for alias_meta in TYPE_ALIAS_METADATA.values():
        defined_path_str = alias_meta.get('path')
        if not defined_path_str:
            continue
        try:
            defined_path = pathlib.Path(defined_path_str).resolve()
        except Exception:
            continue
        try:
            defined_path.relative_to(resolved_models_root)
        except ValueError:
            continue
        component_name = alias_meta.get('component')
        alias_name = alias_meta.get('alias')
        if not component_name or not alias_name:
            continue
        if component_name in components:
            continue
        annotation_str = alias_meta.get('annotation', '')
        expanded_annotation = _expand_type_aliases(annotation_str, GLOBAL_TYPE_ALIASES)

        # Check if anyof flag is set in metadata
        anyof_flag = alias_meta.get('anyof', False)

        # Unwrap Optional to detect nullable unions
        unwrapped_annotation, is_nullable = _unwrap_optional(expanded_annotation)

        # Build schema with anyof context if Union type
        if anyof_flag:
            # For union types, extract with anyOf instead of oneOf
            union_schema = _extract_union_schema(unwrapped_annotation, anyof=True, nullable=is_nullable)
            schema = union_schema if union_schema else _build_schema_from_annotation(expanded_annotation)
        else:
            # Use unwrapped annotation for schema building (nullable already handled in _build_schema_from_annotation)
            schema = _build_schema_from_annotation(expanded_annotation)

        description = str(alias_meta.get('description')) if 'description' in alias_meta else ''
        if isinstance(description, str):
            schema['description'] = description
        default_value = alias_meta.get('default', MISSING)
        if default_value is not MISSING:
            schema['default'] = default_value
        extensions = alias_meta.get('extensions') or {}
        for ext_key, ext_value in extensions.items():
            schema[_normalize_extension_key(ext_key)] = ext_value
        components[component_name] = schema
    return components, excluded_components
