"""Tests for 3-role annotator permissions and scoring/Trial comments CRUD."""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from psycheval.config import (
    HarborDataset,
    HarborMount,
    load_config,
    write_workspace_harbor_config,
)
from psycheval.serve import ServeAccess, ServeRuntime
from psycheval.serve.api import create_app
from psycheval.state import CatalogQuery, open_workspace_state
from psycheval.state.comments import (
    COMMENT_BODY_MAX_BYTES,
    CommentConflict,
    CommentForbidden,
    ScoringCommentStore,
    SourceCommentStore,
    format_comments_for_export,
    normalize_dataset_comment_key,
    resolve_dataset_comment_key,
    validate_comment_body,
)
from tests.fixtures.judge_task import YAML
from tests.peval.cli_inputs_support import write_trial_cell_artifacts
from tests.peval.test_harbor_evidence import write_evidence_trial, write_task
from tests.peval.test_workbuddy_datasets import _write_workbuddy_bundle


def _xlsx_shared_text(payload: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        chunks = []
        for name in archive.namelist():
            if name.endswith(".xml"):
                chunks.append(archive.read(name).decode("utf-8", errors="ignore"))
        return "\n".join(chunks)


def _setup_workspace(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    (tmp_path / "peval.toml").write_text(
        'locale = "en"\nanalysis_eval_slug = "default"\n', encoding="utf-8"
    )
    native = tmp_path / "native"
    scored = native / "scored"
    write_task(scored, "org/scored")
    (scored / "tests/grader.json").write_text(
        json.dumps(
            {
                "custom_checks": ["answer", "output"],
                "scoring": {"descriptions": {"custom:answer": "Check answer."}},
            }
        ),
        encoding="utf-8",
    )
    (scored / "tests/judge.yaml").write_text(YAML, encoding="utf-8")

    office = _write_workbuddy_bundle(tmp_path / "office")
    (office / "tasks/office-one/tests/judge.yaml").write_text(YAML, encoding="utf-8")

    jobs = tmp_path / "jobs"
    trial = jobs / "eval-job" / "office-trial"
    write_evidence_trial(
        trial,
        config_task={"path": str(office / "tasks/office-one")},
        result={
            "task_name": "workbuddy/office-one",
            "verifier_result": {"rewards": {"reward": 0.5}},
        },
    )

    write_trial_cell_artifacts(
        tmp_path / "runs/default/psychevo/local-session/local-trial",
        session_id="local-session",
        trial_key="local-trial",
    )

    write_workspace_harbor_config(
        tmp_path / "peval.toml",
        (
            HarborDataset(id="native", path=str(native)),
            HarborDataset(id="office", path=str(office), format="workbuddy.v1"),
        ),
        (HarborMount(id="jobs", path=str(jobs), dataset_ids=("office",)),),
    )
    return native, office, jobs, trial


def test_comment_body_validation_and_store_ownership(tmp_path: Path) -> None:
    assert validate_comment_body("  line 1\n\tline 2  ") == "line 1\n\tline 2"
    with pytest.raises(ValueError, match="empty"):
        validate_comment_body("   \n\t ")
    with pytest.raises(ValueError, match="UTF-8 bytes"):
        validate_comment_body("a" * (COMMENT_BODY_MAX_BYTES + 1))
    with pytest.raises(ValueError, match="control"):
        validate_comment_body("bad\x00char")

    assert normalize_dataset_comment_key("org/pbench") == "org-pbench"
    assert normalize_dataset_comment_key("My Org / Bench_v1.0") == "my-org-bench_v1.0"
    assert normalize_dataset_comment_key("CON") == "dataset-con"
    with pytest.raises(ValueError, match="Invalid dataset comment key"):
        normalize_dataset_comment_key("///...")

    # Manifest resolution: WorkBuddy [dataset].id > Harbor [dataset].name > directory basename.
    wb_dir = tmp_path / "local-wb-folder"
    wb_dir.mkdir()
    (wb_dir / "dataset.toml").write_text(
        '[dataset]\nschema = "workbuddy.dataset.v1"\nid = "Team/Office_v1.0"\n',
        encoding="utf-8",
    )
    assert (
        resolve_dataset_comment_key(wb_dir, dataset_id="my-local-id")
        == "team-office_v1.0"
    )
    wb_tasks_sub = wb_dir / "tasks"
    wb_tasks_sub.mkdir()
    assert (
        resolve_dataset_comment_key(
            wb_tasks_sub, dataset_id="my-local-id", dataset_format="workbuddy.v1"
        )
        == "team-office_v1.0"
    )

    harbor_manifest_dir = tmp_path / "local-harbor-folder"
    harbor_manifest_dir.mkdir()
    (harbor_manifest_dir / "dataset.toml").write_text(
        '[dataset]\nname = "org/pbench-v2"\nversion = "1.0.0"\n',
        encoding="utf-8",
    )
    assert (
        resolve_dataset_comment_key(harbor_manifest_dir, dataset_id="alias-id")
        == "org-pbench-v2"
    )

    plain_dir = tmp_path / "pbench-v1.0"
    plain_dir.mkdir()
    assert resolve_dataset_comment_key(plain_dir, dataset_id="pbench") == "pbench-v1.0"

    store = ScoringCommentStore(tmp_path)
    first, items = store.add_comment(
        "org/pbench",
        "task-a",
        '["","rubric","fidelity"]',
        "Initial finding",
        author_id="alice",
    )
    assert len(items) == 1
    assert first["author_id"] == "alice"
    assert "author_role" not in first
    assert "created_at_ms" not in first
    assert isinstance(first["updated_at_ms"], int)
    assert first["revision"]
    expected_file = (
        tmp_path
        / ".peval"
        / "datasets"
        / "org-pbench"
        / "task-a"
        / "scoring_comments.json"
    )
    assert expected_file.is_file()
    # One store-level lock lives under .peval/locks/scoring-comments.lock, never inside .peval/datasets/.
    assert list((tmp_path / ".peval" / "datasets").rglob("*.lock")) == []
    assert [p.name for p in (tmp_path / ".peval" / "locks").iterdir()] == [
        "scoring-comments.lock"
    ]

    with pytest.raises(CommentConflict) as conflict:
        store.update_comment(
            "org/pbench",
            "task-a",
            '["","rubric","fidelity"]',
            first["id"],
            "Stale write",
            role="annotator",
            user_id="alice",
            expected_revision="stale-rev",
        )
    assert conflict.value.current_revision == first["revision"]

    with pytest.raises(CommentForbidden):
        store.update_comment(
            "org/pbench",
            "task-a",
            '["","rubric","fidelity"]',
            first["id"],
            "Bob hijack",
            role="annotator",
            user_id="bob",
            expected_revision=first["revision"],
        )

    updated, _ = store.update_comment(
        "org/pbench",
        "task-a",
        '["","rubric","fidelity"]',
        first["id"],
        "Admin moderated",
        role="admin",
        user_id="admin",
        expected_revision=first["revision"],
    )
    assert updated["body"] == "Admin moderated"
    assert updated["author_id"] == "alice"
    assert updated["revision"] != first["revision"]
    exported_text = format_comments_for_export([updated])
    assert exported_text.startswith("[alice @ ")
    assert exported_text.endswith("] Admin moderated")

    # Deleting the last comment removes scoring_comments.json and prunes empty dirs.
    remaining = store.delete_comment(
        "org/pbench",
        "task-a",
        '["","rubric","fidelity"]',
        updated["id"],
        role="admin",
        user_id="admin",
        expected_revision=updated["revision"],
    )
    assert remaining == []
    assert not expected_file.exists()
    assert not (tmp_path / ".peval" / "datasets").exists()


def test_source_comment_store_leaves_notes_untouched_and_cleans_harbor_overlay(
    tmp_path: Path,
) -> None:
    store = SourceCommentStore(tmp_path)
    source_ref = "harbor/jobs/eval-job/trial-1"
    overlay_dir = tmp_path / source_ref
    created, comments = store.add_comment(
        source_ref,
        "Judge missed citation",
        author_id="alice",
    )
    assert len(comments) == 1
    assert "author_role" not in created
    assert "created_at_ms" not in created
    raw_disk = json.loads(
        (overlay_dir / "review_comments.json").read_text(encoding="utf-8")
    )
    assert set(raw_disk["comments"][0].keys()) == {
        "id",
        "body",
        "author_id",
        "updated_at_ms",
    }
    assert not (overlay_dir / "notes.md").exists()

    remaining = store.delete_comment(
        source_ref,
        created["id"],
        role="annotator",
        user_id="alice",
        expected_revision=created["revision"],
    )
    assert remaining == []
    assert not (overlay_dir / "review_comments.json").exists()
    assert not overlay_dir.exists()
    assert not (tmp_path / "harbor").exists()
    assert [p.name for p in (tmp_path / ".peval" / "locks").iterdir()] == [
        "source-comments.lock"
    ]
    with pytest.raises(ValueError, match="Unsupported source reference"):
        store.add_comment(
            "runs/default/psychevo/too-short", "Bad ref", author_id="alice"
        )


def test_manual_minimal_review_comments_json_and_catalog_sync(tmp_path: Path) -> None:
    _native, _office, _jobs, _trial = _setup_workspace(tmp_path)
    state = open_workspace_state(str(tmp_path))
    runtime = ServeRuntime(state, load_config(workspace_root=tmp_path))
    runtime.catalog.reconcile()
    store = SourceCommentStore(tmp_path)

    try:
        rows = runtime.catalog.query(CatalogQuery()).items
        harbor_row = next(r for r in rows if r.payload.get("kind") == "harbor-trial")
        local_row = next(r for r in rows if r.payload.get("kind") != "harbor-trial")
        harbor_ref = str(harbor_row.payload["source_ref"])
        local_ref = str(local_row.payload["source_ref"])
        harbor_file = tmp_path / harbor_ref / "review_comments.json"
        harbor_file.parent.mkdir(parents=True, exist_ok=True)
        # 1. Object without schema_version containing minimal {id, body} + extra/invalid entries.
        harbor_file.write_text(
            json.dumps(
                {
                    "comments": [
                        {"id": "m1", "body": "手动最小评论"},
                        {
                            "id": "m2",
                            "body": "Author only",
                            "author_id": "alice",
                            "author_role": "annotator",
                            "created_at_ms": 1000,
                        },
                        {
                            "id": "m3",
                            "body": "Timestamp only",
                            "updated_at_ms": 1700000000000,
                        },
                        {"id": "", "body": "Missing id ignored"},
                        {"id": "bad2", "body": "   "},
                    ]
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        # 2. Bare top-level JSON array in local source's review_comments.json.
        local_file = tmp_path / local_ref / "review_comments.json"
        local_file.write_text(
            json.dumps([{"id": "bare-1", "body": "Bare array comment"}]),
            encoding="utf-8",
        )

        parsed_harbor = store.read_comments(harbor_ref, strict=True)
        assert [c["id"] for c in parsed_harbor] == ["m1", "m2", "m3"]
        assert set(parsed_harbor[0].keys()) == {"id", "body", "revision"}
        assert set(parsed_harbor[1].keys()) == {"id", "body", "author_id", "revision"}
        assert set(parsed_harbor[2].keys()) == {
            "id",
            "body",
            "updated_at_ms",
            "revision",
        }
        assert format_comments_for_export(parsed_harbor) == (
            "手动最小评论\n\n"
            "[alice] Author only\n\n"
            "[2023-11-14 22:13 UTC] Timestamp only"
        )

        parsed_local = store.read_comments(local_ref, strict=True)
        assert len(parsed_local) == 1
        assert set(parsed_local[0].keys()) == {"id", "body", "revision"}
        assert parsed_local[0]["body"] == "Bare array comment"

        # Annotator cannot mutate unauthored minimal comments or admin comments, even with user_id="admin".
        with pytest.raises(CommentForbidden):
            store.update_comment(
                harbor_ref,
                "m1",
                "Hijack",
                role="annotator",
                user_id="alice",
                expected_revision=parsed_harbor[0]["revision"],
            )
        admin_created, _ = store.add_comment(local_ref, "Admin note", author_id="admin")
        with pytest.raises(CommentForbidden):
            store.update_comment(
                local_ref,
                admin_created["id"],
                "Spoof admin",
                role="annotator",
                user_id="admin",
                expected_revision=admin_created["revision"],
            )
        # Adding a comment preserves omitted fields on existing untouched minimal comments.
        after_add = store.read_comments(local_ref, strict=True)
        assert set(after_add[0].keys()) == {"id", "body", "revision"}

        # Admin can edit a minimal comment (which had no updated_at_ms/author_id).
        edited_m1, _ = store.update_comment(
            harbor_ref,
            "m1",
            "手动最小评论已修改",
            role="admin",
            user_id="admin",
            expected_revision=parsed_harbor[0]["revision"],
        )
        assert edited_m1["body"] == "手动最小评论已修改"
        assert "author_id" not in edited_m1
        assert isinstance(edited_m1["updated_at_ms"], int)

        # Direct review_comments.json edits are picked up by catalog reconcile, search, and filter.
        runtime.catalog.reconcile()
        catalog_items = runtime.catalog.query(
            CatalogQuery(search="手动最小评论已修改", review_comments=("commented",))
        ).items
        assert [item.source_key for item in catalog_items] == [harbor_row.source_key]
        assert catalog_items[0].payload["review_comment_count"] == 3
    finally:
        runtime.close()
        state.close()


def test_manual_minimal_scoring_comments_json_and_task_detail_sync(
    tmp_path: Path,
) -> None:
    native, office, _jobs, _trial = _setup_workspace(tmp_path)
    state = open_workspace_state(str(tmp_path))
    runtime = ServeRuntime(state, load_config(workspace_root=tmp_path))
    runtime.catalog.reconcile()
    access = ServeAccess("admin-secret", annotator_password="ann-secret")
    app = create_app(runtime, access)
    store = ScoringCommentStore(tmp_path)

    try:
        with TestClient(app) as client:
            origin = {"Origin": "http://testserver"}
            office_item_key = client.get(
                "/api/harbor/datasets/office/tasks/office-one"
            ).json()["task"]["scoring_items"][0]["key"]
            native_item_key = client.get(
                "/api/harbor/datasets/native/tasks/scored"
            ).json()["task"]["scoring_items"][0]["key"]

            office_key = resolve_dataset_comment_key(
                office, dataset_id="office", dataset_format="workbuddy.v1"
            )
            native_key = resolve_dataset_comment_key(native, dataset_id="native")

            # 1. Per-Task object without schema_version containing minimal {id, body} + extra/invalid entries.
            office_file = (
                tmp_path
                / ".peval"
                / "datasets"
                / office_key
                / "office-one"
                / "scoring_comments.json"
            )
            office_file.parent.mkdir(parents=True, exist_ok=True)
            office_file.write_text(
                json.dumps(
                    {
                        "items": {
                            office_item_key: [
                                {"id": "s1", "body": "手动最小评分项评论"},
                                {
                                    "id": "s2",
                                    "body": "Author only",
                                    "author_id": "alice",
                                    "author_role": "annotator",
                                    "created_at_ms": 1000,
                                },
                                {"id": "", "body": "Missing id ignored"},
                            ]
                        }
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            # 2. Bare per-Task item map without "items" wrapper (including an item key literally named "items").
            native_file = (
                tmp_path
                / ".peval"
                / "datasets"
                / native_key
                / "scored"
                / "scoring_comments.json"
            )
            native_file.parent.mkdir(parents=True, exist_ok=True)
            native_file.write_text(
                json.dumps(
                    {
                        native_item_key: [
                            {"id": "bare-s1", "body": "Bare map scoring comment"}
                        ],
                        "items": [
                            {"id": "named-items", "body": "Item key named items"}
                        ],
                    }
                ),
                encoding="utf-8",
            )

            parsed_office = store.read_task(office_key, "office-one")[office_item_key]
            assert [c["id"] for c in parsed_office] == ["s1", "s2"]
            assert set(parsed_office[0].keys()) == {"id", "body", "revision"}
            assert set(parsed_office[1].keys()) == {
                "id",
                "body",
                "author_id",
                "revision",
            }
            assert store.read_task(native_key, "scored")[native_item_key][0][
                "body"
            ] == ("Bare map scoring comment")
            assert store.read_task(native_key, "scored")["items"][0]["body"] == (
                "Item key named items"
            )

            # Adding a comment preserves omitted fields on untouched minimal comments.
            store.add_comment(
                native_key, "scored", native_item_key, "Follow up", author_id="admin"
            )
            after_add = store.read_task(native_key, "scored")[native_item_key]
            assert set(after_add[0].keys()) == {"id", "body", "revision"}
            assert after_add[1]["author_id"] == "admin"
            assert "author_role" not in after_add[1]
            assert "created_at_ms" not in after_add[1]

            # Annotator cannot edit minimal unauthored scoring comment; Admin can.
            with pytest.raises(CommentForbidden):
                store.update_comment(
                    office_key,
                    "office-one",
                    office_item_key,
                    "s1",
                    "Hijack",
                    role="annotator",
                    user_id="alice",
                    expected_revision=parsed_office[0]["revision"],
                )
            edited_s1, _ = store.update_comment(
                office_key,
                "office-one",
                office_item_key,
                "s1",
                "手动最小评分项评论已修改",
                role="admin",
                user_id="admin",
                expected_revision=parsed_office[0]["revision"],
            )
            assert "author_id" not in edited_s1
            assert isinstance(edited_s1["updated_at_ms"], int)

            # Reflected immediately in Task detail, Datasets collection, and flattened JSON/XLSX exports.
            detail = client.get("/api/harbor/datasets/office/tasks/office-one").json()
            assert detail["task"]["scoring_comment_count"] == 2
            assert (
                detail["task"]["scoring_comments"][office_item_key][0]["body"]
                == "手动最小评分项评论已修改"
            )
            collections = client.get("/api/collections/datasets").json()["datasets"]
            office_summary = next(d for d in collections if d["id"] == "office")[
                "tasks"
            ][0]
            assert office_summary["scoring_comment_count"] == 2

            export_payload = {
                "kind": "json",
                "mode": "items",
                "columns": ["dataset", "task", "id", "scoring_comments"],
                "rows": [
                    {
                        "dataset_id": "native",
                        "task": "scored",
                        "item_key": native_item_key,
                    }
                ],
            }
            flat_json = client.post(
                "/api/harbor/task-exports", json=export_payload, headers=origin
            )
            assert flat_json.status_code == 200
            exported_comments = flat_json.json()[0]["scoring_comments"]
            assert set(exported_comments[0].keys()) == {"id", "body", "revision"}

            flat_xlsx = client.post(
                "/api/harbor/task-exports",
                json={**export_payload, "kind": "xlsx"},
                headers=origin,
            )
            assert flat_xlsx.status_code == 200
            xlsx_xml = _xlsx_shared_text(flat_xlsx.content)
            assert "Bare map scoring comment" in xlsx_xml
            assert "[admin @" in xlsx_xml

            # Renaming a Task moves its per-Task scoring_comments.json to the new <task> directory.
            login_admin = client.post(
                "/api/session",
                json={"role": "admin", "password": "admin-secret"},
                headers=origin,
            )
            assert login_admin.status_code == 200
            scored_rev = client.get("/api/harbor/datasets/native/tasks/scored").json()[
                "task"
            ]["revision"]
            renamed = client.patch(
                "/api/harbor/datasets/native/tasks/scored",
                json={"new_directory": "scored-renamed"},
                headers={**origin, "If-Match": f'"{scored_rev}"'},
            )
            assert renamed.status_code == 202
            assert not native_file.exists()
            moved_file = (
                tmp_path
                / ".peval"
                / "datasets"
                / native_key
                / "scored-renamed"
                / "scoring_comments.json"
            )
            assert moved_file.is_file()
            renamed_detail = client.get(
                "/api/harbor/datasets/native/tasks/scored-renamed"
            ).json()
            assert (
                renamed_detail["task"]["scoring_comments"][native_item_key][0]["body"]
                == "Bare map scoring comment"
            )

            # Malformed structure safely ignored on read and rejected under strict mode.
            moved_file.write_text(
                json.dumps({"schema_version": 99, "items": {}}), encoding="utf-8"
            )
            assert store.read_dataset(native_key) == {}
            with pytest.raises(ValueError, match="structure"):
                store._read_task_raw(native_key, "scored-renamed", strict=True)
    finally:
        runtime.close()
        state.close()


def test_http_annotator_least_privilege_scoring_and_source_comments_e2e(
    tmp_path: Path,
) -> None:
    native, office, _jobs, _trial = _setup_workspace(tmp_path)
    state = open_workspace_state(str(tmp_path))
    runtime = ServeRuntime(state, load_config(workspace_root=tmp_path))
    runtime.catalog.reconcile()
    access = ServeAccess("admin-secret", annotator_password="ann-secret")
    app = create_app(runtime, access)

    try:
        rows = runtime.catalog.query(CatalogQuery()).items
        harbor_row = next(r for r in rows if r.payload.get("kind") == "harbor-trial")
        local_row = next(r for r in rows if r.payload.get("kind") != "harbor-trial")

        with (
            TestClient(app) as guest,
            TestClient(app) as alice,
            TestClient(app) as bob,
            TestClient(app) as admin,
        ):
            origin = {"Origin": "http://testserver"}

            # Session introspection & login validation.
            assert guest.get("/api/session").json() == {
                "authentication_enabled": True,
                "admin_login_enabled": True,
                "annotator_login_enabled": True,
                "role": "guest",
                "user_id": None,
            }
            assert (
                alice.post(
                    "/api/session",
                    json={
                        "role": "annotator",
                        "user_id": "   ",
                        "password": "ann-secret",
                    },
                    headers=origin,
                ).status_code
                == 422
            )
            for reserved_id in ("admin", "Admin", "ADMIN"):
                assert (
                    alice.post(
                        "/api/session",
                        json={
                            "role": "annotator",
                            "user_id": reserved_id,
                            "password": "ann-secret",
                        },
                        headers=origin,
                    ).status_code
                    == 422
                )
            assert (
                alice.post(
                    "/api/session",
                    json={
                        "role": "annotator",
                        "user_id": "alice",
                        "password": "wrong",
                    },
                    headers=origin,
                ).status_code
                == 401
            )
            login_alice = alice.post(
                "/api/session",
                json={
                    "role": "annotator",
                    "user_id": "alice",
                    "password": "ann-secret",
                },
                headers=origin,
            )
            assert login_alice.status_code == 200
            assert login_alice.json()["role"] == "annotator"
            assert login_alice.json()["user_id"] == "alice"
            assert "peval_session=" in login_alice.headers["set-cookie"]

            login_bob = bob.post(
                "/api/session",
                json={
                    "role": "annotator",
                    "user_id": "bob",
                    "password": "ann-secret",
                },
                headers=origin,
            )
            assert login_bob.status_code == 200
            login_admin = admin.post(
                "/api/session",
                json={"role": "admin", "password": "admin-secret"},
                headers=origin,
            )
            assert login_admin.status_code == 200

            # Strict least-privilege boundary for Annotator (non-expired 403 must NOT use session-expired).
            assert alice.get("/config").status_code == 403
            admin_route_as_annotator = alice.get("/api/config")
            assert admin_route_as_annotator.status_code == 403
            assert (
                admin_route_as_annotator.json()["type"] == "urn:peval:problem:forbidden"
            )
            admin_route_as_guest = guest.get("/api/config")
            assert admin_route_as_guest.status_code == 403
            assert (
                admin_route_as_guest.json()["type"]
                == "urn:peval:problem:session-expired"
            )
            assert alice.get("/api/sources").status_code == 403
            assert alice.get("/api/acp/agents").status_code == 403
            assert (
                alice.patch(
                    f"/api/sources/{harbor_row.source_key}",
                    json={"alias": "blocked"},
                    headers=origin,
                ).status_code
                == 403
            )
            assert (
                alice.put(
                    "/api/harbor/datasets/native/tasks/scored/files/instruction.md",
                    json={"content": "blocked"},
                    headers=origin,
                ).status_code
                == 403
            )
            assert (
                alice.post(
                    "/api/harbor/datasets/native/tasks/scored/reveal",
                    json={"path": "instruction.md"},
                    headers=origin,
                ).status_code
                == 403
            )
            assert (
                alice.patch(
                    "/api/harbor/datasets/native/tasks/scored/metadata",
                    json={"key": "qa", "value": "blocked"},
                    headers=origin,
                ).status_code
                == 403
            )
            assert (
                alice.put(
                    "/api/views/blocked",
                    json={"filters": {}, "group_by": "agent", "notes": ""},
                    headers=origin,
                ).status_code
                == 403
            )
            # Annotator sees guest-redacted projections (no server host paths).
            alice_catalog = alice.get("/api/catalog").json()
            for item in alice_catalog["items"]:
                assert "source_ref" not in item
                assert "path" not in item
            alice_datasets = alice.get("/api/collections/datasets").json()
            assert str(native) not in json.dumps(alice_datasets)
            assert str(office) not in json.dumps(alice_datasets)

            # Scoring-item comments on native Harbor AND read-only WorkBuddy datasets.
            office_detail = alice.get(
                "/api/harbor/datasets/office/tasks/office-one"
            ).json()
            office_item_key = office_detail["task"]["scoring_items"][0]["key"]
            native_detail = alice.get("/api/harbor/datasets/native/tasks/scored").json()
            native_item_key = native_detail["task"]["scoring_items"][0]["key"]

            # Guest cannot write comments (unauthenticated 403 carries session-expired).
            guest_write = guest.post(
                "/api/harbor/datasets/office/tasks/office-one/scoring-comments",
                json={"item_key": office_item_key, "body": "guest blocked"},
                headers=origin,
            )
            assert guest_write.status_code == 403
            assert guest_write.json()["type"] == "urn:peval:problem:session-expired"

            # Annotator Alice creates comment on read-only WorkBuddy dataset + native dataset.
            created_office = alice.post(
                "/api/harbor/datasets/office/tasks/office-one/scoring-comments",
                json={"item_key": office_item_key, "body": "评分标准缺少边界说明"},
                headers=origin,
            )
            assert created_office.status_code == 201
            assert created_office.headers["x-peval-invalidations"] == "tasks"
            office_comment = created_office.json()["comment"]
            assert office_comment["author_id"] == "alice"
            assert "author_role" not in office_comment
            assert "created_at_ms" not in office_comment

            created_native = alice.post(
                "/api/harbor/datasets/native/tasks/scored/scoring-comments",
                json={"item_key": native_item_key, "body": "Rule check verified"},
                headers=origin,
            )
            assert created_native.status_code == 201

            # Attached immediately to task detail & dataset collection read models.
            refreshed_office = alice.get(
                "/api/harbor/datasets/office/tasks/office-one"
            ).json()
            assert refreshed_office["task"]["scoring_comment_count"] == 1
            assert (
                refreshed_office["task"]["scoring_comments"][office_item_key][0]["body"]
                == "评分标准缺少边界说明"
            )
            collections = alice.get("/api/collections/datasets").json()["datasets"]
            office_summary = next(d for d in collections if d["id"] == "office")[
                "tasks"
            ][0]
            assert office_summary["scoring_comment_count"] == 1
            assert (
                office_summary["scoring_comments"][office_item_key][0]["author_id"]
                == "alice"
            )

            # Optimistic lock conflict -> 412 with current ETag.
            stale = alice.patch(
                f"/api/harbor/datasets/office/tasks/office-one/scoring-comments/{office_comment['id']}",
                json={"item_key": office_item_key, "body": "stale"},
                headers={**origin, "If-Match": '"wrong-rev"'},
            )
            assert stale.status_code == 412
            assert stale.headers["etag"] == f'"{office_comment["revision"]}"'

            # Cross-annotator ownership check -> 403 with urn:peval:problem:comment-forbidden.
            bob_forbidden = bob.patch(
                f"/api/harbor/datasets/office/tasks/office-one/scoring-comments/{office_comment['id']}",
                json={"item_key": office_item_key, "body": "bob hijack"},
                headers={**origin, "If-Match": f'"{office_comment["revision"]}"'},
            )
            assert bob_forbidden.status_code == 403
            assert bob_forbidden.json()["type"] == "urn:peval:problem:comment-forbidden"

            bob_del_forbidden = bob.delete(
                f"/api/harbor/datasets/office/tasks/office-one/scoring-comments/{office_comment['id']}",
                params={"item_key": office_item_key},
                headers={**origin, "If-Match": f'"{office_comment["revision"]}"'},
            )
            assert bob_del_forbidden.status_code == 403
            assert (
                bob_del_forbidden.json()["type"]
                == "urn:peval:problem:comment-forbidden"
            )

            # Alice updates own comment.
            alice_updated = alice.patch(
                f"/api/harbor/datasets/office/tasks/office-one/scoring-comments/{office_comment['id']}",
                json={"item_key": office_item_key, "body": "已补充边界说明"},
                headers={**origin, "If-Match": f'"{office_comment["revision"]}"'},
            )
            assert alice_updated.status_code == 200
            office_comment = alice_updated.json()["comment"]
            assert office_comment["body"] == "已补充边界说明"

            # Bob adds a second comment on the same item; Admin moderates & deletes it.
            bob_added = bob.post(
                "/api/harbor/datasets/office/tasks/office-one/scoring-comments",
                json={"item_key": office_item_key, "body": "Second opinion"},
                headers=origin,
            )
            assert bob_added.status_code == 201
            bob_comment = bob_added.json()["comment"]

            admin_edited = admin.patch(
                f"/api/harbor/datasets/office/tasks/office-one/scoring-comments/{bob_comment['id']}",
                json={"item_key": office_item_key, "body": "Moderated by admin"},
                headers={**origin, "If-Match": f'"{bob_comment["revision"]}"'},
            )
            assert admin_edited.status_code == 200
            bob_comment = admin_edited.json()["comment"]

            # Flattened task JSON & XLSX exports include scoring_comments.
            export_payload = {
                "kind": "json",
                "mode": "items",
                "columns": ["dataset", "task", "id", "scoring_comments"],
                "rows": [
                    {
                        "dataset_id": "office",
                        "task": "office-one",
                        "item_key": office_item_key,
                    }
                ],
            }
            flat_json = alice.post(
                "/api/harbor/task-exports", json=export_payload, headers=origin
            )
            assert flat_json.status_code == 200
            exported_row = flat_json.json()[0]
            assert len(exported_row["scoring_comments"]) == 2
            assert exported_row["scoring_comments"][0]["body"] == "已补充边界说明"

            flat_xlsx = alice.post(
                "/api/harbor/task-exports",
                json={**export_payload, "kind": "xlsx"},
                headers=origin,
            )
            assert flat_xlsx.status_code == 200
            xlsx_xml = _xlsx_shared_text(flat_xlsx.content)
            assert "[alice @" in xlsx_xml
            assert "] 已补充边界说明" in xlsx_xml
            assert "[bob @" in xlsx_xml
            assert "] Moderated by admin" in xlsx_xml

            # Admin deletes Bob's comment.
            admin_del = admin.delete(
                f"/api/harbor/datasets/office/tasks/office-one/scoring-comments/{bob_comment['id']}",
                params={"item_key": office_item_key},
                headers={**origin, "If-Match": f'"{bob_comment["revision"]}"'},
            )
            assert admin_del.status_code == 200
            assert len(admin_del.json()["comments"]) == 1

            # Scoring-item comments live at .peval/datasets/<dataset>/<task>/scoring_comments.json,
            # independent of local absolute path and peval.toml dataset ID.
            store = ScoringCommentStore(tmp_path)
            office_key = resolve_dataset_comment_key(
                office, dataset_id="renamed-office", dataset_format="workbuddy.v1"
            )
            assert len(store.read_task(office_key, "office-one")[office_item_key]) == 1
            assert (
                tmp_path
                / ".peval"
                / "datasets"
                / office_key
                / "office-one"
                / "scoring_comments.json"
            ).is_file()

            # Scoring-result comments on Harbor Trial & local source.
            assert (
                guest.post(
                    f"/api/source-comments/{harbor_row.source_key}",
                    json={"body": "guest blocked"},
                    headers=origin,
                ).status_code
                == 403
            )

            created_trial = alice.post(
                f"/api/source-comments/{harbor_row.source_key}",
                json={"body": "漏判核心图表误差"},
                headers=origin,
            )
            assert created_trial.status_code == 201
            assert created_trial.headers["x-peval-invalidations"] == "catalog"
            trial_comment = created_trial.json()["comment"]
            assert trial_comment["author_id"] == "alice"

            created_local = alice.post(
                f"/api/source-comments/{local_row.source_key}",
                json={"body": "Local trial note"},
                headers=origin,
            )
            assert created_local.status_code == 201

            # Catalog projects comments, counts, column_presence, facets, filters, and full-text search.
            catalog_page = alice.get("/api/catalog").json()
            assert catalog_page["column_presence"]["review_comments"] == 2
            assert catalog_page["facets"]["review_comments"] == [
                {"value": "commented", "count": 2}
            ]
            projected_harbor = next(
                item
                for item in catalog_page["items"]
                if item["source_key"] == harbor_row.source_key
            )
            assert projected_harbor["review_comment_count"] == 1
            assert projected_harbor["review_comments_present"] is True
            assert projected_harbor["review_comments"][0]["body"] == "漏判核心图表误差"

            assert (
                alice.get(
                    "/api/catalog", params={"review_comment": "invalid"}
                ).status_code
                == 400
            )
            only_commented = alice.get(
                "/api/catalog", params={"review_comment": "commented"}
            ).json()
            assert len(only_commented["items"]) == 2
            only_uncommented = alice.get(
                "/api/catalog", params={"review_comment": "uncommented"}
            ).json()
            assert only_uncommented["items"] == []

            search_hit = alice.get(
                "/api/catalog", params={"search": "漏判核心图表"}
            ).json()
            assert [item["source_key"] for item in search_hit["items"]] == [
                harbor_row.source_key
            ]
            search_author = alice.get("/api/catalog", params={"search": "alice"}).json()
            assert len(search_author["items"]) == 2

            # Cross-annotator 403 comment-forbidden & 412 conflict on source comments.
            bob_src_forbidden = bob.patch(
                f"/api/source-comments/{harbor_row.source_key}/{trial_comment['id']}",
                json={"body": "bob hijack"},
                headers={**origin, "If-Match": f'"{trial_comment["revision"]}"'},
            )
            assert bob_src_forbidden.status_code == 403
            assert (
                bob_src_forbidden.json()["type"]
                == "urn:peval:problem:comment-forbidden"
            )

            stale_src = alice.patch(
                f"/api/source-comments/{harbor_row.source_key}/{trial_comment['id']}",
                json={"body": "stale"},
                headers={**origin, "If-Match": '"wrong"'},
            )
            assert stale_src.status_code == 412

            # Leaderboard XLSX export includes Comments column.
            xlsx_res = admin.post(
                "/api/exports",
                json={"kind": "xlsx", "source_keys": [harbor_row.source_key]},
                headers=origin,
            )
            assert xlsx_res.status_code == 200
            lb_xml = _xlsx_shared_text(xlsx_res.content)
            assert "Comments" in lb_xml
            assert "[alice @" in lb_xml
            assert "] 漏判核心图表误差" in lb_xml

            # Admin deletes Alice's Harbor Trial comment and catalog updates synchronously.
            deleted_src = admin.delete(
                f"/api/source-comments/{harbor_row.source_key}/{trial_comment['id']}",
                headers={**origin, "If-Match": f'"{trial_comment["revision"]}"'},
            )
            assert deleted_src.status_code == 200
            assert deleted_src.json()["comments"] == []
            after_delete = alice.get("/api/catalog").json()
            assert after_delete["column_presence"]["review_comments"] == 1
            assert after_delete["facets"]["review_comments"] == [
                {"value": "commented", "count": 1},
                {"value": "uncommented", "count": 1},
            ]
            filtered_commented = alice.get(
                "/api/catalog", params={"review_comment": "commented"}
            ).json()
            assert [item["source_key"] for item in filtered_commented["items"]] == [
                local_row.source_key
            ]
            assert filtered_commented["facets"]["review_comments"] == [
                {"value": "commented", "count": 1}
            ]
            filtered_uncommented = alice.get(
                "/api/catalog", params={"review_comment": "uncommented"}
            ).json()
            assert [item["source_key"] for item in filtered_uncommented["items"]] == [
                harbor_row.source_key
            ]
            assert filtered_uncommented["facets"]["review_comments"] == [
                {"value": "uncommented", "count": 1}
            ]
            post_filtered = alice.post(
                "/api/catalog-queries",
                json={
                    "state": "active",
                    "page": 1,
                    "page_size": 100,
                    "search": "",
                    "sort": "last_turn_end",
                    "direction": "desc",
                    "categories": [],
                    "tags": [],
                    "agents": [],
                    "models": [],
                    "results": [],
                    "review_comments": ["uncommented"],
                    "views": [],
                    "browser_views": [],
                },
                headers=origin,
            )
            assert post_filtered.status_code == 200
            assert [item["source_key"] for item in post_filtered.json()["items"]] == [
                harbor_row.source_key
            ]
            summary_base = {
                "state": "active",
                "search": "",
                "datasets": [],
                "categories": [],
                "tags": [],
                "agents": [],
                "models": [],
                "tasks": [],
                "jobs": [],
                "providers": [],
                "results": [],
                "views": [],
                "browser_views": [],
                "inline_views": [],
                "metric_scope": "family",
                "group_by": "overall",
            }
            for review_comments_filter, expected_count in (
                ([], 2),
                (["commented"], 1),
                (["uncommented"], 1),
            ):
                summary_res = alice.post(
                    "/api/catalog-summaries",
                    json={**summary_base, "review_comments": review_comments_filter},
                    headers=origin,
                )
                assert summary_res.status_code == 200
                assert summary_res.json()["summary"]["matched_count"] == expected_count
            saved_view = admin.put(
                "/api/views/commented-only",
                json={
                    "filters": {"review_comments": ["commented"]},
                    "group_by": "overall",
                    "notes": "",
                },
                headers=origin,
            )
            assert saved_view.status_code == 201
            assert saved_view.json()["filters"] == {"review_comments": ["commented"]}
            by_view = alice.get(
                "/api/catalog", params={"view": "commented-only"}
            ).json()
            assert [item["source_key"] for item in by_view["items"]] == [
                local_row.source_key
            ]
    finally:
        runtime.close()
        state.close()


def test_delete_purge_and_failed_rename_maintain_scoring_comment_integrity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    native, _office, _jobs, _trial = _setup_workspace(tmp_path)
    state = open_workspace_state(str(tmp_path))
    runtime = ServeRuntime(state, load_config(workspace_root=tmp_path))
    runtime.catalog.reconcile()
    access = ServeAccess("admin-secret")
    app = create_app(runtime, access)
    store = ScoringCommentStore(tmp_path)
    dataset_key = resolve_dataset_comment_key(native, dataset_id="native")

    try:
        from psycheval.serve.harbor_workspace import HarborWorkspace

        workspace = HarborWorkspace(runtime.store.paths.config_path, runtime.config)
        item_key = workspace.task_detail("native", "scored")["task"]["scoring_items"][
            0
        ]["key"]

        # 1. Failed comment move during rename rolls back the Task directory rename.
        store.add_comment(
            dataset_key, "scored", item_key, "Keep attached", author_id="admin"
        )
        scored_rev = workspace.task_detail("native", "scored")["task"]["revision"]

        def boom(*_args, **_kwargs):
            raise OSError("simulated comment move failure")

        monkeypatch.setattr(ScoringCommentStore, "move_task_comments_locked", boom)
        with pytest.raises(OSError, match="simulated comment move failure"):
            workspace.rename_task(
                dataset_id="native",
                task="scored",
                new_directory="scored-new",
                expected_revision=scored_rev,
            )
        assert (native / "scored").is_dir()
        assert not (native / "scored-new").exists()
        assert len(store.read_task(dataset_key, "scored")[item_key]) == 1
        monkeypatch.undo()

        # 2. Hard delete removes scoring_comments.json so a recreated Task does not inherit it.
        workspace.delete_task(
            dataset_id="native",
            task="scored",
            expected_revision=scored_rev,
        )
        assert store.read_task(dataset_key, "scored") == {}
        assert not (
            tmp_path / ".peval/datasets" / dataset_key / "scored/scoring_comments.json"
        ).exists()
        write_task(native / "scored", "org/scored")
        (native / "scored/tests/grader.json").write_text(
            json.dumps({"custom_checks": ["answer"]}), encoding="utf-8"
        )
        recreated = workspace.task_detail("native", "scored")
        assert recreated["task"]["scoring_comment_count"] == 0

        # 3. Trash keeps comments; purging removes them when no active Task shares the name.
        new_item_key = recreated["task"]["scoring_items"][0]["key"]
        store.add_comment(
            dataset_key, "scored", new_item_key, "Old trash note", author_id="admin"
        )
        trashed = workspace.trash_task(
            dataset_id="native",
            task="scored",
            expected_revision=recreated["task"]["revision"],
        )
        assert len(store.read_task(dataset_key, "scored")[new_item_key]) == 1
        workspace.purge_task(
            dataset_id="native",
            entry_id=trashed["entry_id"],
            expected_revision=trashed["revision"],
        )
        assert store.read_task(dataset_key, "scored") == {}

        # 4. Purging a trashed Task preserves comments when a new active Task already reused that name.
        write_task(native / "scored", "org/scored")
        (native / "scored/tests/grader.json").write_text(
            json.dumps({"custom_checks": ["answer"]}), encoding="utf-8"
        )
        first_rev = workspace.task_detail("native", "scored")["task"]["revision"]
        trashed_old = workspace.trash_task(
            dataset_id="native", task="scored", expected_revision=first_rev
        )
        write_task(native / "scored", "org/scored")
        (native / "scored/tests/grader.json").write_text(
            json.dumps({"custom_checks": ["answer"]}), encoding="utf-8"
        )
        store.add_comment(
            dataset_key,
            "scored",
            new_item_key,
            "Active replacement comment",
            author_id="admin",
        )
        workspace.purge_task(
            dataset_id="native",
            entry_id=trashed_old["entry_id"],
            expected_revision=trashed_old["revision"],
        )
        assert [
            c["body"] for c in store.read_task(dataset_key, "scored")[new_item_key]
        ] == ["Active replacement comment"]

        # 5. Scoring-comment routes work without invoking workspace.task_detail().
        def fail_task_detail(*_args, **_kwargs):
            raise AssertionError("scoring-comment route must not call task_detail")

        monkeypatch.setattr(HarborWorkspace, "task_detail", fail_task_detail)
        with TestClient(app) as client:
            origin = {"Origin": "http://testserver"}
            login = client.post(
                "/api/session",
                json={"role": "admin", "password": "admin-secret"},
                headers=origin,
            )
            assert login.status_code == 200
            listed = client.get(
                "/api/harbor/datasets/native/tasks/scored/scoring-comments"
            )
            assert listed.status_code == 200
            created = client.post(
                "/api/harbor/datasets/native/tasks/scored/scoring-comments",
                json={"item_key": new_item_key, "body": "Fast route create"},
                headers=origin,
            )
            assert created.status_code == 201
            cid = created.json()["comment"]["id"]
            rev = created.json()["comment"]["revision"]
            updated = client.patch(
                f"/api/harbor/datasets/native/tasks/scored/scoring-comments/{cid}",
                json={"item_key": new_item_key, "body": "Fast route edit"},
                headers={**origin, "If-Match": f'"{rev}"'},
            )
            assert updated.status_code == 200
            rev2 = updated.json()["comment"]["revision"]
            deleted = client.delete(
                f"/api/harbor/datasets/native/tasks/scored/scoring-comments/{cid}",
                params={"item_key": new_item_key},
                headers={**origin, "If-Match": f'"{rev2}"'},
            )
            assert deleted.status_code == 200
    finally:
        runtime.close()
        state.close()
