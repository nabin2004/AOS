"""Safe Python introspection engine for extracting structured function, class, and module metadata."""

from __future__ import annotations

import inspect
import types
from typing import Any, Callable, Dict, List, Optional, Tuple

from aos_lkg.schema.nodes import ParameterInfo, ReturnInfo


def safe_signature(obj: Any) -> Tuple[str, List[ParameterInfo], Optional[ReturnInfo]]:
    """
    Safely extract signature, parameters list, and return info for any Python object.
    Handles pure Python functions, methods, built-ins, and compiled C/Cython routines.
    """
    params: List[ParameterInfo] = []
    returns: Optional[ReturnInfo] = None
    sig_str = "()"

    # Try standard inspect.signature
    try:
        sig = inspect.signature(obj)
        sig_str = str(sig)

        for name, param in sig.parameters.items():
            type_str = None
            if param.annotation is not inspect.Parameter.empty:
                if isinstance(param.annotation, type):
                    type_str = param.annotation.__name__
                else:
                    type_str = str(param.annotation)

            default_str = None
            is_req = True
            if param.default is not inspect.Parameter.empty:
                is_req = False
                default_str = repr(param.default)

            params.append(
                ParameterInfo(
                    name=name,
                    type_str=type_str,
                    default_str=default_str,
                    is_required=is_req,
                    description=None,
                )
            )

        if sig.return_annotation is not inspect.Signature.empty:
            ret_type = (
                sig.return_annotation.__name__
                if isinstance(sig.return_annotation, type)
                else str(sig.return_annotation)
            )
            returns = ReturnInfo(type_str=ret_type, description=None)

        return sig_str, params, returns
    except (TypeError, ValueError):
        pass

    # Fallback for docstring signature parsing (e.g. C-extensions / ufuncs)
    doc = inspect.getdoc(obj) or ""
    first_line = doc.split("\n")[0].strip() if doc else ""
    if "(" in first_line and ")" in first_line:
        # e.g., "brentq(f, a, b, args=(), xtol=2e-12, rtol=8.881784197001252e-16, maxiter=100, full_output=False, disp=True)"
        sig_candidate = first_line[first_line.find("(") : first_line.rfind(")") + 1]
        sig_str = sig_candidate

        # Extract basic parameter names
        inner = sig_str[1:-1].strip()
        if inner:
            raw_params = [p.strip() for p in inner.split(",") if p.strip()]
            for p in raw_params:
                if "=" in p:
                    p_name, p_default = p.split("=", 1)
                    params.append(
                        ParameterInfo(
                            name=p_name.strip(),
                            default_str=p_default.strip(),
                            is_required=False,
                        )
                    )
                else:
                    params.append(
                        ParameterInfo(
                            name=p.strip(),
                            is_required=True,
                        )
                    )

    return sig_str, params, returns


def get_clean_docstring(obj: Any) -> Optional[str]:
    """Retrieve and clean the docstring of an object."""
    try:
        doc = inspect.getdoc(obj)
        if doc and doc.strip():
            return doc.strip()
    except Exception:
        pass
    return None


def is_compiled_object(obj: Any) -> bool:
    """Check if object is a compiled C/Cython extension or built-in."""
    return (
        inspect.isbuiltin(obj)
        or isinstance(obj, types.BuiltinFunctionType)
        or type(obj).__name__ == "ufunc"
        or not hasattr(obj, "__code__")
    )


def safe_get_source(obj: Any) -> Optional[str]:
    """Safely attempt to get source code if available."""
    try:
        return inspect.getsource(obj)
    except Exception:
        return None
