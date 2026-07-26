# Continuous integration

`github-actions-ci.yml` installs from `requirements-dev.txt`, rebuilds both
vendored datasets, runs the full test suite and executes the model CLI across
Python 3.10 / 3.11 / 3.12.

It is parked here rather than in `.github/workflows/` because the automation
account that created this branch does not hold the GitHub `workflows`
permission, so pushing a live workflow file is refused.

To enable it:

```bash
mkdir -p .github/workflows
git mv ci/github-actions-ci.yml .github/workflows/ci.yml
git commit -m "Enable CI"
git push
```
