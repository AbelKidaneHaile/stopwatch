# stopwatch

![PyPI version](https://img.shields.io/pypi/v/stopwatch.svg)

Python package for time related tasks.

* [GitHub](https://github.com/AbelKidaneHaile/stopwatch/) | [PyPI](https://pypi.org/project/stopwatch/) | [Documentation](https://AbelKidaneHaile.github.io/stopwatch/)
* Created by [Abel Kidane Haile](https://abelkidanehaile.github.io/) | GitHub [@AbelKidaneHaile](https://github.com/AbelKidaneHaile) | PyPI [@AbelKidaneHaile](https://pypi.org/user/AbelKidaneHaile/)
* MIT License

## Features

* TODO

## Documentation

Documentation is built with [Zensical](https://zensical.org/) and deployed to GitHub Pages.

* **Live site:** https://AbelKidaneHaile.github.io/stopwatch/
* **Preview locally:** `just docs-serve` (serves at http://localhost:8000)
* **Build:** `just docs-build`

API documentation is auto-generated from docstrings using [mkdocstrings](https://mkdocstrings.github.io/).

Docs deploy automatically on push to `main` via GitHub Actions. To enable this, go to your repo's Settings > Pages and set the source to **GitHub Actions**.

## Development

To set up for local development:

```bash
# Clone your fork
git clone git@github.com:your_username/stopwatch.git
cd stopwatch

# Install in editable mode with live updates
uv tool install --editable .
```

This installs the CLI globally but with live updates - any changes you make to the source code are immediately available when you run `stopwatch`.

Run tests:

```bash
uv run pytest
```

Run quality checks (format, lint, type check, test):

```bash
just qa
```

## Author

stopwatch was created in 2026 by Abel Kidane Haile.

Built with [Cookiecutter](https://github.com/cookiecutter/cookiecutter) and the [audreyfeldroy/cookiecutter-pypackage](https://github.com/audreyfeldroy/cookiecutter-pypackage) project template.
