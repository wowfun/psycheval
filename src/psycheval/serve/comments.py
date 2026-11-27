"""HTTP routes for workspace-overlay scoring-item and Trial review comments."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import Depends, FastAPI, Header, Query, Request
from pydantic import Field

from psycheval.serve.access import SessionIdentity
from psycheval.serve.api_access import (
    ANNOTATOR_ACCESS,
    GUEST_ACCESS,
    access,
    mutation_guard,
    require_annotator,
)
from psycheval.serve.api_http import (
    ProblemException,
    etag,
    if_match_value,
    json_response,
)
from psycheval.serve.api_models import StrictRequest
from psycheval.serve.api_support import harbor_workspace, writable_runtime
from psycheval.serve.runtime import ServeRuntime
from psycheval.state.comments import (
    CommentConflict,
    CommentForbidden,
    CommentNotFound,
    ScoringCommentStore,
    SourceCommentStore,
)


class ScoringCommentCreateRequest(StrictRequest):
    item_key: str = Field(min_length=1, max_length=1024)
    body: str = Field(min_length=1)


class ScoringCommentUpdateRequest(StrictRequest):
    item_key: str = Field(min_length=1, max_length=1024)
    body: str = Field(min_length=1)


class SourceCommentWriteRequest(StrictRequest):
    body: str = Field(min_length=1)


def _translate_comment_error(exc: Exception) -> ProblemException:
    if isinstance(exc, CommentNotFound):
        return ProblemException(404, str(exc))
    if isinstance(exc, CommentForbidden):
        return ProblemException(403, str(exc), slug="comment-forbidden")
    if isinstance(exc, CommentConflict):
        headers = {"ETag": etag(exc.current_revision)} if exc.current_revision else {}
        return ProblemException(412, str(exc), headers=headers)
    return ProblemException(400, str(exc))


def register_comment_routes(app: FastAPI) -> None:
    annotator_mutation = [Depends(mutation_guard)]
    scoring_base = "/api/harbor/datasets/{dataset_id}/tasks/{task}/scoring-comments"

    @app.get(scoring_base)
    @access(GUEST_ACCESS)
    def list_scoring_comments(request: Request, dataset_id: str, task: str) -> Any:
        runtime: ServeRuntime = request.app.state.runtime
        workspace = harbor_workspace(runtime.store, runtime)
        dataset_key, task_name, _ = workspace.resolve_task_for_comments(
            dataset_id, task
        )
        store = ScoringCommentStore(runtime.store.paths.root)
        comments = store.read_task(dataset_key, task_name)
        return json_response(
            {
                "dataset_id": dataset_id,
                "task": task_name,
                "comments": comments,
            }
        )

    @app.post(scoring_base, dependencies=annotator_mutation)
    @access(ANNOTATOR_ACCESS)
    def create_scoring_comment(
        request: Request,
        dataset_id: str,
        task: str,
        body: ScoringCommentCreateRequest,
        identity: Annotated[SessionIdentity, Depends(require_annotator)],
    ) -> Any:
        runtime = writable_runtime(request)
        workspace = harbor_workspace(runtime.store, runtime)
        dataset_key, task_name, valid_keys = workspace.resolve_task_for_comments(
            dataset_id, task, include_scoring_keys=True
        )
        if body.item_key not in valid_keys:
            raise ProblemException(404, "Scoring item not found in Task")
        assert identity.user_id is not None
        store = ScoringCommentStore(runtime.store.paths.root)
        try:
            created, comments = store.add_comment(
                dataset_key,
                task_name,
                body.item_key,
                body.body,
                author_id=identity.user_id,
            )
        except (CommentConflict, CommentForbidden, CommentNotFound, ValueError) as exc:
            raise _translate_comment_error(exc) from exc
        return json_response(
            {
                "dataset_id": dataset_id,
                "task": task_name,
                "item_key": body.item_key,
                "comment": created,
                "comments": comments,
            },
            status=201,
            headers={
                "ETag": etag(created["revision"]),
                "X-Peval-Invalidations": "tasks",
            },
        )

    @app.patch(scoring_base + "/{comment_id}", dependencies=annotator_mutation)
    @access(ANNOTATOR_ACCESS)
    def update_scoring_comment(
        request: Request,
        dataset_id: str,
        task: str,
        comment_id: str,
        body: ScoringCommentUpdateRequest,
        identity: Annotated[SessionIdentity, Depends(require_annotator)],
        if_match: Annotated[str | None, Header(alias="If-Match")] = None,
    ) -> Any:
        runtime = writable_runtime(request)
        expected = if_match_value(if_match)
        workspace = harbor_workspace(runtime.store, runtime)
        dataset_key, task_name, _ = workspace.resolve_task_for_comments(
            dataset_id, task
        )
        store = ScoringCommentStore(runtime.store.paths.root)
        try:
            updated, comments = store.update_comment(
                dataset_key,
                task_name,
                body.item_key,
                comment_id,
                body.body,
                role=identity.role,
                user_id=identity.user_id,
                expected_revision=expected,
            )
        except (CommentConflict, CommentForbidden, CommentNotFound, ValueError) as exc:
            raise _translate_comment_error(exc) from exc
        return json_response(
            {
                "dataset_id": dataset_id,
                "task": task_name,
                "item_key": body.item_key,
                "comment": updated,
                "comments": comments,
            },
            headers={
                "ETag": etag(updated["revision"]),
                "X-Peval-Invalidations": "tasks",
            },
        )

    @app.delete(scoring_base + "/{comment_id}", dependencies=annotator_mutation)
    @access(ANNOTATOR_ACCESS)
    def delete_scoring_comment(
        request: Request,
        dataset_id: str,
        task: str,
        comment_id: str,
        item_key: Annotated[str, Query(min_length=1, max_length=1024)],
        identity: Annotated[SessionIdentity, Depends(require_annotator)],
        if_match: Annotated[str | None, Header(alias="If-Match")] = None,
    ) -> Any:
        runtime = writable_runtime(request)
        expected = if_match_value(if_match)
        workspace = harbor_workspace(runtime.store, runtime)
        dataset_key, task_name, _ = workspace.resolve_task_for_comments(
            dataset_id, task
        )
        store = ScoringCommentStore(runtime.store.paths.root)
        try:
            remaining = store.delete_comment(
                dataset_key,
                task_name,
                item_key,
                comment_id,
                role=identity.role,
                user_id=identity.user_id,
                expected_revision=expected,
            )
        except (CommentConflict, CommentForbidden, CommentNotFound, ValueError) as exc:
            raise _translate_comment_error(exc) from exc
        return json_response(
            {
                "dataset_id": dataset_id,
                "task": task_name,
                "item_key": item_key,
                "comments": remaining,
            },
            headers={"X-Peval-Invalidations": "tasks"},
        )

    source_base = "/api/source-comments/{source_key}"

    @app.get(source_base)
    @access(GUEST_ACCESS)
    def list_source_comments(request: Request, source_key: str) -> Any:
        runtime: ServeRuntime = request.app.state.runtime
        try:
            row = runtime.catalog.row_for_key(source_key)
        except ValueError as exc:
            raise ProblemException(404, str(exc)) from exc
        store = SourceCommentStore(runtime.store.paths.root)
        comments = store.read_comments(str(row["source_ref"]), strict=False)
        return json_response({"source_key": source_key, "comments": comments})

    @app.post(source_base, dependencies=annotator_mutation)
    @access(ANNOTATOR_ACCESS)
    def create_source_comment(
        request: Request,
        source_key: str,
        body: SourceCommentWriteRequest,
        identity: Annotated[SessionIdentity, Depends(require_annotator)],
    ) -> Any:
        runtime = writable_runtime(request)
        try:
            row = runtime.catalog.row_for_key(source_key)
        except ValueError as exc:
            raise ProblemException(404, str(exc)) from exc
        assert identity.user_id is not None
        store = SourceCommentStore(runtime.store.paths.root)
        holder: dict[str, Any] = {}

        def mutate() -> None:
            created, comments = store.add_comment(
                str(row["source_ref"]),
                body.body,
                author_id=identity.user_id,
            )
            holder["comment"] = created
            holder["comments"] = comments

        try:
            runtime.mutate("source-comments", [source_key], mutate)
        except (CommentConflict, CommentForbidden, CommentNotFound, ValueError) as exc:
            raise _translate_comment_error(exc) from exc
        return json_response(
            {
                "source_key": source_key,
                "comment": holder["comment"],
                "comments": holder["comments"],
            },
            status=201,
            headers={
                "ETag": etag(holder["comment"]["revision"]),
                "X-Peval-Invalidations": "catalog",
            },
        )

    @app.patch(source_base + "/{comment_id}", dependencies=annotator_mutation)
    @access(ANNOTATOR_ACCESS)
    def update_source_comment(
        request: Request,
        source_key: str,
        comment_id: str,
        body: SourceCommentWriteRequest,
        identity: Annotated[SessionIdentity, Depends(require_annotator)],
        if_match: Annotated[str | None, Header(alias="If-Match")] = None,
    ) -> Any:
        runtime = writable_runtime(request)
        expected = if_match_value(if_match)
        try:
            row = runtime.catalog.row_for_key(source_key)
        except ValueError as exc:
            raise ProblemException(404, str(exc)) from exc
        store = SourceCommentStore(runtime.store.paths.root)
        holder: dict[str, Any] = {}

        def mutate() -> None:
            updated, comments = store.update_comment(
                str(row["source_ref"]),
                comment_id,
                body.body,
                role=identity.role,
                user_id=identity.user_id,
                expected_revision=expected,
            )
            holder["comment"] = updated
            holder["comments"] = comments

        try:
            runtime.mutate("source-comments", [source_key], mutate)
        except (CommentConflict, CommentForbidden, CommentNotFound, ValueError) as exc:
            raise _translate_comment_error(exc) from exc
        return json_response(
            {
                "source_key": source_key,
                "comment": holder["comment"],
                "comments": holder["comments"],
            },
            headers={
                "ETag": etag(holder["comment"]["revision"]),
                "X-Peval-Invalidations": "catalog",
            },
        )

    @app.delete(source_base + "/{comment_id}", dependencies=annotator_mutation)
    @access(ANNOTATOR_ACCESS)
    def delete_source_comment(
        request: Request,
        source_key: str,
        comment_id: str,
        identity: Annotated[SessionIdentity, Depends(require_annotator)],
        if_match: Annotated[str | None, Header(alias="If-Match")] = None,
    ) -> Any:
        runtime = writable_runtime(request)
        expected = if_match_value(if_match)
        try:
            row = runtime.catalog.row_for_key(source_key)
        except ValueError as exc:
            raise ProblemException(404, str(exc)) from exc
        store = SourceCommentStore(runtime.store.paths.root)
        holder: dict[str, Any] = {}

        def mutate() -> None:
            holder["comments"] = store.delete_comment(
                str(row["source_ref"]),
                comment_id,
                role=identity.role,
                user_id=identity.user_id,
                expected_revision=expected,
            )

        try:
            runtime.mutate("source-comments", [source_key], mutate)
        except (CommentConflict, CommentForbidden, CommentNotFound, ValueError) as exc:
            raise _translate_comment_error(exc) from exc
        return json_response(
            {
                "source_key": source_key,
                "comments": holder["comments"],
            },
            headers={"X-Peval-Invalidations": "catalog"},
        )
