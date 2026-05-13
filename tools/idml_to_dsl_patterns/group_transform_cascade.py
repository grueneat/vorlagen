"""Group ItemTransform cascade pattern.

IDML Groups carry their own ItemTransform that must be composed with the
child PageItem's transform to produce page-local coordinates. The
converter walks ancestor Groups innermost-first and composes via
matrix multiplication.

This Pattern wraps the existing _compute_page_local_bbox_pt helper at
tools/idml_to_dsl.py:_compute_page_local_bbox_pt so future call sites
(and the convergence_review classifier) can reference the rule by id.

The current inline call site continues to invoke the helper directly
to preserve byte-identity for the existing emitted templates.
"""
from __future__ import annotations

from .base import Pattern


class GroupTransformCascade:
    id = "group_transform_cascade"
    description = (
        "Compose ancestor Group ItemTransforms with the child PageItem's "
        "ItemTransform to produce page-local coordinates"
    )
    applies_to = "Group"

    def matches(self, idml_element) -> bool:
        if not isinstance(idml_element, dict):
            return False
        ancestors = idml_element.get("ancestor_transforms")
        return bool(ancestors)

    def apply(
        self,
        kwargs: dict,
        idml_element,
        context: dict | None = None,
    ) -> None:
        if not isinstance(idml_element, dict):
            return
        from idml_to_dsl import _compute_page_local_bbox_pt  # type: ignore
        item_transform = idml_element.get("item_transform")
        anchors = idml_element.get("anchors")
        ancestor_transforms = idml_element.get("ancestor_transforms") or []
        spread_item_transform = idml_element.get("spread_item_transform")
        page_item_transform = idml_element.get("page_item_transform")
        page_geometric_bounds = idml_element.get("page_geometric_bounds")
        if (
            item_transform is None
            or anchors is None
            or spread_item_transform is None
            or page_item_transform is None
        ):
            return
        bbox = _compute_page_local_bbox_pt(
            item_transform_str=item_transform,
            anchors=anchors,
            ancestor_transforms=list(ancestor_transforms),
            spread_item_transform_str=spread_item_transform,
            page_item_transform_str=page_item_transform,
            page_geometric_bounds=page_geometric_bounds,
        )
        x_pt, y_pt, w_pt, h_pt, rotation = bbox
        kwargs["x_pt"] = x_pt
        kwargs["y_pt"] = y_pt
        kwargs["w_pt"] = w_pt
        kwargs["h_pt"] = h_pt
        kwargs["rotation_deg"] = rotation
