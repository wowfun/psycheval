from __future__ import annotations

import unittest

from psycheval.serve.visibility import (
    project_catalog_payload,
    project_detail_payload,
    project_guest_error,
    project_harbor_inventory,
)


class ServeGuestVisibilityTests(unittest.TestCase):
    def test_harbor_summary_projection_has_an_explicit_guest_allowlist(self) -> None:
        payload = {
            "datasets": [],
            "workbuddy_summaries": [
                {
                    "plan_id": "plan-a",
                    "dataset_id": "office",
                    "generated_at": "2026-09-03T00:00:00+00:00",
                    "provisional": True,
                    "pending_jobs": ["job-a"],
                    "metrics": {"reward": 0.5},
                    "warnings": ["public warning"],
                    "run_dir": "/private/jobs",
                }
            ],
        }

        guest = project_harbor_inventory(payload, "guest")

        self.assertNotIn("run_dir", guest["workbuddy_summaries"][0])
        self.assertEqual(guest["workbuddy_summaries"][0]["plan_id"], "plan-a")
        self.assertIs(project_harbor_inventory(payload, "admin"), payload)

    def test_internal_error_projection_is_generic_for_guests(self) -> None:
        detail = "failed to read /srv/private/workspace/state.db"
        self.assertEqual(
            project_guest_error(500, detail, "guest"), "internal server error"
        )
        self.assertEqual(project_guest_error(500, detail, "admin"), detail)
        self.assertEqual(
            project_guest_error(400, detail, "guest"),
            "request could not be completed",
        )
        self.assertEqual(
            project_guest_error(404, r"failed at C:\private\state.db", "guest"),
            "request could not be completed",
        )
        self.assertEqual(
            project_guest_error(400, "invalid request", "guest"), "invalid request"
        )
        self.assertEqual(
            project_guest_error(
                400, "invalid request target /api/catalog?page=2", "guest"
            ),
            "invalid request target /api/catalog?page=2",
        )

    def test_catalog_projection_removes_posix_windows_and_unc_source_paths(
        self,
    ) -> None:
        rows = [
            {
                "source_key": "posix",
                "label": "/srv/evals/run-a/trial.json",
                "input_path": "/srv/evals/run-a/trial.json",
                "artifact_dir": "runs/private/run-a",
                "source_ref": "sources/private.json",
                "last_error": "failed at /srv/evals/run-a/trial.json",
                "task_metadata": {
                    "path": "/srv/harbor/tasks/task-a",
                    "diagnostic": "invalid /srv/harbor/tasks/task-a/task.toml",
                    "description": "Published task description",
                    "task_ref": {"dataset_id": "tasks", "task": "task-a"},
                },
                "harbor_provenance": {
                    "regrade": {
                        "path": "/srv/harbor/jobs/source-trial",
                        "trial_id": "trial-a",
                    }
                },
                "verifier_evidence": {
                    "status": "present",
                    "score": 0.7,
                    "score_source": "reward",
                    "harbor_reward": 0.6,
                    "reward_consistency": "drifted",
                    "tests": {"passed": 3, "total": 4},
                    "components": {"overall": 0.7},
                    "llm_judge": {"rubrics": [{"id": "private"}]},
                    "warnings": ["private path /srv/secret"],
                    "revision": "private-revision",
                    "artifacts": [{"id": "private-artifact"}],
                },
            },
            {
                "source_key": "windows",
                "label": r"C:\Users\admin\evals\trial.json",
                "db_path": r"C:\Users\admin\evals\sessions.db",
            },
            {
                "source_key": "unc",
                "label": r"\\server\private-share\evals\trial.json",
                "path": r"\\server\private-share\evals\trial.json",
            },
        ]
        payload = {
            "items": rows,
            "total": 3,
            "facets": {"models": [{"value": "public", "count": 3}]},
        }

        guest = project_catalog_payload(payload, "guest")

        self.assertIsNot(guest, payload)
        for row in guest["items"]:
            for field in (
                "artifact_dir",
                "db_path",
                "input_path",
                "last_error",
                "path",
                "source_ref",
            ):
                self.assertNotIn(field, row)
            self.assertEqual(row["label"], "trial.json")
        task = guest["items"][0]["task_metadata"]
        self.assertEqual(task, {"description": "Published task description"})
        self.assertEqual(
            guest["items"][0]["harbor_provenance"]["regrade"],
            {"trial_id": "trial-a"},
        )
        self.assertEqual(
            guest["items"][0]["verifier_evidence"],
            {
                "status": "present",
                "score": 0.7,
                "score_source": "reward",
                "harbor_reward": 0.6,
                "reward_consistency": "drifted",
                "tests": {"passed": 3, "total": 4},
                "components": {"overall": 0.7},
            },
        )
        self.assertIs(guest["facets"], payload["facets"])
        self.assertIn("path", rows[0]["task_metadata"])
        self.assertIn("path", rows[0]["harbor_provenance"]["regrade"])
        self.assertIs(project_catalog_payload(payload, "admin"), payload)

    def test_report_projection_preserves_published_content_but_not_metadata_paths(
        self,
    ) -> None:
        report = {
            "trajectory": [
                {
                    "steps": [
                        {
                            "source": "user",
                            "message": "Inspect /published/input.txt",
                            "tool_calls": [
                                {"arguments": {"path": r"C:\published\tool-input.txt"}}
                            ],
                        }
                    ]
                }
            ],
            "trajectory_meta": [
                {
                    "data_ref": {
                        "label": r"\\server\private\trial.json",
                        "path": r"\\server\private\trial.json",
                        "relative_path": "../private/trial.json",
                        "source_ref": "private/source-ref",
                        "regrade": {
                            "path": "/srv/regrade/source",
                            "trial_id": "original",
                        },
                    },
                    "task_metadata": {
                        "path": r"C:\Harbor\Tasks\task-a",
                        "diagnostic": "private diagnostic",
                        "description": "Public description",
                        "task_ref": {"dataset_id": "tasks", "task": "task-a"},
                    },
                    "harbor_provenance": {
                        "regrade": {
                            "path": "/srv/regrade/source",
                            "trial_id": "original",
                        }
                    },
                    "verifier_evidence": {
                        "status": "present",
                        "score": 0.7,
                        "score_source": "reward",
                        "reward_consistency": "matched",
                        "artifacts": [{"id": "secret"}],
                        "warnings": ["private"],
                    },
                }
            ],
            "annotations": {
                "analysis": [
                    {
                        "relative_path": "runs/private/analysis.md",
                        "relative_paths": {
                            "md": "runs/private/analysis.md",
                            "json": "runs/private/analysis.json",
                        },
                        "source_ref": "private/analysis-source",
                        "md_report": "Analysis mentions /published/result.txt",
                        "markdown_reports": [
                            {
                                "source": "harbor_trial",
                                "markdown": "Harbor analysis body",
                                "relative_path": "artifacts/logs/analysis.md",
                            },
                            {
                                "source": "workspace_overlay",
                                "markdown": "Workspace analysis body",
                                "relative_path": "runs/private/analysis.md",
                            },
                        ],
                    }
                ],
                "notes": [
                    {
                        "source_ref": {"relative_path": "runs/private/notes.md"},
                        "markdown": "Note mentions \\server\\published\\note.txt",
                    }
                ],
            },
        }
        payload = {"source_key": "source", "report": report}

        guest = project_detail_payload(payload, "guest")["report"]

        data_ref = guest["trajectory_meta"][0]["data_ref"]
        self.assertEqual(
            data_ref,
            {
                "label": "trial.json",
                "regrade": {"trial_id": "original"},
            },
        )
        self.assertEqual(
            guest["trajectory_meta"][0]["task_metadata"],
            {
                "description": "Public description",
                "task_ref": {"dataset_id": "tasks", "task": "task-a"},
            },
        )
        self.assertEqual(
            guest["trajectory_meta"][0]["harbor_provenance"]["regrade"],
            {"trial_id": "original"},
        )
        self.assertEqual(
            guest["trajectory_meta"][0]["verifier_evidence"],
            {
                "status": "present",
                "score": 0.7,
                "score_source": "reward",
                "reward_consistency": "matched",
            },
        )
        self.assertEqual(
            guest["annotations"]["analysis"],
            [
                {
                    "md_report": "Analysis mentions /published/result.txt",
                    "markdown_reports": [
                        {
                            "source": "harbor_trial",
                            "markdown": "Harbor analysis body",
                        },
                        {
                            "source": "workspace_overlay",
                            "markdown": "Workspace analysis body",
                        },
                    ],
                }
            ],
        )
        self.assertEqual(
            guest["annotations"]["notes"],
            [{"markdown": "Note mentions \\server\\published\\note.txt"}],
        )
        self.assertEqual(
            guest["trajectory"][0]["steps"][0]["message"],
            "Inspect /published/input.txt",
        )
        self.assertEqual(
            guest["trajectory"][0]["steps"][0]["tool_calls"][0]["arguments"]["path"],
            r"C:\published\tool-input.txt",
        )
        self.assertIs(guest["trajectory"], report["trajectory"])
        self.assertIn("path", report["trajectory_meta"][0]["data_ref"])
        self.assertIn("relative_path", report["annotations"]["analysis"][0])
        self.assertIs(project_detail_payload(payload, "admin"), payload)


if __name__ == "__main__":
    unittest.main()
