#!/usr/bin/env python3
"""Thin wrapper around a real slicer binary.

The backend only needs a stable input/output contract:
- argv[1]: input model path
- argv[2]: output directory
- argv[3]: material name
- argv[4]: height/profile name

This script resolves environment-specific profile paths, invokes the actual
slicer command, validates the generated gcode, and writes a normalized
`slice-result.json` sidecar for the backend to consume.
"""

from __future__ import annotations

import json
import math
import os
import re
import shlex
import subprocess
import sys
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv

    _script_dir = Path(__file__).resolve().parent
    _backend_dir = _script_dir.parent
    _root_env_path = _backend_dir.parent / ".env"
    _server_override_path = _backend_dir / ".env.server.local"

    if _root_env_path.exists():
        load_dotenv(_root_env_path)
    if _server_override_path.exists():
        load_dotenv(_server_override_path, override=True)
except ImportError:
    pass


def _load_json_mapping(raw: str, label: str) -> dict[str, str]:
    if not raw.strip():
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{label} 不是合法 JSON") from exc
    if not isinstance(data, dict):
        raise RuntimeError(f"{label} 必须是 JSON object")
    normalized: dict[str, str] = {}
    for key, value in data.items():
        if value is None:
            continue
        normalized[str(key).strip()] = str(value).strip()
    return normalized


def _resolve_required_path(label: str, raw_path: str) -> Path:
    if not raw_path.strip():
        raise RuntimeError(f"{label} 未配置")
    path = Path(raw_path).expanduser()
    if not path.exists():
        raise RuntimeError(f"{label} 不存在: {path}")
    return path


def _pick_profile(mapping: dict[str, str], requested: str, label: str) -> Path:
    candidates = [requested, requested.lower(), "default"]
    for candidate in candidates:
        if candidate in mapping and mapping[candidate]:
            return _resolve_required_path(label, mapping[candidate])
    raise RuntimeError(f"{label} 未配置: {requested}")


