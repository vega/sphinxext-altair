"""
Altair Plot Sphinx Extension.

This extension provides a means of inserting live-rendered Altair plots within
sphinx documentation using the directive ``altair-plot``. You can also use it
to set-up various options prior to running the plot code. For example::

    .. altair-plot::
        :output: none

        import altair as alt
        import pandas as pd
        data = pd.DataFrame({'a': list('CCCDDDEEE'),
                             'b': [2, 7, 4, 1, 2, 6, 8, 4, 7]})

    .. altair-plot::

        alt.Chart(data).mark_point().encode(
            x='a',
            y='b'
        )

In the case of the ``altair-plot`` code, the *last statement* of the code-block
should contain the chart object you wish to be rendered.

Options
-------
The directives have the following options::

    .. altair-plot::
        :namespace:  # specify a plotting namespace that is persistent within the doc
        :hide-code:  # if set, then hide the code and only show the plot
        :remove-code:  # if set, then remove the code and only show the plot
        :code-below:  # if set, then code is below rather than above the figure
        :output:  [plot|repr|stdout|none]
        :alt: text  # Alternate text when plot cannot be rendered
        :links: editor source export  # specify one or more of these options
        :chart-var-name: chart  # name of variable in namespace containing output
        :strict: # if set, then code with errors will raise instead of being skipped
        :div_class: # class name for the div element containing the plot


Additionally, this extension introduces a global configuration
``altairplot_links``, set in your ``conf.py`` which is a dictionary
of links that will appear below plots, unless the ``:links:`` option
again overrides it. It should look something like this::

    # conf.py
    # ...
    altairplot_links = {"editor": True, "source": True, "export": True}
    # ...

If this configuration is not specified, all are set to True.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import typing as t
import warnings
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, ClassVar, Literal

import jinja2
from docutils import nodes
from docutils.parsers.rst import Directive
from docutils.parsers.rst.directives import flag, unchanged
from sphinx.locale import _

import altair as alt
from altair.utils.execeval import eval_block
from altair.utils.schemapi import SchemaValidationError

if TYPE_CHECKING:
    from sphinx.application import Sphinx
    from sphinx.environment import BuildEnvironment as _BuildEnvironment

    class BuildEnvironment(_BuildEnvironment):
        _altair_namespaces: dict[str, Any]


# These default URLs can be changed in conf.py; see setup() below.
VEGA_JS_URL_DEFAULT = f"https://cdn.jsdelivr.net/npm/vega@{alt.VEGA_VERSION}"
VEGALITE_JS_URL_DEFAULT = (
    f"https://cdn.jsdelivr.net/npm/vega-lite@{alt.VEGALITE_VERSION}"
)
VEGAEMBED_JS_URL_DEFAULT = (
    f"https://cdn.jsdelivr.net/npm/vega-embed@{alt.VEGAEMBED_VERSION}"
)


VGL_TEMPLATE = jinja2.Template(
    """
<div id="{{ div_id }}"{% if div_class %} class="{{ div_class }}"{% endif %}>
<script>
  // embed when document is loaded, to ensure vega library is available
  // this works on all modern browsers, except IE8 and older
  document.addEventListener("DOMContentLoaded", function(event) {
      var spec = {{ spec }};
      var opt = {
        "mode": "{{ mode }}",
        "renderer": "{{ renderer }}",
        "actions": {{ actions}}
      };
      vegaEmbed('#{{ div_id }}', spec, opt).catch(console.err);
  });
