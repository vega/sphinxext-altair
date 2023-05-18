# How to cut a new release
1. Make certain your branch is in sync with head:

        git pull upstream main

2. Update version to, e.g. 0.2.0 in `sphinxext_altair/__init__.py`

3. Commit change and push to upstream main:

        git add . -u
        git commit -m "MAINT: bump version to 0.2.0"
        git push upstream main

4. Run test suite again after commit above to make sure everything passes:

        hatch run test

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

11. Double-check that a conda-forge pull request is generated from the updated
    pip package by the conda-forge bot (may take up to ~an hour):
    https://github.com/conda-forge/sphinxext-altair-feedstock/pulls
