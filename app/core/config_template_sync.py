import copy
import tomllib
from pathlib import Path
from typing import TypeAlias, cast

TomlScalar: TypeAlias = bool | int | float | str | None
TomlValue: TypeAlias = TomlScalar | list["TomlValue"] | dict[str, "TomlValue"]
TomlTable: TypeAlias = dict[str, TomlValue]
TomlTableArray: TypeAlias = list[TomlTable]


def _default_template_path(runtime_path: Path) -> Path:
    if runtime_path.suffix:
        return runtime_path.with_name(f"{runtime_path.stem}.template{runtime_path.suffix}")
    return runtime_path.with_name(f"{runtime_path.name}.template")


def _format_toml_value(value: TomlValue) -> str:
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


def _is_table_array(value: TomlValue) -> bool:
    return isinstance(value, list) and all(isinstance(item, dict) for item in value)


def _split_table_items(
    table: TomlTable,
) -> tuple[list[tuple[str, TomlValue]], list[tuple[str, TomlTable]], list[tuple[str, TomlTableArray]]]:
    scalar_items: list[tuple[str, TomlValue]] = []
    dict_items: list[tuple[str, TomlTable]] = []
    list_table_items: list[tuple[str, TomlTableArray]] = []

    for key, value in table.items():
        if isinstance(value, dict):
            dict_items.append((key, cast(TomlTable, value)))
        elif _is_table_array(value):
            list_table_items.append((key, cast(TomlTableArray, value)))
        else:
            scalar_items.append((key, value))
    return scalar_items, dict_items, list_table_items


def _emit_table(lines: list[str], table: TomlTable, prefix: str | None, emit_header: bool) -> None:
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


def _to_toml_text(data: TomlTable) -> str:
    lines: list[str] = []
    _emit_table(lines, data, None, False)
    return "\n".join(lines).rstrip() + "\n"


def _emit_array_table(lines: list[str], table: TomlTable, prefix: str) -> None:
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


def _sync_shape(runtime_value: TomlValue, template_value: TomlValue) -> TomlValue:
    if isinstance(template_value, dict):
        runtime_dict = runtime_value if isinstance(runtime_value, dict) else {}
        synced: TomlTable = {}
        for key, template_child in template_value.items():
            if key in runtime_dict:
                synced[key] = _sync_shape(runtime_dict[key], template_child)
            else:
                synced[key] = copy.deepcopy(template_child)
        return synced

    if isinstance(template_value, list):
        if not isinstance(runtime_value, list):
            return copy.deepcopy(template_value)
        if _is_table_array(template_value):
            synced_rows: TomlTableArray = []
            for index, row in enumerate(runtime_value):
                template_item = template_value[index] if index < len(template_value) else template_value[0]
                if isinstance(row, dict):
                    synced_rows.append(cast(TomlTable, _sync_shape(row, template_item)))
                else:
                    synced_rows.append(copy.deepcopy(template_item))
            return synced_rows
        return runtime_value

    return runtime_value


def _load_toml_file(path: Path) -> TomlTable:
    with path.open("rb") as f:
        raw = tomllib.load(f)
    return cast(TomlTable, raw if isinstance(raw, dict) else {})


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
