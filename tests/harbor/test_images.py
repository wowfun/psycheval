"""Image facts are bounded measurements, not semantic image verdicts."""

import io
from pathlib import Path

import pytest

from psycheval.harbor.documents import (
    DocumentLimitError,
    DocumentLimits,
    DocumentParseError,
    MissingDocumentDependency,
    inspect_document,
    select_document,
)
from psycheval.harbor.evidence import SourceSnapshot


def picture(mode="RGB", color="white", size=(10, 5), kind="PNG"):
    image = pytest.importorskip("PIL.Image")
    stream = io.BytesIO()
    with image.new(mode, size, color) as source:
        source.save(stream, format=kind)
    return SourceSnapshot(Path("image." + kind.lower()), stream.getvalue())


@pytest.mark.parametrize("kind", ["PNG", "JPEG"])
def test_image_dimensions_mode_and_solid_statistics(kind):
    report = inspect_document(picture(size=(3840, 3), kind=kind))
    assert (report.width, report.height, report.mode) == (3840, 3, "RGB")
    assert report.extrema == ((255, 255),) * 4
    assert report.means == (255.0,) * 4 and report.variances == (0.0,) * 4
    assert report.nonopaque_fraction == report.transparent_fraction == 0
    assert "3840" in report.to_markdown()


def test_image_alpha_and_variance_are_exact_facts():
    image = pytest.importorskip("PIL.Image")
    stream = io.BytesIO()
    with image.new("RGBA", (2, 1)) as source:
        source.putdata([(0, 0, 0, 0), (200, 100, 50, 255)])
        source.save(stream, format="PNG")
    report = inspect_document(SourceSnapshot(Path("alpha.png"), stream.getvalue()))
    assert report.nonopaque_fraction == report.transparent_fraction == 0.5
    assert report.means == (100, 50, 25, 127.5)
    assert report.variances == (10000, 2500, 625, 16256.25)


def test_image_limits_are_checked_before_pixel_load(monkeypatch):
    image = pytest.importorskip("PIL.Image")
    source = picture(size=(20, 20))

    def forbidden(*args, **kwargs):
        raise AssertionError("pixels decoded before dimension limit")

    monkeypatch.setattr(image.Image, "convert", forbidden)
    with pytest.raises(DocumentLimitError, match="pixel"):
        inspect_document(source, limits=DocumentLimits(image_pixels=399))


def test_image_rejects_corruption_format_mismatch_and_animation():
    pytest.importorskip("PIL.Image")
    with pytest.raises(DocumentParseError):
        inspect_document(SourceSnapshot(Path("bad.png"), b"not an image"))
    with pytest.raises(DocumentParseError, match="Expected PNG"):
        inspect_document(picture(kind="JPEG"), format="png")
    image = pytest.importorskip("PIL.Image")
    stream = io.BytesIO()
    with (
        image.new("RGB", (2, 2), "red") as first,
        image.new("RGB", (2, 2), "blue") as second,
    ):
        first.save(stream, format="PNG", save_all=True, append_images=[second])
    with pytest.raises(DocumentParseError, match="Multiframe"):
        inspect_document(SourceSnapshot(Path("animation.png"), stream.getvalue()))


def test_image_selection_and_missing_extra(tmp_path, monkeypatch):
    import psycheval.harbor.documents as documents

    path = tmp_path / "image.jpg"
    path.write_bytes(picture(kind="JPEG").content)
    assert select_document([tmp_path], format="jpeg").selected == path
    assert inspect_document(path).width == 10

    def blocked(name):
        raise ModuleNotFoundError("blocked", name="PIL")

    monkeypatch.setattr(documents.importlib, "import_module", blocked)
    with pytest.raises(MissingDocumentDependency, match=r"psycheval\[image\]"):
        inspect_document(path)
