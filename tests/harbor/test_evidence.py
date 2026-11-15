import hashlib
import json
from pathlib import Path

import pytest

from psycheval.harbor.evidence import EvidenceWriter, SourceSnapshot


@pytest.mark.parametrize(
    "roots",
    [
        ("work", "state", "work/evidence"),
        ("work/sub", "state", "work"),
        ("work", "work/state", "evidence"),
        ("state/work", "state", "evidence"),
        ("work", "state", "state/evidence"),
        ("work", "evidence/state", "evidence"),
        ("work", "work", "evidence"),
    ],
)
def test_input_evidence_roots_must_be_disjoint_before_copy(
    tmp_path, roots, monkeypatch
):
    from psycheval.harbor import evidence
    from psycheval.harbor.evidence import _capture_input_evidence

    def forbidden_stage(**kwargs):
        pytest.fail("overlapping roots must be rejected before allocating a stage")

    monkeypatch.setattr(evidence.tempfile, "mkdtemp", forbidden_stage)
    workdir, state, destination = (tmp_path / name for name in roots)
    for root in (workdir, state):
        root.mkdir(parents=True, exist_ok=True)
    (state / "keep.txt").write_text("retained")
    with pytest.raises(ValueError, match="overlap"):
        _capture_input_evidence(
            workdir, [], state, destination, check_cancel=lambda: None
        )
    assert (state / "keep.txt").read_text() == "retained"
    assert not list(tmp_path.rglob(".input-evidence-*"))


@pytest.mark.parametrize("tree", ["inputs", "preparation_state"])
def test_missing_initial_evidence_names_the_source_tree(tmp_path, tree):
    from psycheval.harbor.evidence import _capture_input_evidence

    workdir, state, destination = (
        tmp_path / name for name in ("work", "state", "evidence")
    )
    workdir.mkdir()
    if tree == "inputs":
        state.mkdir()
    label = (
        "prepared input.*missing.txt"
        if tree == "inputs"
        else "preparation state.*state"
    )
    with pytest.raises(ValueError, match=label):
        _capture_input_evidence(
            workdir,
            ["missing.txt"] if tree == "inputs" else [],
            state,
            destination,
            check_cancel=lambda: None,
        )
    assert not destination.exists()
    assert not list(tmp_path.glob(".input-evidence-*"))


@pytest.mark.parametrize("tree", ["inputs", "preparation_state"])
def test_input_evidence_rejects_git_metadata_in_both_trees(tmp_path, tree):
    from psycheval.harbor.evidence import _capture_input_evidence

    workdir, state, destination = (
        tmp_path / name for name in ("work", "state", "evidence")
    )
    workdir.mkdir()
    state.mkdir()
    source = workdir if tree == "inputs" else state
    (source / "reference/.git").mkdir(parents=True)
    (source / "reference/.git/config").write_text("keep")
    with pytest.raises(ValueError, match=r"cannot include \.git"):
        _capture_input_evidence(
            workdir,
            ["reference"] if tree == "inputs" else [],
            state,
            destination,
            check_cancel=lambda: None,
        )
    assert (source / "reference/.git/config").read_text() == "keep"
    assert not destination.exists()


@pytest.mark.parametrize("failure", ["short_read", "changed_source"])
def test_snapshot_rejects_incomplete_or_changing_reads(tmp_path, monkeypatch, failure):
    from contextlib import contextmanager
    from types import SimpleNamespace

    source = tmp_path / "input.txt"
    source.write_bytes(b"original")
    original_open = Path.open

    @contextmanager
    def unstable_open(path, *args, **kwargs):
        with original_open(path, *args, **kwargs) as stream:
            if path != source or args != ("rb",):
                yield stream
                return

            def read(limit):
                content = stream.read(limit)
                if failure == "short_read":
                    return content[:-1]
                with original_open(source, "wb") as changed:
                    changed.write(b"longer replacement")
                return content

            yield SimpleNamespace(fileno=stream.fileno, read=read)

    monkeypatch.setattr(Path, "open", unstable_open)
    with pytest.raises(OSError, match="Source changed while reading"):
        SourceSnapshot.read(source)