def _env_flag(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() not in {"0", "false", "no", "off"}


def _resolve_profile_override_value(name: str, material: str) -> str:
    mapping_name = f"{name}_MAP"
    mapping = _load_json_mapping(
        os.getenv(mapping_name, "{}"),
        mapping_name,
    )
    requested = (material or "").strip()
    if requested:
        for candidate in (requested, requested.lower(), "default"):
            value = mapping.get(candidate)
            if value:
                return value.strip()
    return os.getenv(name, "").strip()


def _resolve_profile_override_flag(name: str, material: str, default: bool) -> bool:
    raw = _resolve_profile_override_value(name, material)
    if not raw:
        return _env_flag(name, default)
    return raw.strip().lower() not in {"0", "false", "no", "off"}


def _resolve_tool_command(material: str) -> str:
    mapping = _load_json_mapping(
        os.getenv("PRINT_ORCA_TOOL_COMMAND_MAP", "{}"),
        "PRINT_ORCA_TOOL_COMMAND_MAP",
    )
    requested = (material or "").strip()
    if requested:
        for candidate in (requested, requested.lower()):
            value = mapping.get(candidate)
            if value:
                return value.strip()

    default_command = os.getenv("PRINT_ORCA_DEFAULT_TOOL_COMMAND", "").strip()
    return default_command


def _set_profile_value(profile: dict[str, Any], key: str, value: str, metadata: dict[str, Any]) -> bool:
    normalized = (value or "").strip()
    if not normalized:
        return False
    if str(profile.get(key, "")).strip() == normalized:
        return False
    profile[key] = normalized
    metadata[key] = normalized
    return True


def _ensure_min_int_profile_value(
    profile: dict[str, Any],
    key: str,
    value: str,
    metadata: dict[str, Any],
) -> bool:
    normalized = (value or "").strip()
    if not normalized:
        return False
    try:
        desired = int(normalized)
    except ValueError:
        return False

    current_raw = str(profile.get(key, "")).strip()
    try:
        current = int(current_raw)
    except ValueError:
        current = None

    if current is not None and current >= desired:
        return False

    profile[key] = str(desired)
    metadata[key] = str(desired)
    return True


def _inject_tool_command(gcode_path: Path, tool_command: str) -> dict[str, Any]:
    normalized_command = (tool_command or "").strip()
    if not normalized_command:
        return {}

    try:
        original_text = gcode_path.read_text(encoding="utf-8", errors="ignore")
    except OSError as exc:
        raise RuntimeError(f"无法读取 gcode 文件以注入喷头指令: {gcode_path}") from exc

    lines = original_text.splitlines()
    if any(line.strip().upper() == normalized_command.upper() for line in lines[:80]):
        return {
            "tool_command": normalized_command,
            "tool_command_injected": False,
            "tool_command_already_present": True,
        }

    insert_at = 0
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith(";"):
            insert_at = index + 1
            continue
        break

    lines.insert(insert_at, normalized_command)
    updated_text = "\n".join(lines)
    if original_text.endswith("\n"):
        updated_text += "\n"
    else:
        updated_text += "\n"

    try:
        gcode_path.write_text(updated_text, encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(f"无法写回 gcode 文件以注入喷头指令: {gcode_path}") from exc

    return {
        "tool_command": normalized_command,
        "tool_command_injected": True,
        "tool_command_insert_line": insert_at + 1,
    }


def _maybe_prepare_process_profile(process_profile: Path, material: str) -> tuple[Path, dict[str, Any]]:
    support_enabled = _resolve_profile_override_flag("PRINT_ORCA_ENABLE_SUPPORT", material, False)

    try:
        profile = json.loads(process_profile.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"无法读取 process profile: {process_profile}") from exc

    if not isinstance(profile, dict):
        raise RuntimeError(f"process profile 格式错误: {process_profile}")

    updated = False
    metadata: dict[str, Any] = {}

    bottom_surface_pattern = _resolve_profile_override_value("PRINT_ORCA_BOTTOM_SURFACE_PATTERN", material)
    if _set_profile_value(profile, "bottom_surface_pattern", bottom_surface_pattern, metadata):
        updated = True

    top_surface_pattern = _resolve_profile_override_value("PRINT_ORCA_TOP_SURFACE_PATTERN", material)
    if _set_profile_value(profile, "top_surface_pattern", top_surface_pattern, metadata):
        updated = True

    initial_layer_line_width = _resolve_profile_override_value("PRINT_ORCA_INITIAL_LAYER_LINE_WIDTH", material)
    if _set_profile_value(profile, "initial_layer_line_width", initial_layer_line_width, metadata):
        updated = True

    bottom_shell_layers = _resolve_profile_override_value("PRINT_ORCA_BOTTOM_SHELL_LAYERS", material)
    if _ensure_min_int_profile_value(profile, "bottom_shell_layers", bottom_shell_layers, metadata):
        updated = True

    first_layer_bed_temperature = _resolve_profile_override_value("PRINT_ORCA_FIRST_LAYER_BED_TEMPERATURE", material)
    if _set_profile_value(profile, "first_layer_bed_temperature", first_layer_bed_temperature, metadata):
        updated = True

    bed_temperature = _resolve_profile_override_value("PRINT_ORCA_BED_TEMPERATURE", material)
    if _set_profile_value(profile, "bed_temperature", bed_temperature, metadata):
        updated = True

    if support_enabled:
        metadata["support_enabled"] = True
        if str(profile.get("enable_support", "")).strip() not in {"1", "true", "True"}:
            profile["enable_support"] = "1"
            metadata["enable_support"] = "1"
            updated = True

        support_style = _resolve_profile_override_value("PRINT_ORCA_SUPPORT_STYLE", material)
        if _set_profile_value(profile, "support_style", support_style, metadata):
            updated = True

        support_type = _resolve_profile_override_value("PRINT_ORCA_SUPPORT_TYPE", material)
        if _set_profile_value(profile, "support_type", support_type, metadata):
            updated = True

        support_interface_spacing = _resolve_profile_override_value("PRINT_ORCA_SUPPORT_INTERFACE_SPACING", material)
        if _set_profile_value(profile, "support_interface_spacing", support_interface_spacing, metadata):
            updated = True

        support_base_pattern_spacing = _resolve_profile_override_value("PRINT_ORCA_SUPPORT_BASE_PATTERN_SPACING", material)
        if _set_profile_value(profile, "support_base_pattern_spacing", support_base_pattern_spacing, metadata):
            updated = True

        support_speed = _resolve_profile_override_value("PRINT_ORCA_SUPPORT_SPEED", material)
        if _set_profile_value(profile, "support_speed", support_speed, metadata):
            updated = True

        tree_support_with_infill = _resolve_profile_override_value("PRINT_ORCA_TREE_SUPPORT_WITH_INFILL", material)
        if _set_profile_value(profile, "tree_support_with_infill", tree_support_with_infill, metadata):
            updated = True

    if not updated:
        return process_profile, metadata

    fd, temp_output = tempfile.mkstemp(suffix=process_profile.suffix or ".json")
    os.close(fd)
    temp_path = Path(temp_output)
    temp_path.write_text(
        json.dumps(profile, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    metadata.update({
        "process_profile_overridden": True,
        "support_profile_source": str(process_profile),
    })
    return temp_path, metadata


def _build_default_command(
    *,
    binary: str,
    input_path: Path,
    output_dir: Path,
    printer_profile: Path,
    process_profile: Path,
    filament_profile: Path,
    extra_args: str,
) -> list[str]:
    command = [
        binary,
        "--load-settings",
        f"{printer_profile};{process_profile}",
        "--load-filaments",
        str(filament_profile),
        "--outputdir",
        str(output_dir),
        "--slice",
        "0",
        str(input_path),
    ]
    if extra_args.strip():
        command.extend(shlex.split(extra_args))
    return command


def _build_command(
    *,
    input_path: Path,
    output_dir: Path,
    material: str,
    height: str,
    printer_profile: Path,
    process_profile: Path,
    filament_profile: Path,
    result_json: Path,
) -> list[str]:
    binary = os.getenv("PRINT_ORCA_SLICER_BINARY", "snapmaker-orca").strip() or "snapmaker-orca"
    cmd_template = os.getenv("PRINT_ORCA_CMD_TEMPLATE", "").strip()
    extra_args = os.getenv("PRINT_ORCA_EXTRA_ARGS", "")

    if not cmd_template:
        return _build_default_command(
            binary=binary,
            input_path=input_path,
            output_dir=output_dir,
            printer_profile=printer_profile,
            process_profile=process_profile,
            filament_profile=filament_profile,
            extra_args=extra_args,
        )

    formatted = cmd_template.format(
        binary=shlex.quote(binary),
        input_path=shlex.quote(str(input_path)),
        output_dir=shlex.quote(str(output_dir)),
        material=shlex.quote(material),
        height=shlex.quote(height),
        printer_profile=shlex.quote(str(printer_profile)),
        process_profile=shlex.quote(str(process_profile)),
        filament_profile=shlex.quote(str(filament_profile)),
        result_json=shlex.quote(str(result_json)),
    )
    return shlex.split(formatted)


def _build_subprocess_env(binary: str) -> dict[str, str]:
    env = deepcopy(os.environ)
    force_extract = os.getenv("PRINT_ORCA_APPIMAGE_EXTRACT_AND_RUN", "").strip().lower()
    if binary.endswith(".AppImage") and force_extract not in {"0", "false", "no"}:
        env.setdefault("APPIMAGE_EXTRACT_AND_RUN", "1")
    return env


def _parse_requested_height_mm(raw_height: str) -> float | None:
    text = (raw_height or "").strip().lower()
    if not text:
        return None

    match = re.search(r"(\d+(?:\.\d+)?)\s*(cm|mm)", text)
    if not match:
        return None

    value = float(match.group(1))
    unit = match.group(2)
    return value * 10.0 if unit == "cm" else value


def _prepare_input_model_for_slicing(input_path: Path, requested_height: str) -> tuple[Path, dict[str, Any]]:
    if input_path.suffix.lower() in {".glb", ".gltf"}:
        import trimesh

        loaded = trimesh.load(str(input_path), force="scene")
        if isinstance(loaded, trimesh.Scene):
            meshes = [
                geometry
                for geometry in loaded.geometry.values()
                if isinstance(geometry, trimesh.Trimesh)
                and len(geometry.vertices) > 0
                and len(geometry.faces) > 0
            ]
            if not meshes:
                return input_path, {}
            mesh = trimesh.util.concatenate(meshes) if len(meshes) > 1 else meshes[0]
        elif isinstance(loaded, trimesh.Trimesh):
            if len(loaded.vertices) == 0 or len(loaded.faces) == 0:
                return input_path, {}
            mesh = loaded
        else:
            return input_path, {}

        fd, temp_output = tempfile.mkstemp(suffix=".stl")
        os.close(fd)
        temp_path = Path(temp_output)
        mesh.export(str(temp_path))
        return temp_path, {
            "converted_for_slicing": True,
            "source_format": input_path.suffix.lower().lstrip("."),
            "target_format": "stl",
            "mesh_count": len(meshes) if 'meshes' in locals() else 1,
        }

    if input_path.suffix.lower() not in {".stl", ".obj", ".amf"}:
        return input_path, {}

    target_height_mm = _parse_requested_height_mm(requested_height)
    if target_height_mm is None:
        return input_path, {}

    import trimesh

    loaded = trimesh.load(str(input_path), force="mesh")
    if not isinstance(loaded, trimesh.Trimesh) or len(loaded.vertices) == 0 or len(loaded.faces) == 0:
        return input_path, {}

    current_max_extent = float(max(loaded.extents)) if loaded.extents is not None else 0.0
    if current_max_extent <= 0:
        return input_path, {}

    # AI 生成模型经常使用归一化坐标，直接作为 mm 送入切片会小到无法成功切片。
    if current_max_extent >= 5.0:
        return input_path, {}

    scale_factor = target_height_mm / current_max_extent
    if scale_factor <= 1.0:
        return input_path, {}

    scaled_mesh = loaded.copy()
    scaled_mesh.apply_scale(scale_factor)
    fd, temp_output = tempfile.mkstemp(suffix=input_path.suffix)
    os.close(fd)
    temp_path = Path(temp_output)
    scaled_mesh.export(str(temp_path))
    return temp_path, {
        "auto_scaled_for_slicing": True,
        "source_max_extent_mm": current_max_extent,
        "target_max_extent_mm": float(max(scaled_mesh.extents)),
        "scale_factor": scale_factor,
    }


def _parse_duration_to_seconds(raw_value: str) -> int | None:
    text = raw_value.strip()
    if not text:
        return None
    if text.isdigit():
        return int(text)

    total = 0
    matched = False
    for value, unit in re.findall(r"(\d+)\s*([dhms])", text.lower()):
        matched = True
        number = int(value)
        if unit == "d":
            total += number * 86400
        elif unit == "h":
            total += number * 3600
        elif unit == "m":
            total += number * 60
        elif unit == "s":
            total += number
    return total if matched else None


def _extract_first_float(text: str) -> float | None:
    match = re.search(r"(-?\d+(?:\.\d+)?)", text)
    return float(match.group(1)) if match else None


def _parse_gcode_metadata(gcode_path: Path) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    patterns: list[tuple[str, re.Pattern[str], str]] = [
        (
            "estimated_weight_grams",
            re.compile(r"^\s*;\s*(?:total\s+)?filament used \[g\]\s*=\s*(.+)$", re.I),
            "float",
        ),
        (
            "estimated_print_time_seconds",
            re.compile(r"^\s*;\s*estimated printing time(?: \(normal mode\))?\s*=\s*(.+)$", re.I),
            "duration",
        ),
        (
            "filament_type",
            re.compile(r"^\s*;\s*filament_type\s*=\s*(.+)$", re.I),
            "string",
        ),
        (
            "generated_by",
            re.compile(r"^\s*;\s*generated by\s+(.+)$", re.I),
            "string",
        ),
        (
            "filament_density",
            re.compile(r"^\s*;\s*filament_density\s*[:=]\s*(.+)$", re.I),
            "float",
        ),
        (
            "filament_diameter",
            re.compile(r"^\s*;\s*filament_diameter\s*[:=]\s*(.+)$", re.I),
            "float",
        ),
    ]

    extrusion_relative = False
    current_e = 0.0
    total_extrusion_mm = 0.0
    max_remaining_minutes: int | None = None

    with gcode_path.open("r", encoding="utf-8", errors="ignore") as handle:
        for line_number, line in enumerate(handle, start=1):
            for key, pattern, value_type in patterns:
                if key in metadata:
                    continue
                match = pattern.search(line)
                if not match:
                    continue
                raw_value = match.group(1).strip()
                if value_type == "float":
                    parsed = _extract_first_float(raw_value)
                    if parsed is not None:
                        metadata[key] = parsed
                elif value_type == "duration":
                    parsed = _parse_duration_to_seconds(raw_value)
                    if parsed is not None:
                        metadata[key] = parsed
                else:
                    metadata[key] = raw_value

            code = line.split(";", 1)[0].strip()
            if not code:
                if line_number >= 200 and all(key in metadata for key, *_ in patterns[:4]):
                    break
                continue

            if re.search(r"^\s*M82\b", code, re.I):
                extrusion_relative = False
                continue
            if re.search(r"^\s*M83\b", code, re.I):
                extrusion_relative = True
                continue

            if re.search(r"^\s*G92\b", code, re.I):
                e_match = re.search(r"(?:^|\s)E(-?\d+(?:\.\d+)?)", code, re.I)
                if e_match:
                    current_e = float(e_match.group(1))
                continue

            m73_match = re.search(r"^\s*M73\b.*(?:^|\s)R(\d+)\b", code, re.I)
            if m73_match:
                remaining_minutes = int(m73_match.group(1))
                max_remaining_minutes = max(max_remaining_minutes or 0, remaining_minutes)

            if not re.search(r"^\s*G[0-3]\b", code, re.I):
                continue

            e_match = re.search(r"(?:^|\s)E(-?\d+(?:\.\d+)?)", code, re.I)
            if not e_match:
                continue

            extrusion_value = float(e_match.group(1))
            if extrusion_relative:
                delta_e = extrusion_value
            else:
                delta_e = extrusion_value - current_e
                current_e = extrusion_value

            if delta_e > 0:
                total_extrusion_mm += delta_e

    if max_remaining_minutes is not None and "estimated_print_time_seconds" not in metadata:
        metadata["estimated_print_time_seconds"] = max_remaining_minutes * 60

    filament_density = metadata.get("filament_density")
    filament_diameter = metadata.get("filament_diameter")
    if (
        total_extrusion_mm > 0
        and isinstance(filament_density, (int, float))
        and isinstance(filament_diameter, (int, float))
        and filament_density > 0
        and filament_diameter > 0
        and "estimated_weight_grams" not in metadata
    ):
        radius_mm = filament_diameter / 2.0
        cross_section_area_mm2 = math.pi * radius_mm * radius_mm
        volume_mm3 = total_extrusion_mm * cross_section_area_mm2
        metadata["estimated_weight_grams"] = volume_mm3 * filament_density / 1000.0

    if total_extrusion_mm > 0:
        metadata["filament_used_mm"] = total_extrusion_mm
    return metadata


def _load_result_json(result_json: Path) -> dict[str, Any]:
    candidates = [result_json]
    fallback_result = result_json.parent / "result.json"
    if fallback_result not in candidates:
        candidates.append(fallback_result)

    for candidate in candidates:
        if not candidate.exists():
            continue
        try:
            data = json.loads(candidate.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"切片结果文件无法解析: {candidate}") from exc
        if not isinstance(data, dict):
            raise RuntimeError(f"切片结果文件格式错误: {candidate}")
        return data
    return {}


def _normalize_metadata(raw_result: dict[str, Any], gcode_metadata: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {
        "source": "orca_wrapper",
        "raw_result": raw_result,
        "gcode_metadata": gcode_metadata,
    }

    raw_weight = raw_result.get("estimated_weight_grams")
    if raw_weight is None:
        raw_weight = raw_result.get("weight_grams")
    if raw_weight is None:
        raw_weight = raw_result.get("total_weight")
    if raw_weight is None:
        raw_weight = gcode_metadata.get("estimated_weight_grams")
    if raw_weight is not None:
        if isinstance(raw_weight, str):
            raw_weight = _extract_first_float(raw_weight)
        if raw_weight is not None:
            normalized["estimated_weight_grams"] = float(raw_weight)

    raw_time = raw_result.get("estimated_print_time_seconds")
    if raw_time is None:
        raw_time = raw_result.get("print_time_seconds")
    if raw_time is None:
        raw_time = raw_result.get("print_time")
    if raw_time is None:
        raw_time = raw_result.get("normal_print_time")
    if raw_time is None:
        raw_time = gcode_metadata.get("estimated_print_time_seconds")
    if raw_time is not None:
        if isinstance(raw_time, str):
            raw_time = _parse_duration_to_seconds(raw_time)
        if raw_time is not None:
            normalized["estimated_print_time_seconds"] = int(raw_time)

    filament_type = raw_result.get("filament_type") or gcode_metadata.get("filament_type")
    if filament_type:
        normalized["filament_type"] = str(filament_type)

    generated_by = gcode_metadata.get("generated_by")
    if generated_by:
        normalized["generated_by"] = str(generated_by)

    return normalized


def main() -> int:
    if len(sys.argv) != 5:
        print(
            "usage: slice_with_orca.py <input_path> <output_dir> <material> <height>",
            file=sys.stderr,
        )
        return 2

    input_path = Path(sys.argv[1]).expanduser().resolve()
    output_dir = Path(sys.argv[2]).expanduser().resolve()
    material = sys.argv[3].strip() or "PLA"
    height = sys.argv[4].strip() or "default"
    result_file_name = os.getenv("PRINT_SLICER_RESULT_FILE_NAME", "slice-result.json")
    result_json = output_dir / result_file_name

    if not input_path.exists():
        print(f"input model not found: {input_path}", file=sys.stderr)
        return 3

    output_dir.mkdir(parents=True, exist_ok=True)

    printer_profile = _resolve_required_path(
        "PRINT_ORCA_PRINTER_PROFILE",
        os.getenv("PRINT_ORCA_PRINTER_PROFILE", ""),
    )
    material_map = _load_json_mapping(
        os.getenv("PRINT_ORCA_MATERIAL_PROFILE_MAP", "{}"),
        "PRINT_ORCA_MATERIAL_PROFILE_MAP",
    )
    height_map = _load_json_mapping(
        os.getenv("PRINT_ORCA_HEIGHT_PROFILE_MAP", "{}"),
        "PRINT_ORCA_HEIGHT_PROFILE_MAP",
    )
    filament_profile = _pick_profile(material_map, material, "material profile")
    process_profile = _pick_profile(height_map, height, "height profile")
    temporary_paths: list[Path] = []

    prepared_input_path = input_path
    prepare_metadata: dict[str, Any] = {}
    try:
        prepared_input_path, prepare_metadata = _prepare_input_model_for_slicing(input_path, height)
    except Exception as exc:  # noqa: BLE001
        print(f"failed to prepare model for slicing: {exc}", file=sys.stderr)
        return 5

    try:
        effective_process_profile, support_metadata = _maybe_prepare_process_profile(process_profile, material)
    except Exception as exc:  # noqa: BLE001
        print(f"failed to prepare support profile: {exc}", file=sys.stderr)
        return 6

    if effective_process_profile != process_profile:
        temporary_paths.append(effective_process_profile)
    if support_metadata:
        prepare_metadata.update(support_metadata)

    command = _build_command(
        input_path=prepared_input_path,
        output_dir=output_dir,
        material=material,
        height=height,
        printer_profile=printer_profile,
        process_profile=effective_process_profile,
        filament_profile=filament_profile,
        result_json=result_json,
    )
    subprocess_env = _build_subprocess_env(command[0])

    try:
        completed = subprocess.run(  # noqa: S603
            command,
            env=subprocess_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            print(completed.stdout, file=sys.stdout, end="")
            print(completed.stderr, file=sys.stderr, end="")
            return completed.returncode

        gcode_files = sorted(output_dir.glob("*.gcode"))
        if not gcode_files:
            print(f"no gcode generated in {output_dir}", file=sys.stderr)
            return 4

        gcode_path = gcode_files[0]
        tool_metadata = _inject_tool_command(
            gcode_path,
            _resolve_tool_command(material),
        )
        raw_result = _load_result_json(result_json)
        gcode_metadata = _parse_gcode_metadata(gcode_path)
        normalized_result = _normalize_metadata(raw_result, gcode_metadata)
        if prepare_metadata:
            normalized_result["prepare_metadata"] = prepare_metadata
        if tool_metadata:
            normalized_result["tool_metadata"] = tool_metadata
        normalized_result["file_name"] = gcode_path.name
        result_json.write_text(
            json.dumps(normalized_result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return 0
    finally:
        for temporary_path in temporary_paths:
            try:
                temporary_path.unlink()
            except OSError:
                pass
        if prepared_input_path != input_path:
            try:
                prepared_input_path.unlink()
            except OSError:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
