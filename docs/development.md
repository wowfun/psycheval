# Development

Install the frozen Python and Node environments from the repository root:

```console
uv sync --frozen
npm ci
```

The browser test toolchain supports Node.js `^22.22.2`, `^24.15.0`, or `>=26.0.0`.

Python runtime code lives under `src/psycheval`; all Python behavior tests live
under `tests` and use normal package imports. Browser modules live under
`src/psycheval/assets/web`, ship as authored ESM, and are exercised by the Node
tests under `web` without an application bundle. The exception is the immutable
`pretty-aui` standalone distribution under `assets/web/vendor`; do not edit
generated assets directly. To update it, build the owning pretty-aui checkout
and run `npm run vendor:pretty-aui -- /path/to/pretty-aui/dist/standalone`.
Append `--check` to compare that build with the checked-in distribution without
copying. Review the generated diff and run `npm run check` against the vendored
assets. Normal installation and validation use those checked-in assets and do
not require the upstream checkout or a second package archive. Its `LICENSE`
and `THIRD_PARTY_LICENSES.txt` files must remain present.

Keep Harbor-specific adapters at the pinned public `0.24.0` seams under
`psycheval.harbor`; package-wide CLI, trajectory, report, and workspace code
lives directly under `psycheval`. Update the owning reference and closest
deterministic test when a stable interface changes.

The repository-owned `skills/peval` Skill uses progressive references and
assets and is not Python package data. `peval init --skill <skill-dir>` validates
one explicitly selected local Skill and atomically replaces its workspace copy;
plain `peval init` installs nothing. Validate the repository source with the
Skill checker. Follow
[Documentation Ownership](AGENTS.md) for docs changes.

Build artifacts belong in `.local/` and are not authority. Never develop against
real profile databases, credentials, provider configuration, or user
workspaces.

## Source and distribution installation

For source development, expose the editable checkout with
`uv tool install -e . --force`. Consumers install the versioned package using
the [README workflow](../README.md#install). Keep the full dependency constraints
until a broader supported range has been tested; optional Agent executables,
WorkBuddy runtime and repository Skill remain explicit installations.

Build and inspect a candidate in a separate build environment:

```console
UV_PROJECT_ENVIRONMENT=.local/build-env uv sync --frozen --only-group build
UV_PROJECT_ENVIRONMENT=.local/build-env uv build --no-build-isolation --out-dir .local/dist
UV_PROJECT_ENVIRONMENT=.local/build-env uv run --no-sync twine check --strict .local/dist/*
UV_PROJECT_ENVIRONMENT=.local/build-env uv run --no-sync python scripts/check_distribution.py .local/dist
```

On PowerShell set `$env:UV_PROJECT_ENVIRONMENT = '.local/build-env'` before these
commands instead of using the inline environment assignment. The sdist contains
only runtime source, build metadata (including Hatch's `.gitignore` input), README
and required licenses. The wheel is
built from that sdist. Generated metadata is the only payload beyond tracked
source and license copies; the artifact checker compares filenames and bytes.
The project's own code remains MIT. The distribution includes Apache-2.0 and
BSD-3-Clause components; DOMPurify is distributed under its Apache-2.0 option.
Keep all bundled license notices intact.

PR installation checks export frozen runtime constraints using
`uv export --frozen --no-dev --no-hashes --no-emit-project`, then pass that file to
`scripts/validate_install.py --constraints`. Constraints must not be installed as
requirements. Release acceptance omits constraints and installs into an empty
environment. Neither gate relies on the source checkout to import the package.
CI builds one pure-Python candidate and distributes it to every consumer cell.
The build job also prepares the ECharts smoke fixture from the package-lock
archive, verifying its integrity before extracting the single required asset.
Consumers pass that fixture with `--echarts`; they do not install Node dependencies.

## Publishing a release

The version belongs to `psycheval.harbor.__version__`; update it before creating
the release tag. Build and checking tools are pinned in the build dependency
group and lockfile. README repository links are converted to the same version's
tag only in built metadata; source links remain subject to the docs checker.

Configure verified PyPI and TestPyPI accounts with two-factor authentication.
On each index add a pending Trusted Publisher for project `psycheval`, repository
`wowfun/psycheval`, workflow `publish.yml`, and respectively environment
`pypi` or `testpypi`. Pending publishers do not reserve a project name.
Restrict both GitHub environments to `v*` tags; require maintainer confirmation
for `pypi`. Use separate tag rules to restrict creation to release maintainers
and prevent updates/deletion without granting those operations through a
creation bypass. Configure these controls before pushing the first tag.

Merge the preparation into `main`, wait for its push CI, then push the matching
`v<version>` tag. The publish workflow checks main ancestry and successful
push/main CI for that exact commit. It builds once, saves a 90-day artifact and
SHA-256 receipt, validates Linux/Windows Python 3.12–3.14 consumers, and uploads
to TestPyPI. It downloads those files, verifies their receipt hashes, and tests
the downloaded wheel in an empty environment with dependencies from PyPI.
Review the rendered TestPyPI description before approving the PyPI
environment. The exact same files then reach PyPI, followed by an index install
and GitHub release. Candidate versions produce GitHub prereleases.
The GitHub release deliberately publishes `receipt.json` alongside the wheel and
sdist so consumers can inspect their commit, tag and SHA-256 provenance.

Rerun failed jobs to reuse the original artifact; a full rerun also recovers
that workflow run's artifact instead of rebuilding it. Existing index files are
skipped only when their SHA-256 matches the receipt. Missing files are uploaded;
unexpected files or different bytes fail the release. An expired/missing artifact
after upload requires a new version. Index visibility checks and refreshed
installs have bounded retries. Upload jobs run no project code and only they
receive OIDC upload permission; GitHub release permission is separate.

If a published candidate is defective, publish an advisory and a new candidate
version. Yanking is optional and does not protect consumers with an exact pin.
