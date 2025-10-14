#!/usr/bin/env python
"""OpenAPI / Swagger synchronization & coverage utility.

Summary
=======
This module scans the TacoBot HTTP handler tree for docstring‑embedded OpenAPI
blocks (delimited by ``>>>openapi`` / ``<<<openapi`` by default) and keeps the canonical
Swagger specification file (``.swagger.v1.yaml``) in sync. It can:

* Detect drift (missing / changed operations) and show a colorized unified diff.
* Optionally apply the changes to the swagger file (``--fix`` mode).
* Generate documentation coverage metrics (JSON / plain text / Cobertura XML).
* Produce a GitHub Actions friendly Markdown summary (written either to the
    path passed via ``--markdown-summary`` and/or to the file referenced by the
    ``GITHUB_STEP_SUMMARY`` environment variable).
* List orphan swagger paths (present in spec, absent in code) and ignored
    handlers (annotated with ``@openapi: ignore`` in their docstrings / module
    docstring).
* Emit per‑endpoint diagnostics and suggestions to improve documentation.

Why this exists
---------------
Manual maintenance of OpenAPI specs drifts quickly. By colocating a minimal
YAML fragment alongside each handler we enable:
* Localized review of API surface changes (git diff shows both code + spec).
* Simple per‑method coverage accounting (each handler counts as one logical
    line for Cobertura reports → easy CI gates).
* Low‑friction incremental documentation (start with summary + responses; add
    parameters later without touching a large central file).

Key Concepts
------------
* Endpoint collection: ``collect_endpoints`` walks the handlers root gathering
    decorated methods using ``uri_mapping`` / ``uri_variable_mapping``. Pattern
    based mappings (``uri_pattern_mapping``) are *ignored* for swagger sync but
    are tracked as intentionally skipped.
* Supported YAML keys inside an openapi block are constrained to
    ``SUPPORTED_KEYS`` for predictable merges. Any unspecified response schema
    defaults to ``200: { description: "OK" }``.
* Merge strategy: Per path+method operation objects are replaced atomically if
    any field differs (simpler + deterministic vs. deep diffs).
* Coverage: Two dimensions are reported – documentation presence (has an
    ``>>>openapi <<<openapi`` block) and swagger synchronization (operation also present &
    structurally identical). A third list shows swagger‑only operations.
* Output directory: All artifact paths passed via CLI are resolved relative to
    ``--output-directory`` (default: ``.``). If that directory lives inside the
    repository and is *not* named ``reports`` a warning is printed to discourage
    accidental commits of ephemeral outputs.

CLI Synopsis
------------
        python scripts/swagger_sync.py --check \
                --handlers-root bot/lib/http/handlers/ \
                --swagger-file .swagger.v1.yaml \
                --coverage-report openapi_coverage.json \
                --coverage-format json \
                --markdown-summary openapi_summary.md

Important Flags (abridged):
* ``--fix``: Persist merged swagger changes.
* ``--check``: (default) Do not write; exit non‑zero on drift or coverage fail.
* ``--coverage-report`` + ``--coverage-format``: Emit coverage in json|text|cobertura.
* ``--fail-on-coverage-below``: Gate CI (accepts 0‑1 or 0‑100 style thresholds).
* ``--show-orphans`` / ``--show-ignored`` / ``--show-missing-blocks``: Additional diagnostics for paths/components.
* ``--color {auto,always,never}``: Control ANSI colorization of diffs.
* ``--output-directory``: Base path for report + summary artifacts.

Exit Codes
----------
* 0: Swagger is in sync and coverage threshold (if any) satisfied.
* 1: Drift detected OR coverage threshold not met.
* (Other): Early parameter / file validation errors raise ``SystemExit``.

Environment Integration
-----------------------
If ``GITHUB_STEP_SUMMARY`` is set the Markdown summary is appended there so the
GitHub Actions job summary surfaces drift & coverage without inspecting logs.

Migration Note
--------------
This file supersedes the legacy ``scripts/sync_endpoints.py`` (now deleted).
All functionality was carried forward; only the entrypoint name changed to
better reflect its purpose (``swagger_sync``) and to avoid persistent diffs on
future enhancements.

Potential Future Enhancements
-----------------------------
* Automatic component schema stubs (guarded behind a flag).
* Pagination / filtering hints for large collections.
* Security scheme enforcement summary.
* Automatic pruning suggestions for stale swagger‑only paths older than N days.

Method‑rooted OpenAPI Blocks
----------------------------
Two docstring block layouts are supported between the `>>>openapi` / `<<<openapi` delimiters:

1. Flat (legacy) – operation fields live at the top level (``summary``, ``tags``, ``parameters``, ``responses`` …):

        ```yaml
        >>>openapi
        summary: List items
        tags: [items]
        responses:
            '200': { description: OK }
        <<<openapi
        ```

2. Method‑rooted – top‑level keys are HTTP methods whose values are operation objects. This is useful
     when a single handler function is decorated for multiple methods and you want different docs per method:

        ```yaml
        >>>openapi
        get:
            summary: List items
            tags: [items]
            responses:
                '200': { description: OK }
        post:
            summary: Create item
            tags: [items]
            requestBody:
                required: true
                content:
                    application/json:
                        schema: { $ref: '#/components/schemas/NewItem' }
            responses:
                '200': { description: Created }
    <<<openapi
        ```

Detection Logic
---------------
If every top‑level key inside the block that matches an HTTP verb (``get``, ``post``, ``put``, ``delete``,
``patch``, ``options``, ``head``) forms a non‑empty set, the block is treated as *method‑rooted* and the
sub‑mapping corresponding to the decorator’s method is selected. Otherwise the parser assumes the *flat*
style and uses the whole mapping as the operation object.

Rules & Caveats
---------------
* Only keys in ``SUPPORTED_KEYS`` inside the chosen mapping are forwarded to the swagger operation.
* Mixing styles (e.g. having both ``summary:`` and ``get:`` at the same top level) is discouraged; any
    flat keys are ignored when method‑rooted keys are present.
* Omitted ``responses`` results in a default ``200`` with description "OK" (same as flat mode).
* A method listed in decorators but missing from the method‑rooted block yields an empty meta mapping
    (effectively no OpenAPI block for that method). Add at least a ``summary`` + ``responses`` to count
    towards coverage.
* See ``tests/test_swagger_sync_method_rooted.py`` for an executable example.
* ``--strict`` flag: When supplied to the CLI, any HTTP verb keys present in a method‑rooted block that
    are NOT declared in the decorator's ``method=`` list cause the run to fail fast (non‑zero exit).
    Without ``--strict`` these are downgraded to warnings and the extraneous verb definitions are ignored.

Model Component Auto‑Generation
-------------------------------
Classes in the models root (default ``bot/lib/models``) decorated with
``@openapi_model("ComponentName", description="...")`` are translated into
basic ``components.schemas`` entries.

Two modes are supported:

1. **Object Schema Mode (Default)**: Property extraction is heuristic: any
   ``self.<attr>`` assignment (optionally with an annotation) inside ``__init__``
   becomes a schema property. Types are inferred from annotations or literal
   defaults (int → integer, bool → boolean, float → number, list → array, else
   string). Optional/nullable detection is naive (presence of ``Optional`` / ``None``
   in the annotation string). Complex/nested objects are intentionally collapsed
   to ``string`` for safety—refine manually in the swagger file if richer schemas
   are required.

2. **Simple Type Schema Mode**: When the class docstring contains a ``>>>openapi``
   block with a ``type`` field but no ``properties`` field, the entire block
   is used as the complete schema definition. This allows for simple types like
   enums, primitives with defaults, etc.

Disable this behavior with ``--no-model-components`` or change
the scan root via ``--models-root``.

Object Schema Example::

    from bot.lib.models.openapi import openapi_model
    from typing import Optional

    @openapi_model("DiscordChannel", description="Discord text/voice channel snapshot")
    class DiscordChannel:
        def __init__(self, id: int, name: str, topic: Optional[str] = None, nsfw: bool = False, position: int = 0):
            self.id: int = id
            self.name: str = name
            self.topic: Optional[str] = topic  # Optional → nullable true (and not required)
            self.nsfw: bool = nsfw
            self.position: int = position
            self.permission_overwrites: list[str] = []  # list → type: array, items: string

Generated YAML (excerpt)::

    components:
      schemas:
        DiscordChannel:
          type: object
          description: Discord text/voice channel snapshot
          properties:
            id: { type: integer }
            name: { type: string }
            topic: { type: string, nullable: true }
            nsfw: { type: boolean }
            position: { type: integer }
            permission_overwrites:
              type: array
              items: { type: string }
          required: [id, name, nsfw, position, permission_overwrites]

Simple Type Schema Example::

    from bot.lib.models.openapi import openapi_model

    @openapi_model("MinecraftWorld", description="Represents a Minecraft world")
    class MinecraftWorld:
        '''Represents a Minecraft world managed by TacoBot.

        >>>openapi
        type: string
        default: taco_atm10
        enum:
          - taco_atm8
          - taco_atm9
          - taco_atm10
        <<<openapi
        '''

Generated YAML (excerpt)::

    components:
      schemas:
        MinecraftWorld:
          type: string
          default: taco_atm10
          description: Represents a Minecraft world
          enum:
            - taco_atm8
            - taco_atm9
            - taco_atm10

Inference Rules:
* Required unless annotation contains ``Optional`` or ``None``.
* ``int``→integer, ``bool``→boolean, ``float``→number, ``list[List]``→array (items default to string).
* Nullable flag added when ``Optional``/``None`` present.
* Private attributes (leading ``_``) ignored.
* Unknown / complex types collapse to ``string`` (manually refine in swagger if needed).

Drift Warnings:
If the inferred schema differs from the existing component a unified diff is printed (colorized when enabled):

    WARNING: Model schema drift detected for component 'DiscordChannel'.
    --- a/components.schemas.DiscordChannel
    +++ b/components.schemas.DiscordChannel
    @@
    -  topic: { type: string }
    +  topic: { type: string, nullable: true }

Accept by running with ``--fix`` and committing the updated ``.swagger.v1.yaml``.

Limitations: no recursion, no enum/format inference, arrays always ``items: {type: string}``. Edit richer details manually.
Tests: see ``tests/test_swagger_sync_model_components.py``.

Internal API (selected)
-----------------------
* ``collect_endpoints`` → List[Endpoint], plus ignored list
* ``merge`` → (updated_swagger, changed?, notes, diffs)
* ``detect_orphans`` → list[str] of swagger‑only operations
* ``_generate_coverage`` / ``_compute_coverage`` → metrics + per‑endpoint records
* ``_diff_operations`` → unified diff lines for a single operation

The underscore‑prefixed helpers are intentionally internal; tests import them
only where fine‑grained verification adds reliability (e.g. color behavior).

Usage Tip
---------
Run in check mode locally before committing:
        python scripts/swagger_sync.py --check --show-missing-blocks --coverage-report reports/openapi/coverage.json --output-directory reports/openapi

Then, if drift is reported and acceptable, apply:
        python scripts/swagger_sync.py --fix

Implementation detail: colorization is suppressed automatically when stdout is
not a TTY (unless ``--color=always``). The global ``DISABLE_COLOR`` flag keeps
the cost of color decisions minimal in inner loops.
"""

