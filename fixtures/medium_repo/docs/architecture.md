# Architecture

## Overview

`RuntimeGraph` coordinates `SnapshotLoader`, `GraphState`, and the Markdown
adapter.

## Data Flow

Facts are indexed from source, normalized into snapshots, and surfaced through
reports plus graph exports.
