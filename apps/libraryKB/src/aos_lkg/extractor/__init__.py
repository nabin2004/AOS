"""Extractor subpackage exports."""

from aos_lkg.extractor.inspector import (
    safe_signature,
    get_clean_docstring,
    is_compiled_object,
    safe_get_source,
)
from aos_lkg.extractor.doc_parser import parse_docstring, ParsedDocstring
from aos_lkg.extractor.filters import (
    is_public_symbol,
    is_deprecated,
    get_canonical_module,
    should_skip_module,
)
from aos_lkg.extractor.crawler import PackageCrawler

__all__ = [
    "safe_signature",
    "get_clean_docstring",
    "is_compiled_object",
    "safe_get_source",
    "parse_docstring",
    "ParsedDocstring",
    "is_public_symbol",
    "is_deprecated",
    "get_canonical_module",
    "should_skip_module",
    "PackageCrawler",
]
