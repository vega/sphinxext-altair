"""
Altair Plot Sphinx Extension
============================

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
    altairplot_links = {'editor': True, 'source': True, 'export': True}
    # ...

If this configuration is not specified, all are set to True.
"""

import contextlib
import io
import json
import os
import sys
import warnings
from typing import Any, Callable, Dict, List, Optional, Union

import altair as alt
import jinja2
import sphinx.application
import sphinx.environment
from altair.utils.execeval import eval_block
from docutils import nodes
from docutils.parsers.rst import Directive
from docutils.parsers.rst.directives import flag, unchanged
from sphinx.locale import _

if sys.version_info >= (3, 8):
    from typing import Literal
else:
    from typing_extensions import Literal

# These default URLs can be changed in conf.py; see setup() below.
VEGA_JS_URL_DEFAULT = "https://cdn.jsdelivr.net/npm/vega@{}".format(alt.VEGA_VERSION)
VEGALITE_JS_URL_DEFAULT = "https://cdn.jsdelivr.net/npm/vega-lite@{}".format(
    alt.VEGALITE_VERSION
)
VEGAEMBED_JS_URL_DEFAULT = "https://cdn.jsdelivr.net/npm/vega-embed@{}".format(
    alt.VEGAEMBED_VERSION
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
    pass


def purge_altair_namespaces(
    app: sphinx.application.Sphinx,
    env: sphinx.environment.BuildEnvironment,
    docname: str,
) -> None:
    if not hasattr(env, "_altair_namespaces"):
        return
    env._altair_namespaces.pop(docname, {})


DEFAULT_ALTAIRPLOT_LINKS = {"editor": True, "source": True, "export": True}


def validate_links(links: str) -> Union[Dict[str, bool], Literal[False]]:
    if links.strip().lower() == "none":
        return False

    links_split = links.strip().split()
    diff = set(links_split) - set(DEFAULT_ALTAIRPLOT_LINKS.keys())
    if diff:
        raise ValueError("Following links are invalid: {}".format(list(diff)))
    return {link: link in links_split for link in DEFAULT_ALTAIRPLOT_LINKS}


def validate_output(output: str) -> str:
    output = output.strip().lower()
    if output not in ["plot", "repr", "stdout", "none"]:
        raise ValueError(":output: flag must be one of [plot|repr|stdout|none]")
    return output


def validate_div_class(output: str) -> str:
    return output.strip().lower()


class AltairPlotDirective(Directive):
    has_content = True

    option_spec: Dict[str, Union[flag, unchanged, Callable[[str], Any]]] = {
        "hide-code": flag,
        "remove-code": flag,
        "code-below": flag,
        "namespace": unchanged,
        "output": validate_output,
        "alt": unchanged,
        "links": validate_links,
        "chart-var-name": unchanged,
        "strict": flag,
        "div_class": validate_div_class,
    }

    def run(self) -> List[nodes.Element]:
        env: sphinx.environment.BuildEnvironment = self.state.document.settings.env
        app = env.app

        hide_code = "hide-code" in self.options
        remove_code = "remove-code" in self.options
        code_below = "code-below" in self.options
        strict = "strict" in self.options
        div_class: Optional[str] = self.options.get("div_class", None)

        if not hasattr(env, "_altair_namespaces"):
            env._altair_namespaces = {}  # type: ignore[attr-defined]
        namespace_id = self.options.get("namespace", "default")
        namespace = env._altair_namespaces.setdefault(  # type: ignore[attr-defined]
            env.docname, {}
        ).setdefault(namespace_id, {})

        code = "\n".join(self.content)

        # Show code
        source_literal = nodes.literal_block(code, code)
        source_literal["language"] = "python"

        # get the name of the source file we are currently processing
        rst_source = self.state_machine.document["source"]
        rst_dir = os.path.dirname(rst_source)
        rst_filename = os.path.basename(rst_source)

        # use the source file name to construct a friendly target_id
        serialno = env.new_serialno("altair-plot")
        rst_base = rst_filename.replace(".", "-")
        div_id = "{}-altair-plot-{}".format(rst_base, serialno)
        target_id = "{}-altair-source-{}".format(rst_base, serialno)
        target_node = nodes.target("", "", ids=[target_id])

        # create the node in which the plot will appear;
        # this will be processed by html_visit_altair_plot
        plot_node = altair_plot()
        plot_node["target_id"] = target_id
        plot_node["div_id"] = div_id
        plot_node["div_class"] = div_class
        plot_node["code"] = code
        plot_node["namespace"] = namespace
        plot_node["relpath"] = os.path.relpath(rst_dir, env.srcdir)
        plot_node["rst_source"] = rst_source
        plot_node["rst_lineno"] = self.lineno
        plot_node["links"] = self.options.get(
            "links", app.builder.config.altairplot_links
        )
        plot_node["output"] = self.options.get("output", "plot")
        plot_node["chart-var-name"] = self.options.get("chart-var-name", None)
        plot_node["strict"] = strict

        if "alt" in self.options:
            plot_node["alt"] = self.options["alt"]

        result = [target_node]

        if code_below:
            result += [plot_node]

        if hide_code:
            html = "<details><summary><a>Click to show code</a></summary>"
            raw_html = nodes.raw("", html, format="html")
            result += [raw_html]

        if not remove_code:
            result += [source_literal]

        if hide_code:
            html = "</details>"
            raw_html = nodes.raw("", html, format="html")
            result += [raw_html]

        if not code_below:
            result += [plot_node]

        return result


def html_visit_altair_plot(self, node: nodes.Element) -> None:
    # Execute the code, saving output and namespace
    namespace = node["namespace"]
    try:
        f = io.StringIO()
        with contextlib.redirect_stdout(f):
            chart = eval_block(node["code"], namespace)
        stdout = f.getvalue()
    except Exception as err:
        message = "altair-plot: {}:{} Code Execution failed:" "{}: {}".format(
            node["rst_source"], node["rst_lineno"], err.__class__.__name__, str(err)
        )
        if node["strict"]:
            raise ValueError(message) from err
        else:
            warnings.warn(message, stacklevel=1)
            raise nodes.SkipNode from err

    chart_name = node["chart-var-name"]
    if chart_name is not None:
        if chart_name not in namespace:
            raise ValueError(
                "chart-var-name='{}' not present in namespace" "".format(chart_name)
            )
        chart = namespace[chart_name]

    output = node["output"]

    if output == "none":
        raise nodes.SkipNode
    elif output == "stdout":
        if not stdout:
            raise nodes.SkipNode
        else:
            output_literal = nodes.literal_block(stdout, stdout)
            output_literal["language"] = "none"
            node.extend([output_literal])
    elif output == "repr":
        if chart is None:
            raise nodes.SkipNode
        else:
            rep = "    " + repr(chart).replace("\n", "\n    ")
            repr_literal = nodes.literal_block(rep, rep)
            repr_literal["language"] = "none"
            node.extend([repr_literal])
    elif output == "plot":
        if isinstance(chart, alt.TopLevelMixin):
            # Last line should be a chart; convert to spec dict
            try:
                spec = chart.to_dict()
            except alt.utils.schemapi.SchemaValidationError as err:
                raise ValueError("Invalid chart: {0}".format(node["code"])) from err
            actions = node["links"]

            # Pass relevant info into the template and append to the output
            html = VGL_TEMPLATE.render(
                div_id=node["div_id"],
                div_class=node["div_class"],
                spec=json.dumps(spec),
                mode="vega-lite",
                renderer="canvas",
                actions=json.dumps(actions),
            )
            self.body.append(html)
        else:
            warnings.warn(
                "altair-plot: {}:{} Malformed block. Last line of "
                "code block should define a valid altair Chart object."
                "".format(node["rst_source"], node["rst_lineno"]),
                stacklevel=1,
            )
        raise nodes.SkipNode


def generic_visit_altair_plot(self, node: nodes.Element) -> None:
    if "alt" in node.attributes:
        self.body.append(_("[ graph: %s ]") % node["alt"])
    else:
        self.body.append(_("[ graph ]"))
    raise nodes.SkipNode


def depart_altair_plot(self, node: nodes.Element) -> None:
    return


def builder_inited(app: sphinx.application.Sphinx) -> None:
    app.add_js_file(app.config.altairplot_vega_js_url)
    app.add_js_file(app.config.altairplot_vegalite_js_url)
    app.add_js_file(app.config.altairplot_vegaembed_js_url)


def setup(app: sphinx.application.Sphinx) -> Dict[str, str]:
    setup.app = app  # type: ignore[attr-defined]
    setup.config = app.config  # type: ignore[attr-defined]
    setup.confdir = app.confdir  # type: ignore[attr-defined]

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
