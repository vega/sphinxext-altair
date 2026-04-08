# Tests are inspired by the test suite of sphinx itself
from __future__ import annotations

import re
from typing import TYPE_CHECKING, cast

import pytest

from altair import SCHEMA_URL
from sphinxext_altair.altairplot import (
    VEGA_JS_URL_DEFAULT,
    VEGAEMBED_JS_URL_DEFAULT,
    VEGALITE_JS_URL_DEFAULT,
    AltairPlotWarning,
    purge_altair_namespaces,
    validate_links,
)

if TYPE_CHECKING:
    from sphinx.application import Sphinx

    from sphinxext_altair.altairplot import BuildEnvironment


@pytest.mark.parametrize("add_namespaces_attr", [True, False])
@pytest.mark.sphinx(testroot="altairplot")
def test_purge_altair_namespaces(add_namespaces_attr: bool, app: Sphinx) -> None:
    env: BuildEnvironment = cast("BuildEnvironment", app.env)
    if add_namespaces_attr:
        env._altair_namespaces = {"docname": {}}

    # Test for a docname that exists
    purge_altair_namespaces(app, env, "docname")
    if add_namespaces_attr:
        assert env._altair_namespaces == {}
    else:
        assert not hasattr(env, "_altair_namespaces")

    # Test for a docname that does not exist
    purge_altair_namespaces(app, env, "docname2")


@pytest.mark.parametrize(
    ("links", "expected"),
    [
        ("none", False),
        ("None", False),
        ("editor unknown", "raise"),
        ("editor source", {"editor": True, "source": True, "export": False}),
    ],
)
def test_validate_links(links: str, expected: str | bool | dict[str, bool]) -> None:
    if expected == "raise":
        with pytest.raises(
            ValueError, match=r"Following links are invalid: \['unknown'\]"
        ):
            output = validate_links(links)
    else:
        output = validate_links(links)
        assert output == expected


@pytest.mark.sphinx(testroot="altairplot", freshenv=True)
def test_altairplotdirective(app: Sphinx) -> None:
    with pytest.warns(
        AltairPlotWarning,
        match=re.compile(
            r"errors_warnings\.rst:5\n.+polars\.DataFrame\(\{\"a\": \[1, 2, 3\], \"b\": \[4, 5, 6\]\}\)",
            re.DOTALL,
        ),
    ):
        app.builder.build_all()
    result = (app.outdir / "index.html").read_text(encoding="utf8")
    assert result.count("https://cdn.jsdelivr.net/npm/vega@") == 1
    assert result.count("https://cdn.jsdelivr.net/npm/vega-lite@") == 1
    assert result.count("https://cdn.jsdelivr.net/npm/vega-embed@") == 1
    assert result.count(VEGAEMBED_JS_URL_DEFAULT)
    assert result.count(VEGALITE_JS_URL_DEFAULT)
    assert result.count(VEGA_JS_URL_DEFAULT)
    assert SCHEMA_URL in result

    assert 'id="index-rst-altair-source-0"' in result
    assert '<div id="index-rst-altair-plot-0"' not in result

    assert 'id="index-rst-altair-source-1"' in result
    assert 'id="index-rst-altair-plot-1"' in result
    assert '"actions": {"editor": true, "source": true, "export": true}' in result

    assert '<div id="index-rst-altair-plot-2">' in result
    assert '</div><div class="highlight-python notranslate">' in result

    assert 'id="index-rst-altair-source-3"' in result
    assert "Data({" in result

    assert '<div id="index-rst-altair-plot-4"' in result
    assert 'id="index-rst-altair-source-4"' not in result

    assert "Click to show code" in result
    assert '<div id="index-rst-altair-plot-5"' in result

    assert '<div id="index-rst-altair-plot-6"' in result
    assert '"actions": {"editor": true, "source": false, "export": false}' in result

    assert result.count('class="test-class"') == 1
    assert '<div id="index-rst-altair-plot-7" class="test-class">' in result
