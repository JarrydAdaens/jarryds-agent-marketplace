"""Privacy Gate 1: prove public visibility cannot be represented in config.

Run from the plugin root:
    uv run --with pytest --with pyyaml --with jsonschema pytest tests/test_config_schema.py
"""

import json
from pathlib import Path

import jsonschema
import pytest
import yaml

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
SCHEMA = json.loads((PLUGIN_ROOT / "schemas" / "config.schema.json").read_text(encoding="utf-8"))
EXAMPLE = yaml.safe_load(
    (PLUGIN_ROOT / "config" / "repository-savior.example.yaml").read_text(encoding="utf-8")
)


def walk(node):
    yield node
    if isinstance(node, dict):
        for value in node.values():
            yield from walk(value)
    elif isinstance(node, list):
        for value in node:
            yield from walk(value)


class TestNoVisibilityRepresentable:
    def test_schema_defines_no_visibility_property(self):
        for node in walk(SCHEMA):
            if isinstance(node, dict):
                for key in node.get("properties", {}):
                    assert key not in ("visibility", "public", "internal", "private")

    def test_all_objects_forbid_additional_properties(self):
        """A visibility key cannot be smuggled in beside the known keys."""
        for node in walk(SCHEMA):
            if isinstance(node, dict) and "properties" in node:
                assert node.get("additionalProperties") is False

    @pytest.mark.parametrize(
        "injection",
        [
            {"visibility": "public"},
            {"github": {**EXAMPLE["github"], "visibility": "public"}},
            {"publication": {**EXAMPLE["publication"], "visibility": "public"}},
            {"publication": {**EXAMPLE["publication"], "require_audit_pass": False}},
            {"execution": {**EXAMPLE["execution"], "maximum_parallel_repositories": 4}},
            {"naming": {**EXAMPLE["naming"], "collision_policy": "overwrite"}},
        ],
    )
    def test_injected_overrides_are_rejected(self, injection):
        config = {**EXAMPLE, **injection}
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(config, SCHEMA)


class TestExampleConfig:
    def test_example_validates(self):
        jsonschema.validate(EXAMPLE, SCHEMA)

    def test_example_contains_no_visibility_key(self):
        for node in walk(EXAMPLE):
            if isinstance(node, dict):
                assert "visibility" not in node
