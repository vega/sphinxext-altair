Test documentation
==================

Preparation for the plot which should not show any output:

.. altair-plot::
    :output: none

    import altair as alt

    data = alt.Data(
        values=[
            {"x": "A", "y": 5},
            {"x": "B", "y": 3},
            {"x": "C", "y": 6},
            {"x": "D", "y": 7},
            {"x": "E", "y": 2},
        ]
    )


The above code could have also been directly included in the following directive which shows the plot:

.. altair-plot::

    alt.Chart(data).mark_bar().encode(
        x="x:N",
        y="y:Q",
    )

Code below plot
---------------

.. altair-plot::
    :code-below:

    alt.Chart(data).mark_bar().encode(
        x="x:N",
        y="y:Q",
    )

Repr output
-----------
The variable ``data`` is shown as repr output.

.. altair-plot::
    :output: repr

    data


Remove code
-----------
No code should be shown, only the plot.

.. altair-plot::
    :remove-code:

    alt.Chart(data).mark_bar().encode(
        x="x:N",
        y="y:Q",
    )


Hide code
---------
The code should be hidden and can be expanded.

.. altair-plot::
    :hide-code:

    alt.Chart(data).mark_bar().encode(
        x="x:N",
        y="y:Q",
    )

Links
-----
The context menu in the top-right corner of this chart should only show the "Open in Vega Editor" and "View Compiled Vega" links.

.. altair-plot::
    :links: editor

    alt.Chart(data).mark_bar().encode(
        x="x:N",
        y="y:Q",
    )


Specify div class name
----------------------
This cannot be tested visually but is tested in the testing script.

.. altair-plot::
    :div_class: test-class

    alt.Chart(data).mark_bar().encode(
        x="x:N",
        y="y:Q",
    )


