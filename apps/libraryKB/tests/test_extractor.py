"""Unit tests for extractor introspection, doc parsing, and crawling."""

import pytest
import scipy.optimize
import numpy as np

from aos_lkg.extractor.inspector import safe_signature, get_clean_docstring, is_compiled_object
from aos_lkg.extractor.doc_parser import parse_docstring
from aos_lkg.extractor.filters import is_public_symbol, is_deprecated
from aos_lkg.extractor.crawler import PackageCrawler


def test_safe_signature_scipy_brentq():
    sig_str, params, returns = safe_signature(scipy.optimize.brentq)
    assert "(" in sig_str and ")" in sig_str
    param_names = [p.name for p in params]
    assert "f" in param_names
    assert "a" in param_names
    assert "b" in param_names


def test_safe_signature_numpy_ufunc():
    sig_str, params, returns = safe_signature(np.sin)
    assert "(" in sig_str and ")" in sig_str
    assert len(params) >= 1


def test_parse_docstring_numpy_format():
    doc = """
    Compute the root of a function.

    Parameters
    ----------
    f : callable
        Function to find root of.
    a : float
        Lower bracket boundary.
    b : float
        Upper bracket boundary.

    Returns
    -------
    root : float
        The calculated root.
    """
    parsed = parse_docstring(doc)
    assert parsed.summary.startswith("Compute the root")
    assert "f" in parsed.parameters
    assert "callable" in parsed.parameters["f"]["type"]
    assert "a" in parsed.parameters
    assert "b" in parsed.parameters


def test_crawler_scipy_optimize():
    crawler = PackageCrawler(max_depth=1, include_submodules=False)
    kg = crawler.crawl_package("scipy", target_submodules=["optimize"])

    assert len(kg.nodes) > 0
    # Check that library node exists
    lib_node = kg.get_node("lib:scipy")
    assert lib_node is not None
    assert lib_node.name == "scipy"

    # Check that function nodes were discovered
    fn_nodes = [n for n in kg.nodes.values() if n.type == "function"]
    assert len(fn_nodes) > 0
