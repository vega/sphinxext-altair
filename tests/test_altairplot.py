# Tests are inspired by the test suite of sphinx itself
import pytest

from sphinxext_altair.altairplot import (
    VEGA_JS_URL_DEFAULT,
    VEGAEMBED_JS_URL_DEFAULT,
    VEGALITE_JS_URL_DEFAULT,
    purge_altair_namespaces,
    validate_links,
)


@pytest.mark.parametrize("add_namespaces_attr", [True, False])
@pytest.mark.sphinx(testroot="altairplot")
def test_purge_altair_namespaces(add_namespaces_attr, app):
    env = app.env
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
def test_validate_links(links, expected):
    if expected == "raise":
        with pytest.raises(
            ValueError, match=r"Following links are invalid: \['unknown'\]"
        ):
            output = validate_links(links)
    else:
        output = validate_links(links)
        assert output == expected


@pytest.mark.sphinx(testroot="altairplot", freshenv=True)
def test_altairplotdirective(app):
    app.builder.build_all()
    result = (app.outdir / "index.html").read_text(encoding="utf8")
    assert result.count("https://cdn.jsdelivr.net/npm/vega@") == 1
    assert result.count("https://cdn.jsdelivr.net/npm/vega-lite@") == 1
    assert result.count("https://cdn.jsdelivr.net/npm/vega-embed@") == 1
    assert result.count(VEGAEMBED_JS_URL_DEFAULT)
    assert result.count(VEGALITE_JS_URL_DEFAULT)
    assert result.count(VEGA_JS_URL_DEFAULT)

    assert result.count('class="test-class"') == 1
    block_no_output = """\
<div class="highlight-python notranslate" id="index-rst-altair-source-0"><div class="highlight"><pre><span></span><span class="kn">import</span> <span class="nn">altair</span> <span class="k">as</span> <span class="nn">alt</span>

<span class="n">data</span> <span class="o">=</span> <span class="n">alt</span><span class="o">.</span><span class="n">Data</span><span class="p">(</span>
    <span class="n">values</span><span class="o">=</span><span class="p">[</span>
        <span class="p">{</span><span class="s2">&quot;x&quot;</span><span class="p">:</span> <span class="s2">&quot;A&quot;</span><span class="p">,</span> <span class="s2">&quot;y&quot;</span><span class="p">:</span> <span class="mi">5</span><span class="p">},</span>
        <span class="p">{</span><span class="s2">&quot;x&quot;</span><span class="p">:</span> <span class="s2">&quot;B&quot;</span><span class="p">,</span> <span class="s2">&quot;y&quot;</span><span class="p">:</span> <span class="mi">3</span><span class="p">},</span>
        <span class="p">{</span><span class="s2">&quot;x&quot;</span><span class="p">:</span> <span class="s2">&quot;C&quot;</span><span class="p">,</span> <span class="s2">&quot;y&quot;</span><span class="p">:</span> <span class="mi">6</span><span class="p">},</span>
        <span class="p">{</span><span class="s2">&quot;x&quot;</span><span class="p">:</span> <span class="s2">&quot;D&quot;</span><span class="p">,</span> <span class="s2">&quot;y&quot;</span><span class="p">:</span> <span class="mi">7</span><span class="p">},</span>
        <span class="p">{</span><span class="s2">&quot;x&quot;</span><span class="p">:</span> <span class="s2">&quot;E&quot;</span><span class="p">,</span> <span class="s2">&quot;y&quot;</span><span class="p">:</span> <span class="mi">2</span><span class="p">},</span>
    <span class="p">]</span>
<span class="p">)</span>
</pre></div>
</div>"""
    assert block_no_output in result

    block_plot_1 = """\
<div class="highlight-python notranslate" id="index-rst-altair-source-1"><div class="highlight"><pre><span></span><span class="n">alt</span><span class="o">.</span><span class="n">Chart</span><span class="p">(</span><span class="n">data</span><span class="p">)</span><span class="o">.</span><span class="n">mark_bar</span><span class="p">()</span><span class="o">.</span><span class="n">encode</span><span class="p">(</span>
    <span class="n">x</span><span class="o">=</span><span class="s2">&quot;x:N&quot;</span><span class="p">,</span>
    <span class="n">y</span><span class="o">=</span><span class="s2">&quot;y:Q&quot;</span><span class="p">,</span>
<span class="p">)</span>
</pre></div>
</div>

<div id="index-rst-altair-plot-1">
<script>
  // embed when document is loaded, to ensure vega library is available
  // this works on all modern browsers, except IE8 and older
  document.addEventListener("DOMContentLoaded", function(event) {
      var spec = {"config": {"view": {"continuousWidth": 300, "continuousHeight": 300}}, "data": {"values": [{"x": "A", "y": 5}, {"x": "B", "y": 3}, {"x": "C", "y": 6}, {"x": "D", "y": 7}, {"x": "E", "y": 2}]}, "mark": {"type": "bar"}, "encoding": {"x": {"field": "x", "type": "nominal"}, "y": {"field": "y", "type": "quantitative"}}, "$schema": "https://vega.github.io/schema/vega-lite/v5.8.0.json"};
      var opt = {
        "mode": "vega-lite",
        "renderer": "canvas",
        "actions": {"editor": true, "source": true, "export": true}
      };
      vegaEmbed('#index-rst-altair-plot-1', spec, opt).catch(console.err);
  });
</script>
</div>"""
    assert block_plot_1 in result

    block_plot_2 = """\
<div id="index-rst-altair-plot-2">
<script>
  // embed when document is loaded, to ensure vega library is available
  // this works on all modern browsers, except IE8 and older
  document.addEventListener("DOMContentLoaded", function(event) {
      var spec = {"config": {"view": {"continuousWidth": 300, "continuousHeight": 300}}, "data": {"values": [{"x": "A", "y": 5}, {"x": "B", "y": 3}, {"x": "C", "y": 6}, {"x": "D", "y": 7}, {"x": "E", "y": 2}]}, "mark": {"type": "bar"}, "encoding": {"x": {"field": "x", "type": "nominal"}, "y": {"field": "y", "type": "quantitative"}}, "$schema": "https://vega.github.io/schema/vega-lite/v5.8.0.json"};
      var opt = {
        "mode": "vega-lite",
        "renderer": "canvas",
        "actions": {"editor": true, "source": true, "export": true}
      };
      vegaEmbed('#index-rst-altair-plot-2', spec, opt).catch(console.err);
  });
</script>
</div><div class="highlight-python notranslate"><div class="highlight"><pre><span></span><span class="n">alt</span><span class="o">.</span><span class="n">Chart</span><span class="p">(</span><span class="n">data</span><span class="p">)</span><span class="o">.</span><span class="n">mark_bar</span><span class="p">()</span><span class="o">.</span><span class="n">encode</span><span class="p">(</span>
    <span class="n">x</span><span class="o">=</span><span class="s2">&quot;x:N&quot;</span><span class="p">,</span>
    <span class="n">y</span><span class="o">=</span><span class="s2">&quot;y:Q&quot;</span><span class="p">,</span>
<span class="p">)</span>
</pre></div>
</div>"""
    assert block_plot_2 in result

    block_3 = """\
<div class="highlight-python notranslate" id="index-rst-altair-source-3"><div class="highlight"><pre><span></span><span class="n">data</span>
</pre></div>
</div>
<div class="highlight-none notranslate"><div class="highlight"><pre><span></span>    Data({
      values: [{&#39;x&#39;: &#39;A&#39;, &#39;y&#39;: 5}, {&#39;x&#39;: &#39;B&#39;, &#39;y&#39;: 3}, {&#39;x&#39;: &#39;C&#39;, &#39;y&#39;: 6}, {&#39;x&#39;: &#39;D&#39;, &#39;y&#39;: 7}, {&#39;x&#39;: &#39;E&#39;, &#39;y&#39;: 2}]
    })
</pre></div>
</div>"""
    assert block_3 in result

    block_plot_4 = """\
<p>No code should be shown, only the plot.</p>

<div id="index-rst-altair-plot-4">
<script>
  // embed when document is loaded, to ensure vega library is available
  // this works on all modern browsers, except IE8 and older
  document.addEventListener("DOMContentLoaded", function(event) {
      var spec = {"config": {"view": {"continuousWidth": 300, "continuousHeight": 300}}, "data": {"values": [{"x": "A", "y": 5}, {"x": "B", "y": 3}, {"x": "C", "y": 6}, {"x": "D", "y": 7}, {"x": "E", "y": 2}]}, "mark": {"type": "bar"}, "encoding": {"x": {"field": "x", "type": "nominal"}, "y": {"field": "y", "type": "quantitative"}}, "$schema": "https://vega.github.io/schema/vega-lite/v5.8.0.json"};
      var opt = {
        "mode": "vega-lite",
        "renderer": "canvas",
        "actions": {"editor": true, "source": true, "export": true}
      };
      vegaEmbed('#index-rst-altair-plot-4', spec, opt).catch(console.err);
  });
</script>
</div>"""
    assert block_plot_4 in result

    block_plot_5 = """\
<p>The code should be hidden and can be expanded.</p>
<details><summary><a>Click to show code</a></summary><div class="highlight-python notranslate"><div class="highlight"><pre><span></span><span class="n">alt</span><span class="o">.</span><span class="n">Chart</span><span class="p">(</span><span class="n">data</span><span class="p">)</span><span class="o">.</span><span class="n">mark_bar</span><span class="p">()</span><span class="o">.</span><span class="n">encode</span><span class="p">(</span>
    <span class="n">x</span><span class="o">=</span><span class="s2">&quot;x:N&quot;</span><span class="p">,</span>
    <span class="n">y</span><span class="o">=</span><span class="s2">&quot;y:Q&quot;</span><span class="p">,</span>
<span class="p">)</span>
</pre></div>
</div>
</details>
<div id="index-rst-altair-plot-5">
<script>
  // embed when document is loaded, to ensure vega library is available
  // this works on all modern browsers, except IE8 and older
  document.addEventListener("DOMContentLoaded", function(event) {
      var spec = {"config": {"view": {"continuousWidth": 300, "continuousHeight": 300}}, "data": {"values": [{"x": "A", "y": 5}, {"x": "B", "y": 3}, {"x": "C", "y": 6}, {"x": "D", "y": 7}, {"x": "E", "y": 2}]}, "mark": {"type": "bar"}, "encoding": {"x": {"field": "x", "type": "nominal"}, "y": {"field": "y", "type": "quantitative"}}, "$schema": "https://vega.github.io/schema/vega-lite/v5.8.0.json"};
      var opt = {
        "mode": "vega-lite",
        "renderer": "canvas",
        "actions": {"editor": true, "source": true, "export": true}
      };
      vegaEmbed('#index-rst-altair-plot-5', spec, opt).catch(console.err);
  });
</script>
</div>"""
    assert block_plot_5 in result

    block_plot_6 = """\
<div class="highlight-python notranslate" id="index-rst-altair-source-6"><div class="highlight"><pre><span></span><span class="n">alt</span><span class="o">.</span><span class="n">Chart</span><span class="p">(</span><span class="n">data</span><span class="p">)</span><span class="o">.</span><span class="n">mark_bar</span><span class="p">()</span><span class="o">.</span><span class="n">encode</span><span class="p">(</span>
    <span class="n">x</span><span class="o">=</span><span class="s2">&quot;x:N&quot;</span><span class="p">,</span>
    <span class="n">y</span><span class="o">=</span><span class="s2">&quot;y:Q&quot;</span><span class="p">,</span>
<span class="p">)</span>
</pre></div>
</div>

<div id="index-rst-altair-plot-6">
<script>
  // embed when document is loaded, to ensure vega library is available
  // this works on all modern browsers, except IE8 and older
  document.addEventListener("DOMContentLoaded", function(event) {
      var spec = {"config": {"view": {"continuousWidth": 300, "continuousHeight": 300}}, "data": {"values": [{"x": "A", "y": 5}, {"x": "B", "y": 3}, {"x": "C", "y": 6}, {"x": "D", "y": 7}, {"x": "E", "y": 2}]}, "mark": {"type": "bar"}, "encoding": {"x": {"field": "x", "type": "nominal"}, "y": {"field": "y", "type": "quantitative"}}, "$schema": "https://vega.github.io/schema/vega-lite/v5.8.0.json"};
      var opt = {
        "mode": "vega-lite",
        "renderer": "canvas",
        "actions": {"editor": true, "source": false, "export": false}
      };
      vegaEmbed('#index-rst-altair-plot-6', spec, opt).catch(console.err);
  });
</script>
</div>"""
    assert block_plot_6 in result

    block_plot_7 = """\
<div class="highlight-python notranslate" id="index-rst-altair-source-7"><div class="highlight"><pre><span></span><span class="n">alt</span><span class="o">.</span><span class="n">Chart</span><span class="p">(</span><span class="n">data</span><span class="p">)</span><span class="o">.</span><span class="n">mark_bar</span><span class="p">()</span><span class="o">.</span><span class="n">encode</span><span class="p">(</span>
    <span class="n">x</span><span class="o">=</span><span class="s2">&quot;x:N&quot;</span><span class="p">,</span>
    <span class="n">y</span><span class="o">=</span><span class="s2">&quot;y:Q&quot;</span><span class="p">,</span>
<span class="p">)</span>
</pre></div>
</div>

<div id="index-rst-altair-plot-7" class="test-class">
<script>
  // embed when document is loaded, to ensure vega library is available
  // this works on all modern browsers, except IE8 and older
  document.addEventListener("DOMContentLoaded", function(event) {
      var spec = {"config": {"view": {"continuousWidth": 300, "continuousHeight": 300}}, "data": {"values": [{"x": "A", "y": 5}, {"x": "B", "y": 3}, {"x": "C", "y": 6}, {"x": "D", "y": 7}, {"x": "E", "y": 2}]}, "mark": {"type": "bar"}, "encoding": {"x": {"field": "x", "type": "nominal"}, "y": {"field": "y", "type": "quantitative"}}, "$schema": "https://vega.github.io/schema/vega-lite/v5.8.0.json"};
      var opt = {
        "mode": "vega-lite",
        "renderer": "canvas",
        "actions": {"editor": true, "source": true, "export": true}
      };
      vegaEmbed('#index-rst-altair-plot-7', spec, opt).catch(console.err);
  });
</script>
</div>"""
    assert block_plot_7 in result