@pytest.mark.parametrize("rollback_fails", [False, True])
def test_failed_input_publication_preserves_previous_copy(
    tmp_path, monkeypatch, rollback_fails
):
    from psycheval.harbor.evidence import _capture_input_evidence

    workdir, state = tmp_path / "workdir", tmp_path / "state"
    workdir.mkdir()
    state.mkdir()
    source = workdir / "input.txt"
    source.write_bytes(b"original")
    destination = tmp_path / "trial/input_evidence"

    def capture():
        _capture_input_evidence(
            workdir, ["input.txt"], state, destination, check_cancel=lambda: None
        )

    capture()
    manifest = (destination / "manifest.json").read_bytes()
    source.write_bytes(b"replacement")
    rename = Path.rename

    def fail_publication(path, target):
        if path.name.startswith(".input-evidence-"):
            if path.name.endswith("-previous"):
                if rollback_fails:
                    raise PermissionError("rollback blocked")
            else:
                raise PermissionError("publication blocked")
        return rename(path, target)

    monkeypatch.setattr(Path, "rename", fail_publication)
    with pytest.raises(PermissionError, match="publication blocked") as failure:
        capture()
    remaining = list(destination.parent.glob(".input-evidence-*"))
    if rollback_fails:
        assert len(remaining) == 1 and remaining[0].name.endswith("-previous")
        retained = remaining[0]
        assert str(retained) in failure.value.__notes__[0]
        assert "rollback blocked" in failure.value.__notes__[0]
        assert not destination.exists()
    else:
        assert remaining == []
        retained = destination
    assert (retained / "manifest.json").read_bytes() == manifest
    assert (retained / "inputs/input.txt").read_bytes() == b"original"