from __future__ import annotations

# Copy of original script content (kept identical for rename) -----------------
import ast
import argparse
import pathlib
import re
import sys
import textwrap
import difflib
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import fnmatch
import time
import json
from io import StringIO

try:
    from ruamel.yaml import YAML  # type: ignore
    # Create a YAML instance with better formatting and comment preservation
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.map_indent = 2
    yaml.sequence_indent = 4
    yaml.sequence_dash_offset = 2
    yaml.width = 4096  # Prevent line wrapping for long lines
except Exception as e:  # pragma: no cover
    # ANSI constants not declared yet at this point; print plain message
    print("Missing dependency ruamel.yaml. Install with: pip install ruamel.yaml", file=sys.stderr)
    raise

# Default (new) delimiters and legacy fallback pattern. The regex will be built at runtime
# to allow user overrides via CLI flags.
DEFAULT_OPENAPI_START = ">>>openapi"
DEFAULT_OPENAPI_END = "<<<openapi"

def build_openapi_block_re(start_marker: str, end_marker: str) -> re.Pattern[str]:
    # Escape user-provided markers for safe regex embedding; capture lazily.
    sm = re.escape(start_marker)
    em = re.escape(end_marker)
    return re.compile(rf"{sm}\s*(.*?)\s*{em}", re.DOTALL | re.IGNORECASE)

# Initialized later in main() after argument parsing; provide a module-level default for import-time uses (tests may override).
OPENAPI_BLOCK_RE = build_openapi_block_re(DEFAULT_OPENAPI_START, DEFAULT_OPENAPI_END)
DEFAULT_HANDLERS_ROOT = pathlib.Path("bot/lib/http/handlers/")
DEFAULT_MODELS_ROOT = pathlib.Path("bot/lib/models/")
DEFAULT_SWAGGER_FILE = pathlib.Path(".swagger.v1.yaml")
SUPPORTED_KEYS = {"summary", "description", "tags", "parameters", "requestBody", "responses", "security"}
IGNORE_MARKER = "@openapi: ignore"
MODEL_DECORATOR_ATTR = '__openapi_component__'
MISSING = object()
TYPE_ALIAS_CACHE: Dict[pathlib.Path, Dict[str, str]] = {}
TYPE_ALIAS_METADATA: Dict[str, Dict[str, Any]] = {}
GLOBAL_TYPE_ALIASES: Dict[str, str] = {}


def _decorator_identifier(node: ast.AST) -> Optional[str]:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _extract_constant(node: ast.AST) -> Any:
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        operand = getattr(node, 'operand', None)
        if isinstance(operand, ast.Constant) and isinstance(operand.value, (int, float)):
            return -operand.value
    return MISSING


def _safe_unparse(node: Optional[ast.AST]) -> Optional[str]:
    if node is None:
        return None
    if hasattr(ast, 'unparse'):
        try:
            return ast.unparse(node)
        except Exception:
            return None
    return None


def _normalize_extension_key(name: str) -> str:
    return name if name.startswith('x-') else f"x-{name}"


def _extract_literal_schema(anno_str: str) -> Optional[Dict[str, Any]]:
    if 'Literal[' not in anno_str and 'typing.Literal[' not in anno_str:
        return None
    lit_start = anno_str.find('Literal[')
    if lit_start == -1:
        lit_start = anno_str.find('typing.Literal[')
    sub = anno_str[lit_start:]
    end_idx = sub.find(']')
    if end_idx == -1:
        return None
    inner = sub[len('Literal['):end_idx]
    raw_vals = [v.strip() for v in inner.split(',') if v.strip()]
    enum_vals: List[str] = []
    for rv in raw_vals:
        if (rv.startswith("'") and rv.endswith("'")) or (rv.startswith('"') and rv.endswith('"')):
            rv_clean = rv[1:-1]
        else:
            rv_clean = rv
        if rv_clean and all(c.isalnum() or c in ('-','_','.') for c in rv_clean):
            enum_vals.append(rv_clean)
    if not enum_vals:
        return None
    return {'type': 'string', 'enum': sorted(set(enum_vals))}


