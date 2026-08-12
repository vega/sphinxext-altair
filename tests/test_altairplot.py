# Tests are inspired by the test suite of sphinx itself
from __future__ import annotations

import json
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

    def extract_embed_values(
        plot_id: int,
    ) -> tuple[dict[str, object], dict[str, object], str | None]:
        div_id = f"index-rst-altair-plot-{plot_id}"
        match = re.search(
            rf'<div id="{div_id}"(?: class="([^"]+)")?>\s*<script>.*?'
            rf"var spec = (\{{.*?\}});\s*"
            rf"var opt = (\{{.*?\}});\s*"
            rf"vegaEmbed\('#{div_id}', spec, opt\)",
            result,
            re.DOTALL,
        )
        assert match is not None
        class_name = match.group(1)
        spec = json.loads(match.group(2))
        opt = json.loads(match.group(3))
        return spec, opt, class_name

    for plot_id in (1, 2, 4, 5, 6, 7):
        spec, opt, _ = extract_embed_values(plot_id)
        assert spec["$schema"] == SCHEMA_URL
        assert opt["mode"] == "vega-lite"
        assert opt["renderer"] == "canvas"

    assert 'id="index-rst-altair-source-0"' in result
    assert '<div id="index-rst-altair-plot-0"' not in result

    assert 'id="index-rst-altair-source-1"' in result
    _, plot_1_opt, _ = extract_embed_values(1)
    assert plot_1_opt["actions"] == {"editor": True, "source": True, "export": True}

    code_below_section = re.search(
        r'<section id="code-below-plot">.*?</section>', result, re.DOTALL
    )
    assert code_below_section is not None
    assert re.search(
        r'<div id="index-rst-altair-plot-2">.*?</div><div class="highlight-python notranslate">',
        code_below_section.group(0),
        re.DOTALL,
    )

    assert 'id="index-rst-altair-source-3"' in result
    assert "Data({" in result

    extract_embed_values(4)
    assert 'id="index-rst-altair-source-4"' not in result

    assert "Click to show code" in result
    assert re.search(r"<details>.*?Click to show code.*?</details>", result, re.DOTALL)
    extract_embed_values(5)

    _, plot_6_opt, _ = extract_embed_values(6)
    assert plot_6_opt["actions"] == {"editor": True, "source": False, "export": False}

    _, _, plot_7_class = extract_embed_values(7)
    assert plot_7_class == "test-class"
