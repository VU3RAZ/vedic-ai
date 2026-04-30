"""YAML rule file loader with structural validation of feature paths at load time."""

from __future__ import annotations

from pathlib import Path

import yaml

from vedic_ai.core.exceptions import ConfigError, RuleError
from vedic_ai.core.rules import RuleDefinition
from vedic_ai.domain.enums import Graha

_VALID_GRAHAS: frozenset[str] = frozenset(g.value for g in Graha)

_VALID_TOP_KEYS: frozenset[str] = frozenset({
    "planets", "houses", "yogas", "lagna", "aspects", "nakshatra_ascendant", "metadata",
    "timing", "transit",
})


def _validate_feature_path(path: str, rule_id: str) -> None:
    """Raise RuleError for unknown or malformed feature paths.

    Validates the top-level namespace and the second component for planets/houses.
    Called at load time so invalid rules are caught before any chart is processed.
    """
    parts = path.split(".")
    if not parts or not parts[0]:
        raise RuleError(f"Rule '{rule_id}': empty feature path")

    top = parts[0]
    if top not in _VALID_TOP_KEYS:
        raise RuleError(
            f"Rule '{rule_id}': unknown feature namespace '{top}' in path '{path}'"
        )

    if top == "planets" and len(parts) >= 2 and parts[1] not in _VALID_GRAHAS:
        raise RuleError(
            f"Rule '{rule_id}': unknown graha '{parts[1]}' in path '{path}'"
        )

    if top == "houses" and len(parts) >= 2:
        seg = parts[1]
        if not seg.isdigit() or not (1 <= int(seg) <= 12):
            raise RuleError(
                f"Rule '{rule_id}': invalid house number '{seg}' in path '{path}'"
            )


def load_rule_set(path: str) -> list[RuleDefinition]:
    """Load and validate rules from a YAML file or a directory of YAML files.

    Files in a directory are processed in sorted order. Each file must contain
    a YAML list of rule dicts. All feature paths are validated at load time;
    duplicate rule IDs across files raise a RuleError.

    Raises:
        ConfigError: YAML parse error or non-list file structure.
        RuleError: Invalid rule schema, unknown feature path, or duplicate rule_id.
    """
    p = Path(path)
    if p.is_dir():
        yaml_files = sorted(p.glob("*.yaml")) + sorted(p.glob("*.yml"))
        if not yaml_files:
            return []
    elif p.is_file():
        yaml_files = [p]
    else:
        raise ConfigError(f"Rule path does not exist: {path}")

    rules: list[RuleDefinition] = []
    seen_ids: set[str] = set()

    for yaml_file in yaml_files:
        try:
            raw = yaml.safe_load(yaml_file.read_text())
        except yaml.YAMLError as exc:
            raise ConfigError(f"YAML parse error in {yaml_file}: {exc}") from exc

        if not isinstance(raw, list):
            raise ConfigError(f"Rule file {yaml_file} must contain a YAML list at the top level")

        for item in raw:
            try:
                rule = RuleDefinition.model_validate(item)
            except Exception as exc:
                raise RuleError(
                    f"Rule validation error in {yaml_file}: {exc}"
                ) from exc

            if rule.rule_id in seen_ids:
                raise RuleError(f"Duplicate rule_id '{rule.rule_id}' found in {yaml_file}")
            seen_ids.add(rule.rule_id)

            for cond in rule.conditions:
                _validate_feature_path(cond.feature, rule.rule_id)

            rules.append(rule)

    return rules
