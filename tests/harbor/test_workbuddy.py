from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml
from harbor.models.job.config import JobConfig

from psycheval.harbor import workbuddy
from psycheval.harbor.runtime_config import HostSettings, load_host_settings


@pytest.mark.parametrize("value", [None, {}, "base.yaml", Path("base.yaml")])
def test_preparation_requires_a_model(value, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    before = set(tmp_path.iterdir())
    with pytest.raises(TypeError, match="JobConfig"):
        workbuddy.prepare_workbuddy_job(value)
    assert set(tmp_path.iterdir()) == before


@pytest.mark.parametrize("attempts,multiplier", [(1, 1.0), (3, 2.0), (5, 1.7)])
def test_native_defaults_and_overrides_survive_yaml(
    attempts, multiplier, tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    source = JobConfig(
        n_attempts=attempts,
        timeout_multiplier=multiplier,
        tasks=[{"path": "tasks/one"}],
        agents=[{"name": "oracle"}, {"name": "oracle"}],
    )
    before = source.model_dump()
    tree = set(tmp_path.iterdir())
    result = workbuddy.prepare_workbuddy_job(source)
    loaded = JobConfig.model_validate(
        yaml.safe_load(yaml.safe_dump(result.model_dump(mode="json")))
    )
    assert loaded.n_attempts == attempts and loaded.timeout_multiplier == multiplier
    assert loaded.jobs_dir == Path("jobs") and loaded.job_name == source.job_name
    assert loaded.tasks == source.tasks and loaded.agents == source.agents
    assert source.model_dump() == before
    assert set(tmp_path.iterdir()) == tree


def host_config(root):
    return JobConfig(
        environment={
            "import_path": "psycheval.harbor.environment:HostEnvironment",
            "kwargs": {
                "host_access": {"filesystem": True, "process": True},
                "workdir_root": root,
            },
        },
        agents=[{"name": "oracle", "kwargs": {"nested": {"items": [1]}}}],
        verifier={
            "env": {
                "WORKBUDDY_VERIFIER_LLM_API_KEY": "${WORKBUDDY_VERIFIER_LLM_API_KEY}"
            }
        },
    )


def test_host_adaptation_is_independent_and_does_not_expand_secrets(
    tmp_path, monkeypatch
):
    source = host_config(str(tmp_path / "workspaces"))
    monkeypatch.setenv("WORKBUDDY_VERIFIER_LLM_API_KEY", "private-value")
    before = source.model_dump()
    first = workbuddy.prepare_workbuddy_job(source)
    second = workbuddy.prepare_workbuddy_job(source)
    first.agents[0].kwargs["nested"]["items"].append(2)
    first.environment.kwargs["host_access"]["process"] = False
    assert source.model_dump() == before
    assert second.agents[0].kwargs["nested"]["items"] == [1]
    assert second.environment.kwargs["host_access"]["process"] is True
    assert "private-value" not in second.model_dump_json()
    assert second.environment.import_path.endswith(
        "workbuddy_environment:WorkBuddyHostEnvironment"
    )
    assert not (tmp_path / "workspaces").exists()


@pytest.mark.parametrize(
    "root", [None, "", "relative", "~/workspaces", "C:relative", "\\root"]
)
def test_invalid_host_roots_do_not_mutate_input_or_create_directories(root, tmp_path):
    source = host_config(root)
    before = source.model_dump()
    tree = set(tmp_path.iterdir())
    with pytest.raises(ValueError, match="absolute native path"):
        workbuddy.prepare_workbuddy_job(source)
    assert source.model_dump() == before and set(tmp_path.iterdir()) == tree


def test_root_precedence_toml_and_cwd_stability(tmp_path, monkeypatch):
    path = tmp_path / "host.toml"
    path.write_text('[harbor.host]\nworkdir_root = "relative"\n')
    settings = load_host_settings(path)
    assert settings.workdir_root == tmp_path / "relative"
    source = host_config(str(tmp_path / "explicit"))
    assert workbuddy.prepare_workbuddy_job(
        source, host_settings=settings
    ).environment.kwargs["workdir_root"] == str(tmp_path / "explicit")
    del source.environment.kwargs["workdir_root"]
    prepared = workbuddy.prepare_workbuddy_job(source, host_settings=settings)
    monkeypatch.chdir(tmp_path.parent)
    assert workbuddy.prepare_workbuddy_job(source, host_settings=settings) == prepared
    assert (
        Path(workbuddy.prepare_workbuddy_job(source).environment.kwargs["workdir_root"])
        == Path.home() / "workspaces"
    )
    with pytest.raises(ValueError, match="absolute"):
        HostSettings(workdir_root=Path("relative"))


def test_mutated_nested_model_is_revalidated(tmp_path):
    source = host_config(str(tmp_path))
    source.agents[0].kwargs = []
    with pytest.raises(ValueError):
        workbuddy.prepare_workbuddy_job(source)
    assert source.agents[0].kwargs == []


def test_preparation_preserves_native_secret_values_and_persistence_masks_them():
    secret = "fixture-literal-secret"
    source = JobConfig(
        agents=[{"name": "oracle", "env": {"API_KEY": secret}}],
        environment={"env": {"API_KEY": secret}},
        verifier={"env": {"WORKBUDDY_VERIFIER_LLM_API_KEY": secret}},
    )
    result = workbuddy.prepare_workbuddy_job(source)
    for owner in ("environment", "verifier"):
        assert getattr(result, owner).env == getattr(source, owner).env
        assert getattr(result, owner).env is not getattr(source, owner).env
    assert result.agents[0].env == source.agents[0].env
    assert secret not in result.model_dump_json()


def test_metrics_require_a_lock_or_explicit_selection(tmp_path):
    with pytest.raises(workbuddy.WorkBuddyError, match="expected_tasks"):
        workbuddy.compute_official_metrics(tmp_path)


def test_metrics_infer_selection_from_native_lock_and_keep_sources(
    tmp_path, monkeypatch
):
    from harbor.models.job.lock import JobLock, TrialLock

    lock = JobLock(
        n_concurrent_trials=1,
        retry={},
        trials=[
            TrialLock(
                task={
                    "name": "missing",
                    "type": "local",
                    "digest": "sha256:" + "a" * 64,
                },
                agent={"name": "oracle"},
                environment={},
                verifier={},
            )
        ],
    )
    (tmp_path / "lock.json").write_text(lock.model_dump_json())

    def compute(view, expected_tasks):
        assert len(expected_tasks) == 1
        return {"reward": 0, "n_tasks": 1, "missing_task_count": 1}

    monkeypatch.setitem(
        sys.modules,
        "workbuddy_bench.scorer.metrics",
        SimpleNamespace(compute_job_metrics=compute),
    )
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    assert workbuddy.compute_official_metrics(tmp_path)["missing_task_count"] == 1
    assert {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()} == before


@pytest.fixture
def runtime_distribution(monkeypatch):
    distribution = SimpleNamespace(
        version=workbuddy.WORKBUDDY_VERSION, read_text=lambda name: None
    )
    monkeypatch.setattr(
        workbuddy.importlib.metadata, "distribution", lambda name: distribution
    )
    monkeypatch.setitem(
        sys.modules,
        "workbuddy_bench.judge",
        SimpleNamespace(CompositeVerifier=object),
    )
    return distribution


@pytest.mark.parametrize(
    "metadata,commit",
    [
        (None, None),
        ('{"vcs_info": {"commit_id": "local-revision"}}', "local-revision"),
        ('{"vcs_info": {"commit_id": "another-revision"}}', "another-revision"),
        ('{"vcs_info": {"commit_id": 123}}', None),
        ('{"vcs_info": {"commit_id": ""}}', None),
        ("not json", None),
        ("[]", None),
    ],
)
def test_runtime_commit_metadata_is_optional_provenance(
    runtime_distribution, metadata, commit
):
    runtime_distribution.read_text = lambda name: metadata
    expected = {"version": workbuddy.WORKBUDDY_VERSION}
    if commit is not None:
        expected["commit"] = commit
    assert workbuddy.validate_workbuddy_runtime() == expected


@pytest.mark.parametrize("error", [OSError("unreadable"), UnicodeError("invalid text")])
def test_runtime_accepts_unreadable_source_metadata(runtime_distribution, error):
    def unreadable(name):
        raise error

    runtime_distribution.read_text = unreadable
    assert workbuddy.validate_workbuddy_runtime() == {
        "version": workbuddy.WORKBUDDY_VERSION
    }


def test_runtime_does_not_probe_editable_source_with_git(
    runtime_distribution, tmp_path, monkeypatch
):
    (tmp_path / ".git").mkdir()
    runtime_distribution.read_text = lambda name: json.dumps(
        {"url": tmp_path.as_uri(), "dir_info": {"editable": True}}
    )

    def forbidden(*args, **kwargs):
        pytest.fail("runtime provenance must not execute Git")

    monkeypatch.setattr("subprocess.run", forbidden)
    assert workbuddy.validate_workbuddy_runtime() == {
        "version": workbuddy.WORKBUDDY_VERSION
    }


def test_runtime_still_requires_the_supported_package_version(runtime_distribution):
    runtime_distribution.version = "0.2.0"
    with pytest.raises(workbuddy.WorkBuddyError, match="version must be"):
        workbuddy.validate_workbuddy_runtime()


@pytest.mark.parametrize(
    "module", [None, SimpleNamespace(), SimpleNamespace(CompositeVerifier=None)]
)
def test_runtime_still_requires_a_callable_verifier(
    runtime_distribution, monkeypatch, module
):
    monkeypatch.setitem(sys.modules, "workbuddy_bench.judge", module)
    with pytest.raises(workbuddy.WorkBuddyError, match="CompositeVerifier"):
        workbuddy.validate_workbuddy_runtime()


def test_metric_projection_uses_full_task_identity_and_preserves_sources(tmp_path):
    jobs = tmp_path / "jobs"
    view = tmp_path / "view"
    view.mkdir()
    name = "task-with-a-name-longer-than-thirty-two-characters"
    payload = {"overall": 0.5, "reason": "中文评分 🎯"}
    for job in ("one", "two"):
        trial = jobs / (name[:32] + "__" + job)
        (trial / "verifier").mkdir(parents=True)
        (trial / "config.json").write_text(
            json.dumps({"task": {"path": "D:\\dataset\\tasks\\" + name}}),
            encoding="utf-8",
        )
        (trial / "verifier/score.json").write_text(
            json.dumps(payload, ensure_ascii=False), encoding="utf-8"
        )
    before = {p: p.read_bytes() for p in jobs.rglob("*") if p.is_file()}
    originals = workbuddy._project_metric_trials(jobs, view, {name: name})
    assert len(originals) == 2
    assert set(originals.values()) == {name[:32] + "__one", name[:32] + "__two"}
    for trial in view.iterdir():
        assert trial.name.rsplit("__", 1)[0] == name
        assert (
            json.loads((trial / "verifier/score.json").read_text(encoding="ascii"))
            == payload
        )
    assert {p: p.read_bytes() for p in jobs.rglob("*") if p.is_file()} == before
    with pytest.raises(workbuddy.WorkBuddyError, match="outside expected_tasks"):
        workbuddy._project_metric_trials(jobs, view, {"other-task": "other-task"})


@pytest.mark.parametrize("job_config", [None, {}, {"tasks": []}, {"unrelated": True}])
def test_metric_projection_skips_job_summaries_with_trial_like_names(
    tmp_path, job_config
):
    job = tmp_path / "jobs/batch__run"
    job.mkdir(parents=True)
    (job / "result.json").write_text('{"stats": {}, "finished_at": "fixture"}')
    if job_config is not None:
        (job / "config.json").write_text(json.dumps(job_config))
    # Failed Trials still count without a score, using config or retained result evidence.
    for name, config in (("one", {"task": {"path": "/tasks/one"}}), ("two", None)):
        trial = job / f"{name}__attempt"
        trial.mkdir()
        (trial / "result.json").write_text(
            json.dumps({"trial_name": trial.name, "task_name": name})
        )
        if config is not None:
            (trial / "config.json").write_text(json.dumps(config))
    for root in (job,):
        view = tmp_path / f"view-{root.name}"
        view.mkdir()
        originals = workbuddy._project_metric_trials(
            root, view, {"one": "one", "two": "two"}
        )
        assert set(originals.values()) == {"one__attempt", "two__attempt"}


def test_metric_projection_preserves_bounded_read_error(tmp_path):
    trial = tmp_path / "jobs/one__attempt"
    (trial / "verifier").mkdir(parents=True)
    (trial / "verifier/score.json").write_text("{}")
    (trial / "config.json").write_bytes(b" " * (workbuddy.EVIDENCE_FILE_LIMIT + 1))
    view = tmp_path / "view"
    view.mkdir()
    with pytest.raises(
        workbuddy.WorkBuddyError, match="Trial configuration.*bounded regular file"
    ):
        workbuddy._project_metric_trials(trial.parent, view, {"one": "one"})


@pytest.mark.parametrize(
    "config",
    [None, [], {}, {"task": {}}, {"task": {"path": ""}}, {"task": {"path": 1}}],
)
def test_metric_projection_rejects_invalid_present_identity_despite_score(
    tmp_path, config
):
    trial = tmp_path / "jobs/one__attempt"
    (trial / "verifier").mkdir(parents=True)
    (trial / "verifier/score.json").write_text('{"overall": 1}')
    (trial / "config.json").write_text(json.dumps(config))
    view = tmp_path / "view"
    view.mkdir()
    with pytest.raises(workbuddy.WorkBuddyError, match="invalid Trial Task identity"):
        workbuddy._project_metric_trials(trial.parent, view, {"one": "one"})


def test_metric_projection_rejects_conflicting_task_identities(tmp_path):
    for attempt, path in (("a", "/first/one"), ("b", "/second/one")):
        trial = tmp_path / "job" / f"one__{attempt}"
        (trial / "verifier").mkdir(parents=True)
        (trial / "verifier/score.json").write_text('{"overall": 1}')
        (trial / "config.json").write_text(json.dumps({"task": {"path": path}}))
    view = tmp_path / "view"
    view.mkdir()
    with pytest.raises(workbuddy.WorkBuddyError, match="conflicting Task identities"):
        workbuddy._project_metric_trials(tmp_path / "job", view, {"one": "one"})


def test_metrics_reject_linked_job_directory(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    link = tmp_path / "link"
    if os.name == "nt":
        subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(source)],
            check=True,
            capture_output=True,
        )
    else:
        link.symlink_to(source, target_is_directory=True)
    with pytest.raises(workbuddy.WorkBuddyError, match="symbolic link"):
        workbuddy.compute_official_metrics(link, expected_tasks=["one"])
    assert list(source.iterdir()) == []


@pytest.mark.parametrize("job_name", ["normal", "batch__run"])
def test_metrics_reject_parent_of_jobs_instead_of_reporting_zero(tmp_path, job_name):
    trial = tmp_path / "jobs" / job_name / "one__attempt"
    (trial / "verifier").mkdir(parents=True)
    (trial / "verifier/score.json").write_text('{"overall": 1}')
    view = tmp_path / "view"
    view.mkdir()
    with pytest.raises(workbuddy.WorkBuddyError, match="one Harbor Job"):
        workbuddy._project_metric_trials(tmp_path / "jobs", view, {"one": "one"})


def test_metrics_compare_paths_and_digests_independently(tmp_path):
    from harbor.models.job.lock import TrialLock

    for suffix in ("locked", "unlocked"):
        trial = tmp_path / "job" / f"one__{suffix}"
        (trial / "verifier").mkdir(parents=True)
        (trial / "verifier/score.json").write_text('{"overall": 1}')
        (trial / "config.json").write_text(json.dumps({"task": {"path": "/tasks/one"}}))
        if suffix == "locked":
            lock = TrialLock(
                task={"name": "one", "type": "local", "digest": "sha256:" + "a" * 64},
                agent={"name": "oracle"},
                environment={},
                verifier={},
            )
            (trial / "lock.json").write_text(lock.model_dump_json())
    view = tmp_path / "view"
    view.mkdir()
    assert (
        len(workbuddy._project_metric_trials(tmp_path / "job", view, {"one": "one"}))
        == 2
    )


@pytest.mark.parametrize(
    "payload",
    [
        {"per_task": {"unexpected": {}}},
        {"missing_tasks": ["unexpected"]},
        {"missing_tasks": "task-000000"},
        {"per_task": []},
        {"per_task": {"task-000000": None}},
        {"per_task": {"task-000000": {"attempts": [None]}}},
    ],
)
def test_metrics_reject_malformed_scorer_task_entries(tmp_path, monkeypatch, payload):
    monkeypatch.setitem(
        sys.modules,
        "workbuddy_bench.scorer.metrics",
        SimpleNamespace(compute_job_metrics=lambda *args, **kwargs: payload),
    )
    with pytest.raises(workbuddy.WorkBuddyError, match="official metrics.*Task"):
        workbuddy.compute_official_metrics(tmp_path, expected_tasks=["example"])