def _extract_constant_dict(node: ast.AST) -> Optional[Dict[str, Any]]:
    if not isinstance(node, ast.Dict):
        return None
    result: Dict[str, Any] = {}
    for key_node, value_node in zip(node.keys, node.values):
        if key_node is None or value_node is None:
            return None
        key = _extract_constant(key_node)
        if key is MISSING or not isinstance(key, str):
            return None
        value = _extract_constant(value_node)
        if value is MISSING:
            return None
        result[key] = value
    return result


def _build_schema_from_annotation(anno_str: str) -> Dict[str, Any]:
    schema = _extract_literal_schema(anno_str) or {}
    if schema:
        return schema
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


def _discover_attribute_aliases(models_root: pathlib.Path) -> Dict[str, Tuple[Optional[str], Any]]:
    alias_map: Dict[str, Tuple[Optional[str], Any]] = {}
    candidates: List[pathlib.Path] = []
    potential = (models_root / 'openapi.py').resolve()
    candidates.append(potential)
    default_candidate = (DEFAULT_MODELS_ROOT / 'openapi.py').resolve()
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
            if _decorator_identifier(ret_value.func) != 'openapi_attribute':
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

        # Only include if it looks like a class name (starts with uppercase)
        if base_name and base_name[0].isupper():
            base_classes.append(base_name)

    return base_classes


def _collect_type_aliases_from_ast(module: ast.AST, file_path: pathlib.Path) -> Dict[str, str]:
    global TYPE_ALIAS_METADATA, GLOBAL_TYPE_ALIASES
    alias_map: Dict[str, str] = {}
    for node in getattr(module, 'body', []):
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if not _is_type_alias_annotation(node.annotation):
                continue
            alias_name = node.target.id
            value_node = node.value
            if isinstance(value_node, ast.Call) and isinstance(value_node.func, ast.Call):
                factory_call = value_node.func
                if _decorator_identifier(factory_call.func) == 'openapi_type_alias':
                    component_name: Optional[str] = None
                    description: Optional[str] = None
                    default_value: Any = MISSING
                    managed_flag = False
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
                    extensions: Dict[str, Any] = {}
                    if managed_flag:
                        extensions['x-tacobot-managed'] = True
                    for k, v in attr_map.items():
                        extensions[_normalize_extension_key(k)] = v
                    if extensions:
                        meta['extensions'] = extensions
                    TYPE_ALIAS_METADATA[alias_name] = meta
                    continue
            value_str = _safe_unparse(node.value)
            if value_str:
                alias_map[alias_name] = value_str
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

@dataclass
class Endpoint:
    path: str
    method: str  # lower case (get, post, ...)
    meta: Dict[str, Any]
    function: str
    file: pathlib.Path

    def to_openapi_operation(self) -> Dict[str, Any]:
        op: Dict[str, Any] = {}
        for k in SUPPORTED_KEYS:
            if k in self.meta:
                op[k] = self.meta[k]
        op.setdefault("responses", {"200": {"description": "OK"}})
        if "tags" in op and isinstance(op["tags"], str):
            op["tags"] = [op["tags"]]
        return op


def extract_openapi_block(doc: Optional[str]) -> Dict[str, Any]:
    if not doc:
        return {}
    m = OPENAPI_BLOCK_RE.search(doc)
    if not m:
        return {}
    raw = m.group(1)
    try:
        data = yaml.load(raw) or {}
        if not isinstance(data, dict):
            raise ValueError("OpenAPI block must be a mapping")
        return data
    except Exception as e:
        raise ValueError(f"Failed parsing >>>openapi <<<openapi block: {e}\nBlock contents:\n{textwrap.indent(raw, '    ')}") from e


def resolve_path_literal(node: ast.AST) -> Optional[str]:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):  # f-string
        parts: List[str] = []
        for value in node.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                parts.append(value.value)
            elif isinstance(value, ast.FormattedValue):
                if isinstance(value.value, ast.Name):
                    name = value.value.id
                    if name == "API_VERSION":
                        parts.append("v1")
                    else:
                        return None
                else:
                    return None
            else:
                return None
        return ''.join(parts)
    return None


def collect_endpoints(handlers_root: pathlib.Path, *, strict: bool = False, ignore_file_globs: Optional[List[str]] = None) -> Tuple[List[Endpoint], List[Tuple[str, str, pathlib.Path, str]]]:
    endpoints: List[Endpoint] = []
    ignored: List[Tuple[str, str, pathlib.Path, str]] = []
    ignore_file_globs = ignore_file_globs or []
    for py_file in handlers_root.rglob("*.py"):
        rel_str = str(py_file.relative_to(handlers_root)).replace('\\', '/')
        if any(fnmatch.fnmatch(rel_str, pattern) or fnmatch.fnmatch(py_file.name, pattern) for pattern in ignore_file_globs):
            continue
        try:
            src = py_file.read_text(encoding="utf-8")
        except Exception:
            continue
        try:
            module = ast.parse(src, filename=str(py_file))
        except SyntaxError as e:
            print(f"WARNING: Skipping {py_file} due to syntax error: {e}", file=sys.stderr)
            continue
        module_doc = ast.get_docstring(module) or ""
        module_ignored = IGNORE_MARKER in module_doc
        for node in module.body:
            if not isinstance(node, ast.ClassDef):
                continue
            # Include both sync and async handler methods
            for fn in [n for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]:
                fn_doc = ast.get_docstring(fn) or ""
                fn_ignored = IGNORE_MARKER in fn_doc
                for deco in fn.decorator_list:
                    if not isinstance(deco, ast.Call):
                        continue
                    deco_name = getattr(deco.func, 'id', '')
                    if deco_name not in {'uri_variable_mapping', 'uri_mapping', 'uri_pattern_mapping'}:
                        continue
                    if not deco.args:
                        continue
                    path_str = resolve_path_literal(deco.args[0])
                    if not path_str:
                        continue
                    methods: List[str] = ['get']
                    for kw in deco.keywords or []:
                        if kw.arg == 'method':
                            if isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                                methods = [kw.value.value.lower()]
                            elif isinstance(kw.value, (ast.List, ast.Tuple)):
                                collected: List[str] = []
                                for elt in kw.value.elts:
                                    if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                        collected.append(elt.value.lower())
                                if collected:
                                    methods = collected
                    if deco_name == 'uri_pattern_mapping':
                        for m in methods:
                            ignored.append((path_str, m, py_file, fn.name))
                        continue
                    # Parse the OpenAPI block once per function; support two styles:
                    # 1. Flat operation keys (summary, tags, parameters, ...)
                    # 2. Method-rooted mapping (get: {...}, post: {...}, ...)
                    raw_meta_full = extract_openapi_block(fn_doc)
                    http_method_keys = {k for k in (raw_meta_full.keys() if isinstance(raw_meta_full, dict) else []) if k.lower() in {"get","post","put","delete","patch","options","head"}}
                    # Validation: if docstring declares method-rooted keys not present in decorator list.
                    if http_method_keys:
                        declared = set(methods)
                        extra = {mk.lower() for mk in http_method_keys if mk.lower() not in declared}
                        if extra:
                            msg = (
                                f"WARNING: OpenAPI docstring method(s) {sorted(extra)} not declared in decorator for {fn.name} "
                                f"at {py_file}:{fn.lineno}. Decorator methods: {sorted(declared)}"
                            )
                            if strict:
                                raise ValueError(msg.replace("WARNING: ", ""))
                            else:
                                print(msg, file=sys.stderr)
                    for m in methods:
                        if module_ignored or fn_ignored:
                            ignored.append((path_str, m, py_file, fn.name))
                            continue
                        if http_method_keys:
                            # Method-rooted style: select the matching sub-dict for this handler method.
                            chosen: Dict[str, Any] = {}
                            for mk, mv in raw_meta_full.items():  # type: ignore[union-attr]
                                if mk.lower() == m and isinstance(mv, dict):
                                    chosen = mv
                                    break
                            meta = chosen
                        else:
                            meta = raw_meta_full if isinstance(raw_meta_full, dict) else {}
                        endpoints.append(Endpoint(path=path_str, method=m, meta=meta, function=fn.name, file=py_file))
    return endpoints, ignored


