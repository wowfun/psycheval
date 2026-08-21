# Harbor Dataset Management

## Authority

The live workspace may register administrator-managed local Harbor Datasets.
The Dataset registry is the sole authority for Task definition roots used by
linked Harbor mounts and by the browser Task workbench. Harbor Job and Trial
roots remain read-only and are not managed by this interface.

`peval-py.toml` declares Datasets independently from mounts:

```toml
[[harbor.datasets]]
id = "pbench"
path = "../datasets/pbench"

[[harbor.mounts]]
id = "pbench-jobs"
path = "../jobs"
dataset_ids = ["pbench"]
```

Dataset IDs use the same lowercase path-safe syntax as mount IDs. IDs and
canonical paths are unique. Mount references are ordered and must resolve to
declared Datasets. The removed `task_paths` mount field is rejected with a
migration example; it is neither inferred nor read as a compatibility input.

An existing Dataset registration must identify a symlink-free directory. Normal
registration, inventory, and Task/file operations do not parse or validate
`dataset.toml`; its absence or invalidity cannot make the Dataset unbrowseable.
The browser can instead create a new directory and initialize `dataset.toml`
and `README.md` through the Dataset model pinned by `harbor==0.21.0`. Removing
a registration never removes its files and is rejected while a mount references
it.

## Dataset Page

`GET /datasets` is the live Dataset and Task workspace. Its searchable overview
reuses the shared data-table behavior and has one row per live Task plus one
placeholder row for an empty registered Dataset. Dataset, Task directory,
package identity, Task status, and diagnostics are searchable; the first visible
row is selected by default. Search or filtering that removes the selected row
selects the first remaining row, while an empty result clears the detail region.

The selected live Task renders its file tree beside one content pane. Guests
may list every live Task file and read UTF-8 text up to 2 MiB, including
solutions and verifier definitions, but may not download any file. Binary and
larger files remain metadata-only. Guest responses omit Dataset locations,
revisions, trash, mount configuration, and other server internals.
Administrators additionally receive revisions and the contextual Dataset,
Task, manifest, trash, and file mutation controls. Trash is a separate
administrator view rather than part of the live overview. Dataset-root files
remain inventory facts, not general editor targets.

When Task or file selections overlap in flight, only the latest selection may
update the file tree or editor. Switching Task or file, using workspace
navigation, or leaving the page protects unsaved administrator text. On narrow
screens the file tree precedes the content pane instead of sharing a row. All
Dataset-page controls, prompts, confirmations, and status text use the active
workspace locale.

Task creation uses the Task schema `1.4` scaffold supplied by the pinned
`harbor==0.21.0` package, with package version `1.0.0`, an instruction,
environment, pytest verifier, and solution. It defaults to a single step and
may explicitly create multiple steps. Renaming a Task directory does not
rewrite `[task].name`. If the installed Harbor package does not expose its
scaffold resources, creation fails without leaving a partial Task and returns
an actionable diagnostic that does not disclose the package location.

Every Task mutation revalidates the definition with Harbor. Invalid definitions
remain editable drafts and expose diagnostics, but only valid Tasks participate
in linked Trial Task evidence. A successful Task mutation schedules one
coalesced catalog reconciliation so affected live metadata does not remain
stale.

Administrator text is saved only by an explicit Save action. Text reads are
limited to 2 MiB, uploads to 16 MiB, and administrator downloads to 20 MiB.
Larger existing files remain listed without being loaded. Limits are enforced
against the bytes actually read so concurrent growth cannot bypass them.
Binary upload content is base64-encoded inside the existing bounded JSON
request envelope. The browser rejects an oversized upload before reading it
and validates the requested step count before creating a Task; the server
remains authoritative for both.

## Filesystem Safety and Concurrency

Dataset, Task, and file paths are resolved through a single containment seam.
Absolute child paths, empty or dot components, `..`, backslashes, symlinks,
special files, control directories, and canonical escapes are rejected. Reads
and writes never follow a link. Existing files retain their mode; newly created
files use ordinary owner-writable non-executable defaults.

Inventory, Task, and file representations carry content revisions. Mutations
must present the applicable expected revision and fail with HTTP 409 when the
configuration or filesystem changed. Manifest synchronization rechecks the
Dataset revision at its commit boundary after deriving Task references. File
replacements and directory-level creates use temporary siblings and atomic
rename. A Task file or directory delete is permanent and requires browser
confirmation.

Deleting a Task instead moves it atomically into
`<dataset>/.peval-py-trash/<entry-id>/`, alongside metadata containing the
original directory, package name, Dataset ID, and deletion time. Trash is not
auto-expired. Restore uses the original name by default, accepts an explicit
replacement name, and rejects collisions. If restore cannot remove its trash
metadata, it rolls the Task move back instead of exposing both live and trash
representations. Purge permanently removes only the resolved trash entry.

## Dataset Manifest

Ordinary Dataset browsing and mutations never parse, validate, or silently
rewrite `dataset.toml`. An explicit Sync manifest action is the sole operation
that parses and validates it; that action uses Harbor's content digest and
manifest model to add or update valid live Task references and remove references
represented by retained trash entries. A missing or invalid manifest fails that
explicit action without affecting Dataset or Task browseability. Invalid Tasks
remain diagnostic and are not synchronized. Root `README.md`, `metric.py`, and
other Dataset files are never edited by the workbench.

## Related Topics

- [Evaluation Workspace](spec.md)
- [Access Control](access.md)
- [Storage](storage.md)
- [HTTP Interface](http.md)
- [Presentation](presentation.md)
- [Testing](testing.md)