def test_mirrored_presentation_produces_raw_and_text_evidence(tmp_path):
    pptx = pytest.importorskip("pptx")
    from psycheval.harbor.documents import inspect_document, select_document

    workdir, artifacts = tmp_path / "workdir", tmp_path / "artifacts"
    workdir.mkdir()
    original = workdir / "agent-intro.pptx"
    deck = pptx.Presentation()
    slide = deck.slides.add_slide(deck.slide_layouts[1])
    slide.shapes.title.text = "Agent introduction"
    slide.placeholders[1].text = "Tools, reasoning, and feedback"
    deck.save(original)
    content = original.read_bytes()
    for path in (
        workdir / "slides/output" / original.name,
        artifacts / original.name,
        artifacts / "slides/output" / original.name,
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    selection = select_document(
        [workdir, artifacts], format="pptx", preferred_stem="agent-intro"
    )
    assert selection.selected is not None and len(selection.candidates) == 4
    logs = tmp_path / "verifier"
    with EvidenceWriter(logs) as writer:
        source = writer.capture("presentation_pptx", selection.selected)
        report = inspect_document(source)
        assert len(report.slides) == 1
        writer.add_text(
            "presentation_text", report.to_markdown(), source_id="presentation_pptx"
        )
    manifest = json.loads((logs / "artifact_manifest.json").read_text())
    raw, text = manifest["artifacts"]
    assert raw["sha256"] == hashlib.sha256(content).hexdigest()
    assert (logs / raw["verifier_raw_path"]).read_bytes() == content
    assert text["extract_status"] == "ok"
    assert text["source_artifact_id"] == raw["id"]
    assert "Agent introduction" in (logs / text["text_path"]).read_text(
        encoding="utf-8"
    )


@pytest.mark.parametrize("snapshot", [False, True])
def test_capture_limits_apply_to_paths_and_snapshots(tmp_path, snapshot):
    source = tmp_path / "source.pdf"
    source.write_bytes(b"12345")
    value = SourceSnapshot.read(source) if snapshot else source
    with EvidenceWriter(tmp_path / "logs") as writer:
        with pytest.raises(ValueError, match="exceed"):
            writer.capture("too_large", value, max_bytes=4)
        writer.capture("fits", value, max_bytes=5)


def test_writer_budgets_and_inactive_exit_are_explicit(tmp_path):
    from psycheval.harbor.evidence import EvidenceLimitError

    writer = EvidenceWriter(
        tmp_path / "logs", max_total_bytes=1024, max_artifacts=1, max_text_bytes=4
    )
    with pytest.raises(RuntimeError):
        writer.__exit__(None, None, None)
    assert not (tmp_path / "logs/artifact_manifest.json").exists()
    with writer:
        with pytest.raises(EvidenceLimitError):
            writer.add_text("text", "中文")
        writer.add_text("text", "fits")
        with pytest.raises(EvidenceLimitError):
            writer.unavailable("another", "missing")
    with (
        pytest.raises(EvidenceLimitError),
        EvidenceWriter(tmp_path / "small", max_total_bytes=5) as writer,
    ):
        writer.capture("raw", SourceSnapshot(Path("a.pdf"), b"12345"))
        with pytest.raises(EvidenceLimitError):
            writer.add_text("text", "x")
        # The manifest is also included in the aggregate budget.
    assert not (tmp_path / "small/artifact_manifest.json").exists()


def test_snapshot_retention_manifest_last_and_stale_cleanup(tmp_path):
    source = tmp_path / "source.pptx"
    source.write_bytes(b"original, even if corrupt")
    logs = tmp_path / "logs"
    logs.mkdir()
    (logs / "other.log").write_text("preserve")
    with EvidenceWriter(logs) as writer:
        snapshot = writer.capture("raw", source)
        source.write_bytes(b"changed")
        writer.add_text("text", "中文\n<&>", source_id="raw")
        assert not (logs / "artifact_manifest.json").exists()
    manifest = json.loads((logs / "artifact_manifest.json").read_text())
    raw, text = manifest["artifacts"]
    assert raw["type"] == "raw_pptx" and text["type"] == "md"
    assert text["extract_status"] == "ok" and text["source_artifact_id"] == "raw"
    assert "raw_path" not in raw
    assert (logs / raw["verifier_raw_path"]).read_bytes() == snapshot.content
    assert raw["sha256"] == hashlib.sha256(snapshot.content).hexdigest()
    with EvidenceWriter(logs) as writer:
        writer.unavailable("text", "no output")
    assert not (logs / raw["verifier_raw_path"]).exists()
    assert not (logs / text["text_path"]).exists()
    assert (logs / "other.log").read_text() == "preserve"


def test_failed_attempt_keeps_raw_without_a_manifest(tmp_path):
    with pytest.raises(RuntimeError), EvidenceWriter(tmp_path) as writer:
        writer.capture("raw", SourceSnapshot(Path("file.docx"), b"corrupt"))
        raise RuntimeError("parse failed")
    assert (tmp_path / "raw_artifacts/raw.docx").read_bytes() == b"corrupt"
    assert not (tmp_path / "artifact_manifest.json").exists()


@pytest.mark.parametrize(
    "path",
    [
        "../escape.md",
        "artifact_text/../escape.md",
        "C:/escape.md",
        "artifact_text/file.txt",
        "artifact_text/nested/../../escape.md",
    ],
)
def test_evidence_rejects_escaping_paths(tmp_path, path):
    with EvidenceWriter(tmp_path) as writer, pytest.raises(ValueError):
        writer.add_text("text", "body", path=path)


def test_duplicate_paths_and_ids_and_empty_text(tmp_path):
    with EvidenceWriter(tmp_path) as writer:
        writer.add_text("empty", "")
        with pytest.raises(ValueError, match="Duplicate artifact"):
            writer.add_text("empty", "replacement")
        with pytest.raises(ValueError, match="Duplicate evidence"):
            writer.add_text("different", "replacement", path="artifact_text/empty.md")
    assert (
        json.loads((tmp_path / "artifact_manifest.json").read_text())["artifacts"][0][
            "extract_status"
        ]
        == "missing"
    )


def test_case_colliding_raw_paths_cannot_overwrite_a_snapshot(tmp_path):
    with EvidenceWriter(tmp_path) as writer:
        writer.capture("Raw", SourceSnapshot(Path("one.pptx"), b"one"))
        with pytest.raises(ValueError, match="Duplicate evidence"):
            writer.capture("raw", SourceSnapshot(Path("two.pptx"), b"two"))
    assert (tmp_path / "raw_artifacts/Raw.pptx").read_bytes() == b"one"


def test_linked_source_and_output_do_not_touch_target(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    source = outside / "source.pdf"
    source.write_bytes(b"real")
    link = tmp_path / "link"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("symlink creation unavailable")
    with pytest.raises(ValueError, match="Linked"):
        SourceSnapshot.read(link / source.name)
    with pytest.raises(ValueError, match="Linked"), EvidenceWriter(link):
        pass
    logs = tmp_path / "logs"
    logs.mkdir()
    (logs / "artifact_text").symlink_to(outside, target_is_directory=True)
    with EvidenceWriter(logs) as writer:
        writer.add_text("body", "new")
    assert source.read_bytes() == b"real"
    assert not (outside / "body.md").exists()