def collect_model_components(models_root: pathlib.Path) -> tuple[Dict[str, Dict[str, Any]], set[str]]:
    """Collect model classes decorated with @openapi_model and derive naive schemas.

    Strategy (pure AST – no imports executed):
    * Find classes with an @openapi_model decorator.
    * Extract component name (first positional arg or class name fallback) and description kwarg.
    * Inside __init__, record any self.<attr> AnnAssign or Assign targets (skip private leading _).
    * Infer primitive types from annotations / literal defaults; mark non-optional as required.
    Limitations: nested / complex types collapsed to string; arrays default items.type=string.

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
            for deco in cls.decorator_list:
                deco_call: Optional[ast.Call] = deco if isinstance(deco, ast.Call) else None
                deco_name = None
                if isinstance(deco, ast.Call):
                    deco_name = _decorator_identifier(deco.func)
                else:
                    deco_name = _decorator_identifier(deco)
                if not deco_name:
                    continue
                if deco_name == 'openapi_model':
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
                elif deco_name == 'openapi_attribute':
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
                            # Check if this is a TypeVar - if so, treat as object
                            if model_name in module_typevars:
                                schema = {'type': 'object'}
                            else:
                                schema = {'$ref': f'#/components/schemas/{model_name}'}
                        else:
                            if typ == 'object':
                                schema = {'type': 'object'}
                            else:
                                # Default to string type
                                schema = {'type': typ}

                    # Only set type if we don't have a $ref
                    if '$ref' not in schema:
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
                            # Check if inner_type is a TypeVar - if so, treat as object
                            if inner_type in module_typevars:
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


def load_swagger(swagger_file: pathlib.Path) -> Dict[str, Any]:
    if not swagger_file.exists():
        raise SystemExit(f"Swagger file {swagger_file} not found.")
    return yaml.load(swagger_file.read_text(encoding="utf-8")) or {}


ANSI_GREEN = "\x1b[32m"
ANSI_RED = "\x1b[31m"
ANSI_CYAN = "\x1b[36m"
ANSI_YELLOW = "\x1b[33m"
ANSI_RESET = "\x1b[0m"

DISABLE_COLOR = False


def _colorize_unified(diff_lines: List[str]) -> List[str]:
    colored: List[str] = []
    for line in diff_lines:
        if DISABLE_COLOR:
            colored.append(line)
            continue
        if line.startswith('+++ ') or line.startswith('--- ') or line.startswith('@@ '):
            colored.append(f"{ANSI_CYAN}{line}{ANSI_RESET}")
        elif line.startswith('+') and not line.startswith('+++ '):
            colored.append(f"{ANSI_GREEN}{line}{ANSI_RESET}")
        elif line.startswith('-') and not line.startswith('--- '):
            colored.append(f"{ANSI_RED}{line}{ANSI_RESET}")
        else:
            colored.append(line)
    return colored


def _dump_operation_yaml(op: Dict[str, Any]) -> List[str]:
    from io import StringIO as StringIOModule
    stream = StringIOModule()
    yaml.dump(op, stream)
    dumped = stream.getvalue().rstrip().splitlines()
    return [l if l.strip() else '' for l in dumped]


def _diff_operations(existing: Optional[Dict[str, Any]], new: Dict[str, Any], *, op_id: str) -> List[str]:
    if existing is None:
        existing_lines: List[str] = []
    else:
        existing_lines = _dump_operation_yaml(existing)
    new_lines = _dump_operation_yaml(new)
    header_from = f"a/{op_id}"
    header_to = f"b/{op_id}"
    diff = list(difflib.unified_diff(existing_lines, new_lines, fromfile=header_from, tofile=header_to, lineterm=''))
    if not diff:
        return []
    return _colorize_unified(diff)


def merge(swagger: Dict[str, Any], endpoints: List[Endpoint]) -> Tuple[Dict[str, Any], bool, List[str], Dict[Tuple[str, str], List[str]]]:
    paths = swagger.setdefault('paths', {})
    changed = False
    notes: List[str] = []
    diffs: Dict[Tuple[str, str], List[str]] = {}
    for ep in endpoints:
        p_entry = paths.setdefault(ep.path, {})
        new_op = ep.to_openapi_operation()
        existing = p_entry.get(ep.method)
        if existing != new_op:
            op_id = f"{ep.path}#{ep.method}"
            diff_lines = _diff_operations(existing, new_op, op_id=op_id)
            diffs[(ep.path, ep.method)] = diff_lines
            p_entry[ep.method] = new_op
            changed = True
            notes.append(f"Updated {ep.method.upper()} {ep.path} from {ep.file.name}:{ep.function}")
    return swagger, changed, notes, diffs


def detect_orphans(swagger: Dict[str, Any], endpoints: List[Endpoint], model_components: Optional[Dict[str, Dict[str, Any]]] = None) -> list[str]:
    code_pairs = {(e.path, e.method) for e in endpoints}
    orphan_notes: list[str] = []

    # Check for orphaned paths (present in swagger but no handler)
    for path, methods in swagger.get('paths', {}).items():
        if not isinstance(methods, dict):
            continue
        for m in methods.keys():
            if m.lower() in {"get","post","put","delete","patch","options","head"}:
                if (path, m.lower()) not in code_pairs:
                    orphan_notes.append(f"Path present only in swagger (no handler): {m.upper()} {path}")

    # Check for orphaned components (present in swagger but no model class)
    if model_components is not None:
        swagger_components = swagger.get('components', {}).get('schemas', {})
        if swagger_components:
            model_component_names = set(model_components.keys())
            for component_name in swagger_components.keys():
                if component_name not in model_component_names:
                    orphan_notes.append(f"Component present only in swagger (no model class): {component_name}")

    return orphan_notes


def _generate_coverage(endpoints: List[Endpoint], ignored: List[Tuple[str,str,pathlib.Path,str]], swagger: Dict[str, Any], *, report_path: pathlib.Path, fmt: str, extra_summary: Optional[Dict[str, Any]] = None) -> None:
    summary, endpoint_records, swagger_only = _compute_coverage(endpoints, ignored, swagger)
    if extra_summary:
        summary.update(extra_summary)
    if fmt == 'json':
        # If model component metrics were added upstream they will already be in summary.
        payload = {
            'summary': summary,
            'endpoints': endpoint_records,
            'swagger_only': swagger_only,
            'generated_at': int(time.time()),
            'format': 'tacobot-openapi-coverage-v1'
        }
        report_path.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    elif fmt == 'text':
        lines = ["OPENAPI COVERAGE REPORT", ""]
        lines.append(f"Handlers (considered): {summary['handlers_total']}")
        lines.append(f"Ignored: {summary['ignored_total']}")
        lines.append(f"With block: {summary['with_openapi_block']} ({summary['coverage_rate_handlers_with_block']:.1%})")
        lines.append(f"In swagger: {summary['handlers_in_swagger']} ({summary['coverage_rate_handlers_in_swagger']:.1%})")
        lines.append(f"Definition matches: {summary['definition_matches']}/{summary['with_openapi_block']} ({summary['operation_definition_match_rate']:.1%})")
        lines.append(f"Swagger only operations: {summary['swagger_only_operations']}")
        lines.append("")
        lines.append("Per-endpoint:")
        for rec in endpoint_records:
            status = []
            if rec['ignored']: status.append('IGNORED')
            if rec['has_openapi_block']: status.append('BLOCK')
            if rec['in_swagger']: status.append('SWAGGER')
            if rec['definition_matches']: status.append('MATCH')
            if rec['missing_in_swagger']: status.append('MISSING_SWAGGER')
            lines.append(f" - {rec['method'].upper()} {rec['path']} :: {'|'.join(status) if status else 'NONE'}")
        if swagger_only:
            lines.append("")
            lines.append("Swagger only:")
            for so in swagger_only:
                lines.append(f" - {so['method'].upper()} {so['path']}")
        report_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    elif fmt == 'cobertura':
        try:
            from xml.etree.ElementTree import Element, SubElement, tostring  # noqa: WPS433
        except Exception as e:  # pragma: no cover
            raise SystemExit(f"XML generation failed: {e}")
        lines_valid = summary['handlers_total'] + summary['swagger_only_operations']
        lines_covered = summary['with_openapi_block']
        line_rate = (lines_covered / lines_valid) if lines_valid else 0.0
        root = Element('coverage', {
            'lines-valid': str(lines_valid),
            'lines-covered': str(lines_covered),
            'line-rate': f"{line_rate:.4f}",
            'branches-covered': '0',
            'branches-valid': '0',
            'branch-rate': '0.0',
            'version': 'tacobot-openapi-coverage-v1',
            'timestamp': str(int(time.time()))
        })
        # Custom properties for supplementary metrics (consumed by CI dashboards)
        props = SubElement(root, 'properties')
        def _prop(name: str, value: Any) -> None:  # noqa: ANN001
            SubElement(props, 'property', {'name': name, 'value': str(value)})
        _prop('handlers_total', summary['handlers_total'])
        _prop('ignored_handlers', summary['ignored_total'])
        _prop('swagger_only_operations', summary['swagger_only_operations'])
        _prop('model_components_generated', summary.get('model_components_generated', 0))
        _prop('model_components_existing_not_generated', summary.get('model_components_existing_not_generated', 0))
        pkgs = SubElement(root, 'packages')
        pkg = SubElement(pkgs, 'package', {'name': 'openapi.handlers', 'line-rate': f"{line_rate:.4f}", 'branch-rate': '0.0', 'complexity': '0'})
        classes = SubElement(pkg, 'classes')
        line_number = 0
        for rec in endpoint_records:
            if rec['ignored']:
                continue
            line_number += 1
            covered = '1' if (rec['has_openapi_block']) else '0'
            cls = SubElement(classes, 'class', {
                'name': f"{rec['method'].upper()} {rec['path']}",
                'filename': rec['file'],
                'line-rate': '1.0' if covered == '1' else '0.0',
                'branch-rate': '0.0',
                'complexity': '0'
            })
            lines_el = SubElement(cls, 'lines')
            SubElement(lines_el, 'line', {
                'number': str(line_number),
                'hits': covered,
                'branch': 'false'
            })
        for so in swagger_only:
            line_number += 1
            cls = SubElement(classes, 'class', {
                'name': f"{so['method'].upper()} {so['path']}",
                'filename': '<swagger-only>',
                'line-rate': '0.0',
                'branch-rate': '0.0',
                'complexity': '0'
            })
            lines_el = SubElement(cls, 'lines')
            SubElement(lines_el, 'line', {
                'number': str(line_number),
                'hits': '0',
                'branch': 'false'
            })
        xml_bytes = tostring(root, encoding='utf-8')
        report_path.write_text(xml_bytes.decode('utf-8'), encoding='utf-8')
    else:
        raise SystemExit(f"Unsupported coverage format: {fmt}")


def _compute_coverage(endpoints: List[Endpoint], ignored: List[Tuple[str,str,pathlib.Path,str]], swagger: Dict[str, Any]):
    swagger_paths = swagger.get('paths', {}) or {}
    methods_set = {"get","post","put","delete","patch","options","head"}
    swagger_ops: List[Tuple[str,str,Dict[str,Any]]] = []
    for p, mdefs in swagger_paths.items():
        if not isinstance(mdefs, dict):
            continue
        for m, opdef in mdefs.items():
            ml = m.lower()
            if ml in methods_set and isinstance(opdef, dict):
                swagger_ops.append((p, ml, opdef))
    endpoint_records = []
    ignored_set = {(p,m,f,fn) for (p,m,f,fn) in ignored}
    with_block = 0
    definition_matches = 0
    total_considered = 0
    in_swagger = 0
    for ep in endpoints:
        is_ignored = any((ep.path, ep.method, ep.file, ep.function) == t for t in ignored_set)
        if is_ignored:
            endpoint_records.append({
                'path': ep.path,
                'method': ep.method,
                'file': str(ep.file),
                'function': ep.function,
                'ignored': True,
                'has_openapi_block': bool(ep.meta),
                'in_swagger': False,
                'definition_matches': False,
                'missing_in_swagger': True,
            })
            continue
        total_considered += 1
        has_block = bool(ep.meta)
        if has_block:
            with_block += 1
        swagger_op = swagger_paths.get(ep.path, {}).get(ep.method)
        op_matches = False
        if swagger_op is not None:
            in_swagger += 1
            generated = ep.to_openapi_operation()
            if swagger_op == generated:
                op_matches = True
                if has_block:
                    definition_matches += 1
        endpoint_records.append({
            'path': ep.path,
            'method': ep.method,
            'file': str(ep.file),
            'function': ep.function,
            'ignored': False,
            'has_openapi_block': has_block,
            'in_swagger': swagger_op is not None,
            'definition_matches': op_matches,
            'missing_in_swagger': swagger_op is None,
        })
    swagger_only = []
    code_pairs = {(e.path,e.method) for e in endpoints if not any((e.path,e.method,e.file,e.function)==t for t in ignored_set)}
    for (p,m,op) in swagger_ops:
        if (p,m) not in code_pairs:
            swagger_only.append({'path': p, 'method': m})
    coverage_rate_handlers_with_block = (with_block / total_considered) if total_considered else 0.0
    coverage_rate_handlers_in_swagger = (in_swagger / total_considered) if total_considered else 0.0
    definition_match_rate = (definition_matches / with_block) if with_block else 0.0
    summary = {
        'handlers_total': total_considered,
        'ignored_total': len(ignored),
        'with_openapi_block': with_block,
        'without_openapi_block': total_considered - with_block,
        'swagger_operations_total': len(swagger_ops),
        'swagger_only_operations': len(swagger_only),
        'handlers_in_swagger': in_swagger,
        'definition_matches': definition_matches,
        'coverage_rate_handlers_with_block': coverage_rate_handlers_with_block,
        'coverage_rate_handlers_in_swagger': coverage_rate_handlers_in_swagger,
        'operation_definition_match_rate': definition_match_rate,
    }
    return summary, endpoint_records, swagger_only


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync handler docstring OpenAPI blocks to swagger file")
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument('--fix', action='store_true', help='Write changes instead of just checking for drift')
    mode_group.add_argument('--check', action='store_true', help='Explicitly run in check mode (default) and show diff')
    parser.add_argument('--show-orphans', action='store_true', help='List swagger paths and components that have no code handler/model')
    parser.add_argument('--show-ignored', action='store_true', help='List endpoints skipped due to @openapi: ignore markers')
    parser.add_argument('--coverage-report', help='Write an OpenAPI coverage report to the given path (json, text, or cobertura based on --coverage-format)')
    parser.add_argument('--coverage-format', default='json', choices=['json','text','cobertura'], help='Coverage report format (default: json)')
    parser.add_argument('--fail-on-coverage-below', type=float, help='Fail (non-zero exit) if documentation coverage (handlers with openapi blocks) is below this threshold (accepts 0-1 or 0-100)')
    parser.add_argument('--verbose-coverage', action='store_true', default=False, help='Show per-endpoint coverage detail inline')
    parser.add_argument('--show-missing-blocks', action='store_true', help='List endpoints missing an >>>openapi <<<openapi block')
    parser.add_argument('--handlers-root', default=str(DEFAULT_HANDLERS_ROOT), help='Root directory containing HTTP handler Python files (default: bot/lib/http/handlers/api/v1)')
    parser.add_argument('--swagger-file', default=str(DEFAULT_SWAGGER_FILE), help='Path to swagger file to sync (default: .swagger.v1.yaml)')
    parser.add_argument('--ignore-file', action='append', default=[], help='Glob pattern (relative to handlers root) or filename to ignore (can be repeated)')
    parser.add_argument('--markdown-summary', help='Write a GitHub Actions style Markdown summary to this file (in addition to console output)')
    parser.add_argument('--output-directory', default='.', help='Base directory to place output artifacts (coverage reports, markdown summary). Default: current working directory')
    parser.add_argument('--strict', action='store_true', help='Treat docstring/decorator HTTP method mismatches as errors (default: warn and ignore extraneous methods)')
    parser.add_argument('--openapi-start', default=DEFAULT_OPENAPI_START, help=f'Start delimiter for embedded OpenAPI blocks (default: {DEFAULT_OPENAPI_START!r})')
    parser.add_argument('--openapi-end', default=DEFAULT_OPENAPI_END, help=f'End delimiter for embedded OpenAPI blocks (default: {DEFAULT_OPENAPI_END!r})')
    parser.add_argument('--list-endpoints', action='store_true', help='Print collected handler endpoints (path method file:function) and exit (debug aid)')
    parser.add_argument('--models-root', default=DEFAULT_MODELS_ROOT, help=f'Root directory to scan for @openapi_model decorated classes (default: {DEFAULT_MODELS_ROOT!r})')
    parser.add_argument('--no-model-components', action='store_true', help='Disable automatic model component generation')
    parser.add_argument(
        '--color',
        choices=['auto', 'always', 'never'],
        default='auto',
        help='Color output mode: auto (default, only if TTY), always, never'
    )
    args = parser.parse_args()

    handlers_root = pathlib.Path(args.handlers_root)
    swagger_path = pathlib.Path(args.swagger_file)
    if not handlers_root.exists():
        raise SystemExit(f"Handlers root does not exist: {handlers_root}")

    global DISABLE_COLOR
    if args.color == 'always':
        DISABLE_COLOR = False
        color_reason = 'enabled (mode=always)'
    elif args.color == 'never':
        DISABLE_COLOR = True
        color_reason = 'disabled (mode=never)'
    else:
        if sys.stdout.isatty():
            DISABLE_COLOR = False
            color_reason = 'enabled (mode=auto, TTY)'
        else:
            DISABLE_COLOR = True
            color_reason = 'disabled (mode=auto, non-TTY)'

    try:
        # Rebuild regex with possibly customized markers before collecting endpoints.
        global OPENAPI_BLOCK_RE
        OPENAPI_BLOCK_RE = build_openapi_block_re(args.openapi_start, args.openapi_end)
        endpoints, ignored = collect_endpoints(handlers_root, strict=args.strict, ignore_file_globs=args.ignore_file)
    except ValueError as e:
        err_msg = f"ERROR: {e}"
        if not DISABLE_COLOR:
            err_msg = f"{ANSI_RED}{err_msg}{ANSI_RESET}"
        print(err_msg, file=sys.stderr)
        sys.exit(1)
    if args.list_endpoints:
        # Just list endpoints and exit early (no swagger load needed)
        print("Collected endpoints:")
        for ep in endpoints:
            print(f" - {ep.method.upper()} {ep.path} ({ep.file}:{ep.function}) block={'yes' if ep.meta else 'no'}")
        if ignored:
            print("Ignored endpoints (@openapi: ignore):")
            for (p,m,f,fn) in ignored:
                print(f" - {m.upper()} {p} ({f}:{fn})")
        sys.exit(0)

    swagger = load_swagger(swagger_path)
    # Model components (collect + track metrics)
    model_components: Dict[str, Dict[str, Any]] = {}
    excluded_model_components: set[str] = set()
    model_components_updated: List[str] = []
    model_components_removed: List[str] = []
    components_changed = False  # Track if components.schemas mutated so we persist swagger even w/o path diffs
    if not args.no_model_components:
        model_components, excluded_model_components = collect_model_components(pathlib.Path(args.models_root))
        if model_components or excluded_model_components:
            schemas = swagger.setdefault('components', {}).setdefault('schemas', {})
            for name, new_schema in model_components.items():
                existing = schemas.get(name)
                if existing != new_schema:
                    # Compare schema differences using string representation
                    from io import StringIO as StringIOModule
                    if existing is not None:
                        existing_stream = StringIOModule()
                        yaml.dump(existing, existing_stream)
                        existing_lines = existing_stream.getvalue().rstrip().splitlines()
                    else:
                        existing_lines = []

                    new_stream = StringIOModule()
                    yaml.dump(new_schema, new_stream)
                    new_lines = new_stream.getvalue().rstrip().splitlines()
                    # Show diff whenever existing differs from new OR when component is brand new
                    if existing_lines != new_lines:
                        if existing is not None:
                            warn = f"Model schema drift detected for component '{name}'."
                        else:
                            warn = f"New model schema component '{name}' added."
                        if not DISABLE_COLOR:
                            warn = f"{ANSI_YELLOW}WARNING: {warn}{ANSI_RESET}"
                        else:
                            warn = f"WARNING: {warn}"
                        print(warn, file=sys.stderr)
                        diff = difflib.unified_diff(existing_lines, new_lines, fromfile=f"a/components.schemas.{name}", tofile=f"b/components.schemas.{name}", lineterm='')
                        for dl in _colorize_unified(list(diff)):
                            print(dl, file=sys.stderr)
                    schemas[name] = new_schema
                    model_components_updated.append(name)
                    components_changed = True

            # Remove excluded components from swagger
            for excluded_name in excluded_model_components:
                if excluded_name in schemas:
                    from io import StringIO as StringIOModule
                    existing_stream = StringIOModule()
                    yaml.dump(schemas[excluded_name], existing_stream)
                    existing_lines = existing_stream.getvalue().rstrip().splitlines()

                    warn = f"Excluded model schema component '{excluded_name}' removed."
                    if not DISABLE_COLOR:
                        warn = f"{ANSI_YELLOW}WARNING: {warn}{ANSI_RESET}"
                    else:
                        warn = f"WARNING: {warn}"
                    print(warn, file=sys.stderr)

                    # Show diff with deletion
                    diff = difflib.unified_diff(existing_lines, [], fromfile=f"a/components.schemas.{excluded_name}", tofile=f"b/components.schemas.{excluded_name}", lineterm='')
                    for dl in _colorize_unified(list(diff)):
                        print(dl, file=sys.stderr)

                    del schemas[excluded_name]
                    model_components_removed.append(excluded_name)
                    components_changed = True

            if model_components_updated:
                print(f"Model schemas updated: {', '.join(sorted(model_components_updated))}")
            if model_components_removed:
                print(f"Model schemas removed: {', '.join(sorted(model_components_removed))}")
    existing_schemas = swagger.get('components', {}).get('schemas', {}) if isinstance(swagger.get('components'), dict) else {}
    model_components_generated_count = len(model_components)
    model_components_existing_not_generated_count = sum(1 for k in existing_schemas.keys() if k not in model_components) if existing_schemas else 0
    swagger_new, changed, notes, diffs = merge(swagger, endpoints)

    orphans = detect_orphans(swagger_new, endpoints, model_components) if args.show_orphans else []
    coverage_summary, coverage_records, coverage_swagger_only = _compute_coverage(endpoints, ignored, swagger_new)
    # augment coverage summary with component metrics
    coverage_summary['model_components_generated'] = model_components_generated_count
    coverage_summary['model_components_existing_not_generated'] = model_components_existing_not_generated_count
    output_dir = pathlib.Path(args.output_directory)
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:  # pragma: no cover
        raise SystemExit(f"Failed to create output directory '{output_dir}': {e}")

    def _resolve_output(p: Optional[str]) -> Optional[pathlib.Path]:
        if not p:
            return None
        path_obj = pathlib.Path(p)
        if path_obj.is_absolute():
            return path_obj
        return output_dir / path_obj

    coverage_report_path = _resolve_output(args.coverage_report)
    markdown_summary_path = _resolve_output(args.markdown_summary)

    # Warn if artifacts risk accidental commit. Allow 'reports' root and any subdirectory underneath.
    try:
        repo_root = pathlib.Path.cwd().resolve()
        out_resolved = output_dir.resolve()
        if repo_root in out_resolved.parents:
            # Determine if path is reports or inside reports
            try:
                rel = out_resolved.relative_to(repo_root)
            except Exception:  # pragma: no cover
                rel = None
            if rel is not None:
                parts = rel.parts
                if not parts:
                    # repo root itself – always warn if not explicitly reports
                    if out_resolved.name != 'reports':
                        warn_msg = f"WARNING: Output directory '{out_resolved}' is inside the repository and is not 'reports/'. Consider using 'reports/' to avoid accidental commits."
                        if not DISABLE_COLOR:
                            warn_msg = f"{ANSI_YELLOW}{warn_msg}{ANSI_RESET}"
                        print(warn_msg, file=sys.stderr)
                else:
                    # Allow reports/ and any nested path under reports/
                    if parts[0] != 'reports':
                        warn_msg = f"WARNING: Output directory '{out_resolved}' is inside the repository and is not 'reports/'. Consider using 'reports/' to avoid accidental commits."
                        if not DISABLE_COLOR:
                            warn_msg = f"{ANSI_YELLOW}{warn_msg}{ANSI_RESET}"
                        print(warn_msg, file=sys.stderr)
    except Exception:  # pragma: no cover
        pass

    if coverage_report_path:
        coverage_report_path.parent.mkdir(parents=True, exist_ok=True)
        extra = {
            'model_components_generated': model_components_generated_count,
            'model_components_existing_not_generated': model_components_existing_not_generated_count,
        }
        _generate_coverage(endpoints, ignored, swagger_new, report_path=coverage_report_path, fmt=args.coverage_format, extra_summary=extra)

    def print_coverage_summary(prefix: str = "OpenAPI Documentation Coverage Summary") -> None:
        cs = coverage_summary
        print(prefix + ":")
        print(f"  Handlers considered:        {cs['handlers_total']}")
        print(f"  Ignored handlers:           {cs['ignored_total']}")
        print(f"  With doc blocks:            {cs['with_openapi_block']} ({cs['coverage_rate_handlers_with_block']:.1%})")
        print(f"  Without doc blocks:         {cs['without_openapi_block']}")
        print(f"  In swagger (handlers):      {cs['handlers_in_swagger']} ({cs['coverage_rate_handlers_in_swagger']:.1%})")
        print(f"  Definition matches:         {cs['definition_matches']} / {cs['with_openapi_block']} ({cs['operation_definition_match_rate']:.1%})")
        print(f"  Swagger only operations:    {cs['swagger_only_operations']}")
        print(f"  Model components generated: {cs.get('model_components_generated', 0)}")
        print(f"  Schemas not generated:      {cs.get('model_components_existing_not_generated', 0)}")
        suggestions: List[str] = []
        if cs['without_openapi_block'] > 0:
            suggestions.append("Add >>>openapi <<<openapi blocks for undocumented handlers.")
        if cs['swagger_only_operations'] > 0:
            suggestions.append("Remove or implement swagger-only paths, or mark related handlers with @openapi: ignore if intentional.")
        if suggestions:
            print("  Suggestions:")
            for s in suggestions:
                print(f"    - {s}")
        if args.show_missing_blocks and cs['without_openapi_block']:
            print("\n  Endpoints missing >>>openapi <<<openapi block:")
            for rec in coverage_records:
                if not rec['ignored'] and not rec['has_openapi_block']:
                    print(f"    - {rec['method'].upper()} {rec['path']} ({rec['file']}:{rec['function']})")
        if args.verbose_coverage:
            print("\n  Per-endpoint detail:")
            for rec in coverage_records:
                flags: List[str] = []
                if rec['ignored']:
                    flags.append('IGNORED')
                if rec['has_openapi_block']:
                    flags.append('BLOCK')
                if rec['in_swagger']:
                    flags.append('SWAGGER')
                if rec['definition_matches']:
                    flags.append('MATCH')
                if rec['missing_in_swagger']:
                    flags.append('MISSING_SWAGGER')
                print(f"    - {rec['method'].upper()} {rec['path']} :: {'|'.join(flags) if flags else 'NONE'}")
            if coverage_swagger_only:
                print("\n  Swagger-only (no handler) operations:")
                for so in coverage_swagger_only[:50]:
                    print(f"    - {so['method'].upper()} {so['path']}")
                if len(coverage_swagger_only) > 50:
                    print(f"    ... ({len(coverage_swagger_only)-50} more)")
    if args.fix:
        if changed or components_changed:
            # Write out even if only components changed (previously skipped)
            from io import StringIO as StringIOModule
            stream = StringIOModule()
            yaml.dump(swagger_new, stream)
            swagger_path.write_text(stream.getvalue(), encoding='utf-8')
            if changed and components_changed:
                print("Swagger updated (endpoint operations + component schemas).")
            elif changed and not components_changed:
                print("Swagger updated (endpoint operations).")
            elif components_changed and not changed:
                print("Swagger updated (component schemas only – no endpoint operation changes).")
            if notes:
                for n in notes:
                    print(f" - {n}")
        else:
            print("No endpoint or component schema changes needed.")
        if args.show_ignored and ignored:
            print("Ignored endpoints (@openapi: ignore):")
            for (p, m, f, fn) in ignored:
                print(f" - {m.upper()} {p} ({f.name}:{fn})")
        if orphans:
            print("Orphans:")
            for o in orphans:
                print(f" - {o}")
        return

    coverage_fail = False
    if args.fail_on_coverage_below is not None:
        threshold = args.fail_on_coverage_below
        if threshold > 1:
            threshold = threshold / 100.0
        actual = coverage_summary['coverage_rate_handlers_with_block']
        if actual + 1e-12 < threshold:
            coverage_fail = True
            msg = f"Coverage threshold not met: {actual:.2%} < {threshold:.2%}"
            if not DISABLE_COLOR:
                msg = f"{ANSI_RED}{msg}{ANSI_RESET}"
            print(msg, file=sys.stderr)

    def build_markdown_summary(*, changed: bool, coverage_fail: bool) -> str:
        def _strip_ansi(s: str) -> str:
            return re.sub(r"\x1b\[[0-9;]*m", "", s)
        cs = coverage_summary
        lines: List[str] = ["# OpenAPI Sync Result", ""]
        if changed:
            lines.append("**Status:** Drift detected. Please run the sync script with `--fix` and commit the updated swagger file.")
        elif coverage_fail:
            lines.append("**Status:** Coverage threshold failed.")
        else:
            lines.append("**Status:** In sync ✅")
        lines.append("")
        lines.append(f"_Diff color output: {color_reason}._")
        lines.append("")
        lines.append("## Coverage Summary")
        lines.append("")
        lines.append("| Metric | Value | Percent |")
        lines.append("|--------|-------|---------|")
        lines.append(f"| Handlers considered | {cs['handlers_total']} | - |")
        lines.append(f"| Ignored handlers | {cs['ignored_total']} | - |")
        lines.append(f"| With doc blocks | {cs['with_openapi_block']} | {cs['coverage_rate_handlers_with_block']:.1%} |")
        lines.append(f"| In swagger (handlers) | {cs['handlers_in_swagger']} | {cs['coverage_rate_handlers_in_swagger']:.1%} |")
        lines.append(f"| Definition matches | {cs['definition_matches']} / {cs['with_openapi_block']} | {cs['operation_definition_match_rate']:.1%} |")
        lines.append(f"| Swagger only operations | {cs['swagger_only_operations']} | - |")
        lines.append(f"| Model components generated | {cs.get('model_components_generated', 0)} | - |")
        lines.append(f"| Schemas not generated | {cs.get('model_components_existing_not_generated', 0)} | - |")
        lines.append("")
        suggestions_md: List[str] = []
        if cs['without_openapi_block'] > 0:
            suggestions_md.append("Add `>>>openapi <<<openapi` blocks for handlers missing documentation.")
        if cs['swagger_only_operations'] > 0:
            suggestions_md.append("Remove, implement, or ignore swagger-only operations.")
        if suggestions_md:
            lines.append("## Suggestions")
            lines.append("")
            for s in suggestions_md:
                lines.append(f"- {s}")
            lines.append("")
        if changed:
            lines.append("## Proposed Operation Diffs")
            lines.append("")
            for (path, method), dlines in diffs.items():
                lines.append(f"<details><summary>{method.upper()} {path}</summary>")
                lines.append("")
                lines.append("```diff")
                for dl in dlines:
                    lines.append(_strip_ansi(dl))
                lines.append("```")
                lines.append("</details>")
            lines.append("")
        if coverage_swagger_only:
            lines.append("## Swagger-only Operations (no handler)")
            lines.append("")
            show = coverage_swagger_only[:25]
            for so in show:
                lines.append(f"- `{so['method'].upper()} {so['path']}`")
            if len(coverage_swagger_only) > 25:
                lines.append(f"... and {len(coverage_swagger_only)-25} more")
            lines.append("")
        if ignored:
            lines.append("## Ignored Endpoints (@openapi: ignore)")
            lines.append("")
            for (p, m, f, fn) in ignored[:50]:
                lines.append(f"- `{m.upper()} {p}` ({f.name}:{fn})")
            if len(ignored) > 50:
                lines.append(f"... and {len(ignored)-50} more")
            lines.append("")
        content = "\n".join(lines)
        content = "\n".join(l.rstrip() for l in content.splitlines())
        content = re.sub(r"\n{3,}", "\n\n", content)
        if not content.endswith("\n"):
            content += "\n"
        return content

    if changed or coverage_fail:
        if changed:
            drift_msg = "Drift detected between handlers and swagger. Run: python scripts/swagger_sync.py --fix"
            if not DISABLE_COLOR:
                drift_msg = f"{ANSI_RED}{drift_msg}{ANSI_RESET}"
            print(drift_msg, file=sys.stderr)
            for n in notes:
                print(f" - {n}")
            print("\nProposed changes:")
            for (path, method), dlines in diffs.items():
                print(f"{method.upper()} {path}")
                for dl in dlines:
                    print(dl)
        elif coverage_fail:
            msg = "Documentation coverage threshold not met."
            if not DISABLE_COLOR:
                msg = f"{ANSI_RED}{msg}{ANSI_RESET}"
            print(msg, file=sys.stderr)
        if orphans:
            if args.show_orphans:
                print("\nOrphans:")
                for o in orphans:
                    print(f" - {o}")
            else:
                print("\n(Info) Potential swagger-only paths (use --show-orphans for list)")
        if args.show_ignored and ignored:
            print("\nIgnored endpoints (@openapi: ignore):")
            for (p, m, f, fn) in ignored:
                print(f" - {m.upper()} {p} ({f.name}:{fn})")
        print()
        print_coverage_summary()
        summary_targets: List[str] = []
        step_summary = os.getenv("GITHUB_STEP_SUMMARY")
        if step_summary:
            summary_targets.append(step_summary)
        if markdown_summary_path:
            summary_targets.append(str(markdown_summary_path))
        if summary_targets:
            try:
                content = build_markdown_summary(changed=changed, coverage_fail=coverage_fail)
                for path_out in summary_targets:
                    mode = 'a'
                    if markdown_summary_path and path_out == str(markdown_summary_path):
                        mode = 'w'
                    with open(path_out, mode, encoding='utf-8') as fh:
                        fh.write(content)
            except Exception as e:  # pragma: no cover
                print(f"WARNING: Failed writing markdown summary: {e}", file=sys.stderr)
        sys.exit(1)
    else:
        print("Swagger paths are in sync with handlers.")
        if orphans:
            if args.show_orphans:
                print("Orphans:")
                for o in orphans:
                    print(f" - {o}")
            else:
                print("(Info) Potential swagger-only paths and components (use --show-orphans for list)")
        if args.show_ignored and ignored:
            print("Ignored endpoints (@openapi: ignore):")
            for (p, m, f, fn) in ignored:
                print(f" - {m.upper()} {p} ({f.name}:{fn})")
        print()
        print_coverage_summary()
        summary_targets: List[str] = []
        step_summary = os.getenv("GITHUB_STEP_SUMMARY")
        if step_summary:
            summary_targets.append(step_summary)
        if markdown_summary_path:
            summary_targets.append(str(markdown_summary_path))
        if summary_targets:
            try:
                content = build_markdown_summary(changed=False, coverage_fail=False)
                for path_out in summary_targets:
                    mode = 'a'
                    if markdown_summary_path and path_out == str(markdown_summary_path):
                        mode = 'w'
                    with open(path_out, mode, encoding='utf-8') as fh:
                        fh.write(content)
            except Exception as e:  # pragma: no cover
                print(f"WARNING: Failed writing markdown summary: {e}", file=sys.stderr)

if __name__ == '__main__':
    main()
