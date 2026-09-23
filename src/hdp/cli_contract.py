"""Frozen public command and format markers for the beta CLI contract."""

from __future__ import annotations

from typing import Final


# This response contract is independent from the factory package version and
# from the HDP/HIR document versions.  It changes only when the shape or
# meaning of machine-readable CLI responses changes.
CLI_CONTRACT_VERSION: Final[str] = "0.1.0"

SUPPORTED_HDP_VERSION: Final[str] = "0.1.0"
SUPPORTED_HIR_VERSION: Final[str] = "0.1.0"
SUPPORTED_BINDING_VERSION: Final[str] = "0.1.0"
SUPPORTED_ADAPTER_VERSION: Final[str] = "0.1.0"
SUPPORTED_GENERATED_MANIFEST_VERSION: Final[str] = "1"
SUPPORTED_INSTALL_MANIFEST_VERSION: Final[str] = "1"
SUPPORTED_INSTALL_TRANSACTION_VERSION: Final[str] = "1"
SUPPORTED_RELEASE_MANIFEST_VERSION: Final[str] = "0.1.0"
# The only pre-beta generated format accepted by the compatibility path.  The
# old alpha emitted no runtime binding/adapter markers; accepting that shape is
# safe only for this exact released factory format and its canonical artifact
# set.
LEGACY_ALPHA_FACTORY_VERSION: Final[str] = "0.2.0a1"

PRODUCT_COMMANDS: Final[tuple[str, ...]] = (
    "init",
    "build",
    "install",
    "audit",
    "verify",
    "release",
    "doctor",
)

COMPATIBILITY_COMMANDS: Final[tuple[str, ...]] = (
    "init",
    "build",
    "install",
    "audit",
    "verify",
    "release",
    "doctor",
    "validate",
    "compile",
    "analyse",
    "test",
    "diff",
    "package",
    "verify-release",
)

COMPATIBILITY_ALIASES: Final[tuple[str, ...]] = ("generate", "inspect")

COMMAND_OPTION_FLAGS: Final[dict[str, tuple[str, ...]]] = {
    "init": ("--template", "--json"),
    "build": ("--output", "--force-generated", "--json"),
    "install": ("--project", "--harness", "--dry-run", "--json"),
    "audit": ("--output", "--allow-partial", "--json"),
    "verify": ("--json",),
    "release": ("--conformance", "--output", "--json"),
    "doctor": ("--json",),
    "validate": ("--json",),
    "compile": ("--binding", "--output", "--force-generated"),
    "generate": ("--binding", "--output", "--force-generated"),
    "analyse": ("--output", "--allow-partial"),
    "inspect": ("--output", "--allow-partial"),
    "test": ("--definition", "--binding"),
    "diff": (),
    "package": ("--definition", "--binding", "--output", "--conformance"),
    "verify-release": (),
}

# Click/Typer parameter order and names are part of the CLI surface too.  A
# renamed positional or option parameter can silently change generated help or
# invocation semantics even when its long flag remains unchanged.
COMMAND_PARAMETER_NAMES: Final[dict[str, tuple[str, ...]]] = {
    "init": ("directory", "template", "json_output"),
    "build": ("project", "output", "force_generated", "json_output"),
    "install": ("target", "project", "harness", "dry_run", "json_output"),
    "audit": ("harness", "output", "allow_partial", "json_output"),
    "verify": ("project", "json_output"),
    "release": ("project", "conformance", "output", "json_output"),
    "doctor": ("json_output",),
    "validate": ("definition", "json_output"),
    "compile": ("definition", "binding", "output", "force_generated"),
    "generate": ("definition", "binding", "output", "force_generated"),
    "analyse": ("harness", "output", "allow_partial"),
    "inspect": ("harness", "output", "allow_partial"),
    "test": ("harness", "definition", "binding"),
    "diff": ("left", "right"),
    "package": ("harness", "definition", "binding", "output", "conformance"),
    "verify-release": ("release",),
}

COMMAND_REQUIRED_PARAMETERS: Final[dict[str, tuple[str, ...]]] = {
    "init": (),
    "build": (),
    "install": ("target",),
    "audit": ("harness",),
    "verify": (),
    "release": (),
    "doctor": (),
    "validate": ("definition",),
    "compile": ("definition", "binding", "output"),
    "generate": ("definition", "binding", "output"),
    "analyse": ("harness", "output"),
    "inspect": ("harness", "output"),
    "test": ("harness", "definition", "binding"),
    "diff": ("left", "right"),
    "package": ("harness", "definition", "binding", "output"),
    "verify-release": ("release",),
}

COMMAND_FLAG_PARAMETERS: Final[dict[str, tuple[str, ...]]] = {
    "init": ("json_output",),
    "build": ("force_generated", "json_output"),
    "install": ("dry_run", "json_output"),
    "audit": ("allow_partial", "json_output"),
    "verify": ("json_output",),
    "release": ("json_output",),
    "doctor": ("json_output",),
    "validate": ("json_output",),
    "compile": ("force_generated",),
    "generate": ("force_generated",),
    "analyse": ("allow_partial",),
    "inspect": ("allow_partial",),
    "test": (),
    "diff": (),
    "package": (),
    "verify-release": (),
}


def unsupported_version_message(
    subject: str, actual: object, expected: str
) -> str:
    """Return one actionable diagnostic for an unsupported version marker."""

    if actual is None:
        rendered = "<missing>"
    elif isinstance(actual, bool):
        rendered = f"{actual!r} (boolean)"
    elif isinstance(actual, (int, float)):
        rendered = f"{actual!r} (number)"
    elif isinstance(actual, str):
        rendered = f"{actual!r} (string)"
    else:
        rendered = f"{actual!r} ({type(actual).__name__})"
    return (
        f"unsupported {subject} version {rendered}; beta supports {expected}. "
        "No automatic migration is provided; update the source explicitly "
        "and rerun validation."
    )
