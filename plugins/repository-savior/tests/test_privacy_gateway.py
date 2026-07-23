"""Privacy Gate 6: prove the PRIVATE_ONLY policy cannot be circumvented.

Run from the plugin root:
    uv run --with pytest pytest tests/test_privacy_gateway.py
"""

import sys
from pathlib import Path

import pytest

GATEWAY_DIR = Path(__file__).resolve().parent.parent / "gateways" / "github-private-only"
sys.path.insert(0, str(GATEWAY_DIR))

import create_private_repo as gateway  # noqa: E402
import verify_remote_privacy as verifier  # noqa: E402


class TestCreateCommand:
    def test_always_private(self):
        command = gateway.build_create_command("owner", "repo")
        assert "--private" in command

    def test_private_even_with_all_options(self):
        command = gateway.build_create_command(
            "owner", "repo", description="d", allow_issues=True, allow_wiki=True
        )
        assert "--private" in command

    def test_no_visibility_parameter_exists(self):
        """The builder's signature has no way to express visibility."""
        import inspect

        params = inspect.signature(gateway.build_create_command).parameters
        assert "visibility" not in params
        assert "public" not in params
        assert "private" not in params  # not even opt-in: it is unconditional

    def test_command_never_contains_public_tokens(self):
        command = " ".join(gateway.build_create_command("owner", "repo", "desc"))
        assert "--public" not in command
        assert "--visibility" not in command

    def test_features_disabled_by_default(self):
        command = gateway.build_create_command("owner", "repo")
        assert "--disable-issues" in command
        assert "--disable-wiki" in command


class TestForbiddenTokenRejection:
    @pytest.mark.parametrize(
        "argv",
        [
            ["create_private_repo.py", "owner", "repo", "--public"],
            ["create_private_repo.py", "owner", "repo", "--visibility", "public"],
            ["create_private_repo.py", "owner", "repo", "--visibility", "internal"],
            ["create_private_repo.py", "owner", "repo", "--VISIBILITY", "PUBLIC"],
            ["gh", "repo", "edit", "owner/repo", "--visibility", "public"],
            ["create_private_repo.py", "owner", "repo", "--internal"],
        ],
    )
    def test_rejects_visibility_overrides(self, argv):
        with pytest.raises(gateway.ForbiddenVisibilityError):
            gateway.reject_forbidden(argv)

    def test_accepts_clean_invocation(self):
        gateway.reject_forbidden(
            ["create_private_repo.py", "owner", "repo", "--description", "Recovered"]
        )


class TestRemoteVerification:
    GOOD = {
        "isPrivate": True,
        "visibility": "PRIVATE",
        "owner": {"login": "owner"},
        "name": "repo",
    }

    def test_verified_private_passes(self):
        assert verifier.evaluate(self.GOOD, "owner", "repo") == []

    @pytest.mark.parametrize(
        "override",
        [
            {"isPrivate": False},
            {"isPrivate": None},
            {"visibility": "PUBLIC"},
            {"visibility": "INTERNAL"},
            {"visibility": ""},
            {"owner": {"login": "someone-else"}},
            {"name": "wrong-name"},
        ],
    )
    def test_any_deviation_blocks(self, override):
        payload = {**self.GOOD, **override}
        assert verifier.evaluate(payload, "owner", "repo") != []

    def test_empty_payload_blocks(self):
        assert verifier.evaluate({}, "owner", "repo") != []
