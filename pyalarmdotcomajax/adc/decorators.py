"""Decorators for adc cli commands."""

import inspect
from collections.abc import Callable
from functools import wraps
from itertools import chain, compress, groupby
from operator import attrgetter
from typing import Any

import typer

from pyalarmdotcomajax.adc.params import (
    Param_CookieT,
    Param_DebugT,
    Param_DeviceNameT,
    Param_JsonT,
    Param_OtpMethodT,
    Param_OtpT,
    Param_PasswordT,
    Param_UsernameT,
    Param_VersionT,
)

# ruff: noqa: T201 C901 UP007

###############################################
###############################################
## ARGUMENT & OPTION SHARING ACROSS COMMANDS ##
###############################################
###############################################
#
# Source: https://github.com/tiangolo/typer/issues/153#issuecomment-2002389855
#


def common_params(
    ctx: typer.Context,
    username: Param_UsernameT,
    password: Param_PasswordT,
    otp_method: Param_OtpMethodT = None,
    cookie: Param_CookieT = None,
    json: Param_JsonT = False,
    otp: Param_OtpT = None,
    device_name: Param_DeviceNameT = None,
    debug: Param_DebugT = False,
    version: Param_VersionT = False,
) -> Any:
    """Share common parameters across multiple commands."""

    ...


def merge_signatures(
    signature: inspect.Signature, other: inspect.Signature, drop: list[str] | None = None, strict: bool = True
) -> tuple[inspect.Signature, list[int], list[int]]:
    """
    Merge two signatures.

    Returns a new signature where the parameters of the second signature have been
    injected in the first if they weren't already there (i.e. same name not found).
    Also returns two maps that can be used to find out if a parameter in the new
    signature was present in the originals (or can be used to recover the original
    signatures).

    If `strict` is true, parameters with same name in both original signatures must
    be of same kind (positional only, keyword only or maybe keyword). Otherwise a
    ValueError is raised.
    """
    # Split parameters by kind
    groups = {k: list(g) for k, g in groupby(signature.parameters.values(), attrgetter("kind"))}

    # Append parameters from other signature
    for name, param in other.parameters.items():
        if drop and name in drop:
            continue
        if name in signature.parameters:
            if strict and param.kind != signature.parameters[name].kind:
                raise ValueError(f"Both signature have same parameter {name!r} but with " f"different kind")
            continue

        # Variadic args (*args or **kwargs)
        if param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
            if param.kind not in groups:
                groups[param.kind] = [param]
            elif param.name != groups[param.kind][0].name:
                raise ValueError(
                    f"Variadic args must have same name when present "
                    f"on both signatures: got {groups[param.kind][0].name!r} "
                    f"and {param.name!r}"
                )
        # Non variadic args
        else:
            groups.setdefault(param.kind, []).append(param)

    # Depending on input signatures, the resulting one can be invalid as the
    # insertion order could yield to a parameter with a default value being in
    # front of a parameter without default value.
    #
    # Make sure params with default values are put after params without default.
    # This is done on a per kind basis (?) and can lead to unintuitive parameter
    # reordering...
    for params in groups.values():
        if params:
            params.sort(key=lambda p: bool(p.default != inspect.Parameter.empty))

    # Merged parameters list
    parameters = sorted(chain(*(groups.values())), key=attrgetter("kind"))

    # Memoize if parameters were present in original signatures
    sel_0 = [1 if p.name in signature.parameters else 0 for p in parameters]
    sel_1 = [1 if p.name in other.parameters else 0 for p in parameters]

    return signature.replace(parameters=parameters), sel_0, sel_1


def with_paremeters(shared: Callable) -> Callable:
    """Share parameters between commands with this decorator."""

    def wrapper(command: Callable) -> Callable:
        """Wrap the command with shared parameters."""
        signature, sel_0, sel_1 = merge_signatures(inspect.signature(command), inspect.signature(shared))

        @wraps(command)
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            """Wrap this function."""
            # Bind values
            bound = signature.bind(*args, **kwargs)
            bound.apply_defaults()

            # Call outer function with a set of selected parameters
            shared(*compress(bound.args, sel_1))

            # Call inner function with another set of selected parameters
            return command(*compress(bound.args, sel_0))

        wrapped.__signature__ = signature  # type: ignore
        return wrapped

    return wrapper


def cli_action() -> Callable:
    """
    Decorate a method to mark it as a CLI action with a given description.

    This decorator adds the method and its description to a `__cli_actions__` attribute
    on the method, used for identifying CLI actions within a class.

    Args:
        func: The method to decorate.
        description: Human-readable description of the CLI action.

    Returns:
        The decorated method.

    """

    def decorator(func: Callable) -> Callable:
        if not hasattr(func, "__cli_actions__"):
            func.__cli_actions__ = {}  # type: ignore  # Initialize once if not already present

        func.__cli_actions__[func.__name__] = {func.__name__: func.__doc__}  # type: ignore

        return func

    return decorator
