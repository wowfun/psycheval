from __future__ import annotations

from psycheval.state.artifacts import StateArtifactMixin
from psycheval.state.ingest import StateIngestMixin
from psycheval.state.mutations import StateMutationMixin
from psycheval.state.paths import (
    WorkspacePaths,
    resolve_workspace_root,
    workspace_paths,
)
from psycheval.state.queries import StateQueryMixin
from psycheval.state.schema import StateSchemaMixin


class ServeStateStore(
    StateSchemaMixin,
    StateIngestMixin,
    StateQueryMixin,
    StateMutationMixin,
    StateArtifactMixin,
):
    def __init__(
        self,
        paths: WorkspacePaths,
        *,
        initialize: bool = True,
        readonly: bool = False,
    ) -> None:
        del readonly
        self.paths = paths
        if initialize:
            self.initialize_schema()

    def close(self) -> None:
        return None


def open_workspace_state(root: str | None = None) -> ServeStateStore:
    resolved = resolve_workspace_root(root)
    return ServeStateStore(workspace_paths(resolved))


def open_workspace_state_readonly(root: str | None = None) -> ServeStateStore:
    resolved = resolve_workspace_root(root)
    return ServeStateStore(
        workspace_paths(resolved),
        initialize=False,
        readonly=True,
    )
