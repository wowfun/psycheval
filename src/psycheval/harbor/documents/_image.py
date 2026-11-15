"""Bounded static PNG/JPEG pixel facts."""

import io
import warnings

from ._limits import DocumentLimitError, DocumentParseError, InspectionBudget
from .models import ImageReport


def inspect(snapshot, backend, kind, limits):
    from PIL import ImageStat

    budget = InspectionBudget(limits)
    budget.pages(1)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", backend.DecompressionBombWarning)
            with backend.open(io.BytesIO(snapshot.content)) as source:
                if source.format != {"png": "PNG", "jpeg": "JPEG"}[kind]:
                    raise DocumentParseError(
                        f"Expected {kind.upper()} image, found {source.format}"
                    )
                width, height = source.size
                if width * height > limits.image_pixels:
                    raise DocumentLimitError("Image exceeds decoded pixel limit")
                if getattr(source, "n_frames", 1) != 1:
                    raise DocumentParseError("Multiframe images are unsupported")
                budget.fact()
                mode = source.mode
                with source.convert("RGBA") as rgba:
                    statistics = ImageStat.Stat(rgba)
                    with rgba.getchannel("A") as alpha:
                        histogram = alpha.histogram()
                    report = ImageReport(
                        snapshot,
                        width,
                        height,
                        mode,
                        tuple(tuple(pair) for pair in statistics.extrema),
                        tuple(statistics.mean),
                        tuple(statistics.var),
                        sum(histogram[:255]) / (width * height),
                        histogram[0] / (width * height),
                        limits.text_bytes,
                    )
    except (backend.DecompressionBombError, backend.DecompressionBombWarning) as error:
        raise DocumentLimitError(f"Image decompression limit: {error}") from error
    except OSError as error:
        raise DocumentParseError(f"Cannot decode image: {error}") from error
    return report
