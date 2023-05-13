# How to cut a new release
1. Create a new virtual environment following the instructions in `README.md`.

2. Make certain your branch is in sync with head:

        git pull upstream main

3. Update version to, e.g. 0.2.0 in `sphinxext_altair/__init__.py`

4. Commit change and push to upstream main:

        git add . -u
        git commit -m "MAINT: bump version to 0.2.0"
        git push upstream main

5. Tag the release:

        git tag -a v0.2.0 -m "Version 0.2.0 release"
        git push upstream v0.2.0

6. Build source & wheel distributions:

        hatch clean  # clean old builds & distributions
        hatch build  # create a source distribution and universal wheel

7. publish to PyPI (Requires correct PyPI owner permissions):

        hatch publish

8. update version to e.g. 0.3.0dev in `sphinxext_altair/__init__.py`

9. Commit change and push to upstream main:

        git add . -u
        git commit -m "MAINT: bump version to 0.3.0dev"
        git push upstream main

10. Add release in https://github.com/altair-viz/sphinxext-altair/releases/ and use version tag
