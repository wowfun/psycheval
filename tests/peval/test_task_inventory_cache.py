import json

from psycheval.serve.task_inventory_cache import TaskInventoryCache


def test_cache_enforces_entry_and_byte_budgets():
    for cache in (TaskInventoryCache(max_entries=1), TaskInventoryCache(max_bytes=1)):
        loads = []

        def get(key):
            def load(read):
                loads.append(key)
                return {"text": read(key).decode()}

            return cache.get(
                key, load=load, read=lambda _: b"text", signature=lambda _: 1
            )

        assert get("first") == get("second") == get("first") == {"text": "text"}
        assert loads == ["first", "second", "first"]


def test_cache_rechecks_safety_and_does_not_reuse_unstable_reads():
    cache = TaskInventoryCache()
    stamp, reads, denied = 1, 0, False

    def signature(_):
        if denied:
            raise ValueError("Unsafe path")
        return stamp

    def read(path):
        nonlocal reads
        signature(path)
        reads += 1
        return b'{"value":"safe"}'

    def load(reader):
        try:
            return json.loads(reader("source"))
        except ValueError:
            return {"error": "Unsafe path"}

    def get(loader=load):
        return cache.get("task", load=loader, read=read, signature=signature)

    assert get() == get() == {"value": "safe"}
    assert reads == 1
    denied = True
    assert get() == {"error": "Unsafe path"}
    denied = False

    def unstable(reader):
        nonlocal stamp
        result = load(reader)
        stamp += 1
        return result

    assert get(unstable) == get() == {"value": "safe"}
    assert reads == 3  # The value read across a change was not cached.
