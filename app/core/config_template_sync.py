import copy
import tomllib
from pathlib import Path
from typing import Any


def _default_template_path(runtime_path: Path) -> Path:
    if runtime_path.suffix:
        return runtime_path.with_name(f"{runtime_path.stem}.template{runtime_path.suffix}")
    return runtime_path.with_name(f"{runtime_path.name}.template")


def _format_toml_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    if isinstance(value, list):
        inner = ", ".join(_format_toml_value(item) for item in value)
        return f"[{inner}]"
    if value is None:
        return '""'
    raise TypeError(f"不支持的 TOML 值类型: {type(value)!r}")


def _split_table_items(
    table: dict[str, Any],
) -> tuple[list[tuple[str, Any]], list[tuple[str, dict[str, Any]]], list[tuple[str, list[dict[str, Any]]]]]:
    scalar_items: list[tuple[str, Any]] = []
    dict_items: list[tuple[str, dict[str, Any]]] = []
    list_table_items: list[tuple[str, list[dict[str, Any]]]] = []

    for key, value in table.items():
        if isinstance(value, dict):
            dict_items.append((key, value))
        elif isinstance(value, list) and value and all(isinstance(item, dict) for item in value):
            list_table_items.append((key, value))
        else:
            scalar_items.append((key, value))
    return scalar_items, dict_items, list_table_items


def _emit_table(lines: list[str], table: dict[str, Any], prefix: str | None, emit_header: bool) -> None:
    if emit_header and prefix:
        lines.append(f"[{prefix}]")

    scalar_items, dict_items, list_table_items = _split_table_items(table)

    for key, value in scalar_items:
        lines.append(f"{key} = {_format_toml_value(value)}")

    if scalar_items and (dict_items or list_table_items):
        lines.append("")

    for index, (key, child) in enumerate(dict_items):
        child_prefix = f"{prefix}.{key}" if prefix else key
        _emit_table(lines, child, child_prefix, True)
        if index != len(dict_items) - 1 or list_table_items:
            lines.append("")

    for table_index, (key, rows) in enumerate(list_table_items):
        table_prefix = f"{prefix}.{key}" if prefix else key
        for row_index, row in enumerate(rows):
            _emit_array_table(lines, row, table_prefix)
            if row_index != len(rows) - 1:
                lines.append("")
        if table_index != len(list_table_items) - 1:
            lines.append("")


def _to_toml_text(data: dict[str, Any]) -> str:
    lines: list[str] = []
    _emit_table(lines, data, None, False)
    return "\n".join(lines).rstrip() + "\n"


def _emit_array_table(lines: list[str], table: dict[str, Any], prefix: str) -> None:
    lines.append(f"[[{prefix}]]")
    scalar_items, dict_items, list_table_items = _split_table_items(table)

    for key, value in scalar_items:
        lines.append(f"{key} = {_format_toml_value(value)}")

    if scalar_items and (dict_items or list_table_items):
        lines.append("")

    for index, (key, child) in enumerate(dict_items):
        child_prefix = f"{prefix}.{key}"
        _emit_table(lines, child, child_prefix, True)
        if index != len(dict_items) - 1 or list_table_items:
            lines.append("")

    for table_index, (key, rows) in enumerate(list_table_items):
        table_prefix = f"{prefix}.{key}"
        for row_index, row in enumerate(rows):
            _emit_array_table(lines, row, table_prefix)
            if row_index != len(rows) - 1:
                lines.append("")
        if table_index != len(list_table_items) - 1:
            lines.append("")


def _sync_shape(runtime_value: Any, template_value: Any) -> Any:
    if isinstance(template_value, dict):
        runtime_dict = runtime_value if isinstance(runtime_value, dict) else {}
        synced: dict[str, Any] = {}
        for key, template_child in template_value.items():
            if key in runtime_dict:
                synced[key] = _sync_shape(runtime_dict[key], template_child)
            else:
                synced[key] = copy.deepcopy(template_child)
        return synced

    if isinstance(template_value, list):
        if not isinstance(runtime_value, list):
            return copy.deepcopy(template_value)
        if template_value and all(isinstance(item, dict) for item in template_value):
            synced_rows: list[Any] = []
            for index, row in enumerate(runtime_value):
                template_item = template_value[index] if index < len(template_value) else template_value[0]
                if isinstance(row, dict):
                    synced_rows.append(_sync_shape(row, template_item))
                else:
                    synced_rows.append(copy.deepcopy(template_item))
            return synced_rows
        return runtime_value

    return runtime_value


def _load_toml_file(path: Path) -> dict[str, Any]:
    with path.open("rb") as f:
        raw = tomllib.load(f)
    return raw if isinstance(raw, dict) else {}


def ensure_config_file_synced(runtime_path: str, template_path: str | None = None) -> None:
    runtime = Path(runtime_path)
    template = Path(template_path) if template_path else _default_template_path(runtime)

    if not template.exists():
        raise RuntimeError(f"配置模板不存在: {template}")

    runtime.parent.mkdir(parents=True, exist_ok=True)
    if not runtime.exists():
        runtime.write_text(template.read_text(encoding="utf-8"), encoding="utf-8")

    template_data = _load_toml_file(template)
    runtime_data = _load_toml_file(runtime)
    synced_data = _sync_shape(runtime_data, template_data)
    if synced_data != runtime_data:
        runtime.write_text(_to_toml_text(synced_data), encoding="utf-8")


def ensure_runtime_configs_synced(app_config_path: str, world_config_path: str) -> None:
    ensure_config_file_synced(app_config_path)
    ensure_config_file_synced(world_config_path)
