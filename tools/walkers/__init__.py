"""Inventory walkers — extract structural inventory from each pipeline stage.

Members:
- schema: dataclass schema for ``SCAFFOLD_INVENTORY.yml``
- walk_idml_inventory: IDML-side walker (frames, text runs, paragraph styles, colors)
- walk_sla: SLA-side wrapper around ``tools.sla_lib.reader.SLADocument``
- walk_pdf: preview/baseline PDF word counts + image placements
- walk_build_py: AST walk of a (reconciled) ``build.py``
"""
