"""Garmin Connect MCP server.

Introspects a logged-in ``garminconnect.Garmin`` instance and exposes every
public read method (and optionally write methods) as an MCP tool over stdio.
Run ``python auth.py`` once to seed tokens before starting this server.
"""
import inspect
import os
from datetime import date, datetime
from decimal import Decimal
from functools import wraps
from pathlib import Path

from garminconnect import (
    Garmin,
    GarminConnectAuthenticationError,
    GarminConnectConnectionError,
    GarminConnectTooManyRequestsError,
)
from mcp.server.fastmcp import FastMCP

TOKEN_PATH = str(Path(os.environ.get("GARMINTOKENS", "~/.garminconnect")).expanduser())
ALLOW_WRITES = os.environ.get("GARMIN_ALLOW_WRITES", "").lower() in ("1", "true", "yes")

READ_PREFIXES = ("get_", "list_", "count_", "search_", "find_", "fetch_")
WRITE_PREFIXES = ("upload_", "create_", "schedule_", "delete_", "update_", "set_",
                  "unschedule_", "add_", "remove_", "import_", "track_")
DENYLIST = {"login", "resume_login", "connectapi", "download", "logout",
            "remove_tokens", "disconnect"}

mcp = FastMCP("garmin")

garmin = Garmin()
garmin.login(TOKEN_PATH)

_profile_number_cache: str | None = None


def _profile_number() -> str:
    """Garmin's userProfileNumber, fetched lazily and cached. Required by
    get_gear / get_gear_defaults, which otherwise force the caller to know
    an opaque internal ID."""
    global _profile_number_cache
    if _profile_number_cache is not None:
        return _profile_number_cache
    for source in (garmin.get_userprofile_settings, garmin.get_user_profile):
        data = source() or {}
        for key in ("userProfilePk", "userProfilePK", "id", "userProfileId",
                    "userProfileNumber", "profileId"):
            if key in data and data[key] is not None:
                _profile_number_cache = str(data[key])
                return _profile_number_cache
    raise RuntimeError(
        "Could not determine userProfileNumber from Garmin profile endpoints."
    )


PROFILE_AUTO_FILL = {"get_gear", "get_gear_defaults"}


def to_json_safe(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, bytes):
        return obj.decode("utf-8", errors="replace")
    if isinstance(obj, dict):
        return {k: to_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_json_safe(v) for v in obj]
    return obj


def coerce_args(sig, args, kwargs):
    """Parse string date/datetime args into date/datetime objects when the
    parameter annotation says so. Leave everything else alone."""
    try:
        bound = sig.bind_partial(*args, **kwargs)
    except TypeError:
        return args, kwargs
    for name, value in list(bound.arguments.items()):
        if not isinstance(value, str):
            continue
        param = sig.parameters.get(name)
        if not param:
            continue
        ann = param.annotation
        if ann is date:
            try:
                bound.arguments[name] = date.fromisoformat(value)
            except ValueError:
                pass
        elif ann is datetime:
            try:
                bound.arguments[name] = datetime.fromisoformat(value)
            except ValueError:
                pass
    return bound.args, bound.kwargs


def sanitize_signature(sig):
    """FastMCP rejects parameter names starting with underscore. Rename any
    such params by stripping leading underscores and return a mapping from
    new name -> original name so the wrapper can translate kwargs back."""
    renames = {}
    new_params = []
    for p in sig.parameters.values():
        if p.name.startswith("_"):
            clean = p.name.lstrip("_") or p.name
            while clean in {np.name for np in new_params} or clean in renames:
                clean = clean + "_"
            renames[clean] = p.name
            new_params.append(p.replace(name=clean))
        else:
            new_params.append(p)
    if renames:
        return sig.replace(parameters=new_params), renames
    return sig, {}


def make_tool(method, name):
    sig = None
    renames = {}
    try:
        raw_sig = inspect.signature(method)
        sig, renames = sanitize_signature(raw_sig)
    except (ValueError, TypeError):
        pass

    autofill_profile = name in PROFILE_AUTO_FILL
    if autofill_profile and sig is not None:
        # Drop userProfileNumber from the exposed schema; the wrapper fills it.
        new_params = [p for p in sig.parameters.values() if p.name != "userProfileNumber"]
        sig = sig.replace(parameters=new_params)

    @wraps(method)
    def wrapper(*args, **kwargs):
        try:
            if renames:
                for new, old in renames.items():
                    if new in kwargs:
                        kwargs[old] = kwargs.pop(new)
            if sig is not None:
                args, kwargs = coerce_args(sig, args, kwargs)
                for new, old in renames.items():
                    if new in kwargs:
                        kwargs[old] = kwargs.pop(new)
            if autofill_profile and "userProfileNumber" not in kwargs:
                kwargs["userProfileNumber"] = _profile_number()
            result = method(*args, **kwargs)
        except GarminConnectAuthenticationError as e:
            raise RuntimeError(
                f"Garmin authentication failed: {e}. "
                "Re-run `python auth.py` to refresh tokens."
            ) from e
        except GarminConnectTooManyRequestsError as e:
            raise RuntimeError(
                f"Garmin rate limit hit: {e}. Back off and retry later."
            ) from e
        except GarminConnectConnectionError as e:
            raise RuntimeError(f"Garmin connection error: {e}") from e
        return to_json_safe(result)

    wrapper.__name__ = name
    wrapper.__doc__ = (method.__doc__ or "").strip() or f"Garmin Connect: {name}"
    if sig is not None:
        wrapper.__signature__ = sig
    return wrapper


def register_tools():
    prefixes = READ_PREFIXES + (WRITE_PREFIXES if ALLOW_WRITES else ())
    count = 0
    for attr in dir(garmin):
        if attr.startswith("_") or attr in DENYLIST:
            continue
        if not attr.startswith(prefixes):
            continue
        method = getattr(garmin, attr)
        if not callable(method):
            continue
        tool = make_tool(method, attr)
        mcp.add_tool(tool, name=attr, description=tool.__doc__)
        count += 1
    return count


register_tools()


def main():
    mcp.run()


if __name__ == "__main__":
    main()
