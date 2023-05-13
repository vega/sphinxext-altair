import pytest

from sphinxext_altair.altairplot import purge_altair_namespaces, validate_links


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
    # TODO: Call run for different inputs and evaluate output
    # See https://github.com/sphinx-doc/sphinx/blob/master/tests/test_ext_viewcode.py
    # for an example of how to do this
    raise NotImplementedError


def test_html_visit_altair_plot():
    raise NotImplementedError


def test_setup():
    raise NotImplementedError
