"""When an IDML ImageFrame references an .ai file, emit ImageFrame with
image=<vector_output> (a PDF) instead of the raster PNG fallback. This
preserves vector quality through Scribus's renderer.

Precondition:
  links_export.yml entry for the .ai source MUST carry a vector_output
  field. tools/links_export.py emits the PDF passthrough alongside the
  PNG raster for every .ai input.

Context:
  context["links_manifest"]: the parsed links_export.yml dict (the
    'assets' block where keys are NFC-normalised original basenames).
"""
from __future__ import annotations

from pathlib import Path

from .base import Pattern


class ImageFramePdfSourceForVectors:
    id = "image_frame_pdf_source_for_vectors"
    description = (
        "Emit ImageFrame with PDF (vector) source for AI assets, preserving "
        "vector quality through Scribus"
    )
    applies_to = "ImageFrame"

    def matches(self, idml_element) -> bool:
        if hasattr(idml_element, "get"):
            uri = idml_element.get("LinkResourceURI", "") or ""
            return uri.lower().endswith(".ai")
        return False

    def apply(
        self,
        kwargs: dict,
        idml_element,
        context: dict | None = None,
    ) -> None:
        if not hasattr(idml_element, "get"):
            return
        uri = idml_element.get("LinkResourceURI", "") or ""
        if not uri.lower().endswith(".ai"):
            return
        if not context or "links_manifest" not in context:
            kwargs["_todo"] = (
                "image_frame_pdf_source_for_vectors: links_manifest missing "
                "from context; cannot resolve vector_output"
            )
            return
        ai_basename = Path(uri).name
        entry = context["links_manifest"].get(ai_basename)
        if entry and entry.get("vector_output"):
            kwargs["image"] = entry["vector_output"]
