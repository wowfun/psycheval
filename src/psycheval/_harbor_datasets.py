"""Resolve workspace Dataset registrations selected by a mount."""

from __future__ import annotations

from psycheval.config import HarborMount, ToolConfig
from psycheval.harbor.datasets import ResolvedHarborDataset, resolve_harbor_dataset


def resolve_harbor_datasets_for_mount(
    config: ToolConfig, mount: HarborMount
) -> tuple[ResolvedHarborDataset, ...]:
    datasets_by_id = {dataset.id: dataset for dataset in config.harbor_datasets}
    return tuple(
        resolve_harbor_dataset(
            dataset_id=dataset.id, path=dataset.path, format=dataset.format
        )
        for dataset in (datasets_by_id[dataset_id] for dataset_id in mount.dataset_ids)
    )


def harbor_task_roots_for_mount(
    config: ToolConfig, mount: HarborMount
) -> tuple[str, ...]:
    return tuple(
        str(dataset.task_root)
        for dataset in resolve_harbor_datasets_for_mount(config, mount)
    )
