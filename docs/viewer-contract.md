# Viewer Contract

PragmaGraph can export a provider-neutral viewer envelope for graph viewers
such as GraphFakos. The envelope is a deterministic JSON contract for observed
code, docs, artifacts, topology, content previews, evidence, provenance,
clusters, edge bundles, and omitted-count metadata.

PragmaGraph owns the observed graph facts. GraphFakos owns the visual renderer,
camera, pointer interaction, themes, overlays, and browser runtime.

## Envelope Shape

The public API lives under `pragmagraph.viewer`.

Key fields:

- `schema_version`: currently `pragmagraph.viewer.v1alpha1`.
- `producer`: package and version metadata for the exporter.
- `snapshot_id`: stable snapshot identity for replay and saved views.
- `graph_stats`: raw node, edge, and cluster counts.
- `level_of_detail`: `raw`, `sampled`, `cluster`, or `meta`.
- `nodes` and `edges`: visible raw or representative graph items.
- `clusters`: structural cluster summaries with representatives, hubs,
  bridges, counts, hints, and expansion cursors.
- `edge_bundles`: intercluster summaries for dense overview rendering.
- `omitted`: raw item counts omitted by budget and reason.
- `content_index`: preview/full-content descriptors for inspector overlays.
- `evidence_index` and `provenance`: source-backed details for review.
- `capabilities`: explicit provider-neutral actions and lookup support.

Large graphs intentionally do not export every raw node by default. The viewer
gets a bounded overview plus deterministic expansion handles.

## CLI Examples

Generate deterministic viewer fixtures under the umbrella scratch tree:

```bash
cd pragmagraph

PYTHONPATH=src .venv/bin/python3.11 -m pragmagraph.__main__ viewer-fixture \
  --scenario viewer-scale-1k \
  --out ../workspace-tmp/pragmagraph-viewer-support/viewer-scale-1k.json \
  --json

PYTHONPATH=src .venv/bin/python3.11 -m pragmagraph.__main__ viewer-fixture \
  --scenario viewer-scale-200k \
  --out ../workspace-tmp/pragmagraph-viewer-support/viewer-scale-200k.json \
  --json

PYTHONPATH=src .venv/bin/python3.11 -m pragmagraph.__main__ viewer-fixture \
  --scenario viewer-scale-1m \
  --out ../workspace-tmp/pragmagraph-viewer-support/viewer-scale-1m.json \
  --json
```

Export a real snapshot as a viewer envelope:

```bash
PYTHONPATH=src .venv/bin/python3.11 -m pragmagraph.__main__ viewer-export \
  .pragmagraph/snapshot.json \
  --lod cluster \
  --node-budget 240 \
  --edge-budget 480 \
  --out .pragmagraph/viewer-envelope.json \
  --json
```

Inspect bounded viewer details:

```bash
PYTHONPATH=src .venv/bin/python3.11 -m pragmagraph.__main__ viewer-cluster \
  ../workspace-tmp/pragmagraph-viewer-support/viewer-scale-200k.json \
  scale-001 \
  --budget 50 \
  --json

PYTHONPATH=src .venv/bin/python3.11 -m pragmagraph.__main__ viewer-content \
  ../workspace-tmp/pragmagraph-viewer-support/viewer-scale-200k.json \
  scale-001:node:0000 \
  --mode preview \
  --json

PYTHONPATH=src .venv/bin/python3.11 -m pragmagraph.__main__ viewer-neighborhood \
  ../workspace-tmp/pragmagraph-viewer-support/viewer-scale-200k.json \
  scale-001:node:0000 \
  --depth 2 \
  --budget 50 \
  --json

PYTHONPATH=src .venv/bin/python3.11 -m pragmagraph.__main__ viewer-path \
  ../workspace-tmp/pragmagraph-viewer-support/viewer-scale-200k.json \
  scale-001:node:0000 \
  scale-002:node:0000 \
  --budget 50 \
  --json

PYTHONPATH=src .venv/bin/python3.11 -m pragmagraph.__main__ viewer-cluster-nodes \
  ../workspace-tmp/pragmagraph-viewer-support/viewer-scale-200k.json \
  scale-001 \
  --role hub \
  --budget 25 \
  --json

PYTHONPATH=src .venv/bin/python3.11 -m pragmagraph.__main__ viewer-omitted \
  ../workspace-tmp/pragmagraph-viewer-support/viewer-scale-200k.json \
  --reason node_budget \
  --json

PYTHONPATH=src .venv/bin/python3.11 -m pragmagraph.__main__ viewer-delta \
  .pragmagraph/snapshot-before.json \
  .pragmagraph/snapshot-after.json \
  --budget 100 \
  --json
```

The helper commands return JSON-serializable structural data only. They do not
emit renderer-specific styling, mutate provider truth, or require GraphFakos to
inspect PragmaGraph internals.

## GraphFakos Handoff

GraphFakos consumes the exported JSON through its provider-envelope adapter:

```bash
cd ../graphfakos

PYTHONPATH=src .venv/bin/python3.11 -m graphfakos.__main__ ui \
  --provider-envelope ../workspace-tmp/pragmagraph-viewer-support/viewer-scale-200k.json \
  --render-engine 3d \
  --theme space \
  --layout grouped \
  --render-limit 240 \
  --serve \
  --open
```

## Boundaries

- PragmaGraph does not import GraphFakos.
- PragmaGraph does not own browser rendering, canvas, WebGL, themes, or camera
  state.
- PragmaGraph does not infer semantic truth or durable memory from viewer
  interaction.
- Durable edits belong to providers or hosts. The envelope only declares
  explicit capability support and provider-neutral draft/lookup surfaces.