</script>
</div>
"""
)


class altair_plot(nodes.General, nodes.Element):
    body: list[str]


def purge_altair_namespaces(app: Sphinx, env: BuildEnvironment, docname: str) -> None:
    if not hasattr(env, "_altair_namespaces"):
        return
    env._altair_namespaces.pop(docname, {})


DEFAULT_ALTAIRPLOT_LINKS: dict[str, bool] = {"editor": True, "source": True, "export": True}  # fmt: off


@lru_cache(maxsize=256)
def strip_lower(content: str, /) -> str:
    return content.strip().lower()


def validate_links(links: str) -> dict[str, bool] | Literal[False]:
    if strip_lower(links) == "none":
        return False

    links_split = links.strip().split()
    defaults = DEFAULT_ALTAIRPLOT_LINKS
    if set(links_split) <= defaults.keys():
        return {s: s in links_split for s in defaults}
    else:
        diff = set(links_split) - defaults.keys()
        msg = f"Following links are invalid: {list(diff)}"
        raise ValueError(msg)


def validate_output(output: str) -> str:
    output = strip_lower(output)
    if output not in {"plot", "repr", "stdout", "none"}:
        msg = ":output: flag must be one of [plot|repr|stdout|none]"
        raise ValueError(msg)
    return output


class AltairPlotDirective(Directive):
    has_content: ClassVar[bool] = True
    option_spec: ClassVar[dict[str, Callable[[str], Any]]] = {
        "hide-code": flag,
        "remove-code": flag,
        "code-below": flag,
        "namespace": unchanged,
        "output": validate_output,
        "alt": unchanged,
        "links": validate_links,
        "chart-var-name": unchanged,
        "strict": flag,
        "div_class": strip_lower,
    }

    def run(self) -> list[nodes.Element]:
        env = t.cast("BuildEnvironment", self.state.document.settings.env)
        app = env.app

        hide_code = "hide-code" in self.options
        code_below = "code-below" in self.options

        if not hasattr(env, "_altair_namespaces"):
            env._altair_namespaces = {}
        namespace_id = self.options.get("namespace", "default")
        namespace = env._altair_namespaces.setdefault(env.docname, {}).setdefault(
            namespace_id, {}
        )

        # Show code
        code = "\n".join(self.content)
        source_literal = nodes.literal_block(code, code)
        source_literal["language"] = "python"

        # get the name of the source file we are currently processing
        rst_source = self.state_machine.document["source"]
        rst_fp = Path(rst_source)

        # use the source file name to construct a friendly target_id
        serialno = env.new_serialno("altair-plot")
        rst_base = rst_fp.name.replace(".", "-")
        div_id = f"{rst_base}-altair-plot-{serialno}"
        target_id = f"{rst_base}-altair-source-{serialno}"
        target_node = nodes.target("", "", ids=[target_id])

        # create the node in which the plot will appear;
        # this will be processed by html_visit_altair_plot
        plot_node = altair_plot(
            target_id=target_id,
            div_id=div_id,
            div_class=self.options.get("div_class", None),
            code=code,
            namespace=namespace,
            relpath=os.path.relpath(rst_fp.parent, env.srcdir),
            rst_source=rst_source,
            rst_lineno=self.lineno,
            links=self.options.get("links", app.builder.config.altairplot_links),
            output=self.options.get("output", "plot"),
            strict="strict" in self.options,
            **{"chart-var-name": self.options.get("chart-var-name", None)},
        )
        if "alt" in self.options:
            plot_node["alt"] = self.options["alt"]

        result: list[nodes.Element] = [target_node]
        if code_below:
            result.append(plot_node)
        if hide_code:
            html = "<details><summary><a>Click to show code</a></summary>"
            result.append(nodes.raw("", html, format="html"))
        if "remove-code" not in self.options:
            result.append(source_literal)
        if hide_code:
            html = "</details>"
            result.append(nodes.raw("", html, format="html"))
        if not code_below:
            result.append(plot_node)
        return result


def html_visit_altair_plot(self: altair_plot, node: nodes.Element) -> None:  # noqa: C901
    # Execute the code, saving output and namespace
    namespace = node["namespace"]
    try:
        f = io.StringIO()
        with contextlib.redirect_stdout(f):
            chart = eval_block(node["code"], namespace)
        stdout = f.getvalue()
    except Exception as err:
        msg = (
            f"altair-plot: {node['rst_source']}:{node['rst_lineno']} "
            f"Code Execution failed: {type(err).__name__}: {err!s}"
        )
        if node["strict"]:
            raise ValueError(msg) from err
        else:
            warnings.warn(msg, stacklevel=1)
            raise nodes.SkipNode from err

    if chart_name := node.get("chart-var-name", None):
        if chart_name in namespace:
            chart = namespace[chart_name]
        else:
            msg = f"chart-var-name='{chart_name}' not present in namespace"
            raise ValueError(msg)

    output = node["output"]

    if output == "none":
        raise nodes.SkipNode
    elif output == "stdout":
        if not stdout:
            raise nodes.SkipNode
        else:
            output_literal = nodes.literal_block(stdout, stdout)
            output_literal["language"] = "none"
            node.append(output_literal)
    elif output == "repr":
        if chart is None:
            raise nodes.SkipNode
        else:
            rep = f"    {chart!r}".replace("\n", "\n    ")
            repr_literal = nodes.literal_block(rep, rep)
            repr_literal["language"] = "none"
            node.append(repr_literal)
    elif output == "plot":
        if isinstance(chart, alt.TopLevelMixin):
            # Last line should be a chart; convert to spec dict
            try:
                spec = chart.to_dict()
            except SchemaValidationError as err:
                msg = f"Invalid chart: {node['code']}"
                raise ValueError(msg) from err

            # Pass relevant info into the template and append to the output
            html = VGL_TEMPLATE.render(
                div_id=node["div_id"],
                div_class=node["div_class"],
                spec=json.dumps(spec),
                mode="vega-lite",
                renderer="canvas",
                actions=json.dumps(node["links"]),
            )
            self.body.append(html)
        else:
            msg = (
                f"altair-plot: {node['rst_source']}:{node['rst_lineno']} Malformed block. "
                "Last line of code block should define a valid altair Chart object."
            )
            warnings.warn(msg, stacklevel=1)
        raise nodes.SkipNode


def generic_visit_altair_plot(self: altair_plot, node: nodes.Element) -> None:
    self.body.append(
        _("[ graph: %s ]") % node["alt"] if "alt" in node.attributes else _("[ graph ]")
    )
    raise nodes.SkipNode


def depart_altair_plot(self: altair_plot, node: nodes.Element) -> None: ...


def builder_inited(app: Sphinx) -> None:
    app.add_js_file(app.config.altairplot_vega_js_url)
    app.add_js_file(app.config.altairplot_vegalite_js_url)
    app.add_js_file(app.config.altairplot_vegaembed_js_url)


def setup(app: Sphinx) -> dict[str, str]:
    app.add_config_value("altairplot_links", DEFAULT_ALTAIRPLOT_LINKS, "env")
    app.add_config_value("altairplot_vega_js_url", VEGA_JS_URL_DEFAULT, "html")
    app.add_config_value("altairplot_vegalite_js_url", VEGALITE_JS_URL_DEFAULT, "html")
    app.add_config_value(
        "altairplot_vegaembed_js_url", VEGAEMBED_JS_URL_DEFAULT, "html"
    )
    app.add_directive("altair-plot", AltairPlotDirective)
    app.add_css_file("altair-plot.css")
    app.add_node(
        altair_plot,
        html=(html_visit_altair_plot, depart_altair_plot),
        latex=(generic_visit_altair_plot, depart_altair_plot),
        texinfo=(generic_visit_altair_plot, depart_altair_plot),
        text=(generic_visit_altair_plot, depart_altair_plot),
        man=(generic_visit_altair_plot, depart_altair_plot),
    )
    app.connect("env-purge-doc", purge_altair_namespaces)
    app.connect("builder-inited", builder_inited)
    return {"version": "0.1"}
