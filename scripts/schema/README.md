# Vendored SCIP schema

`scip.proto` is pinned from Sourcegraph's SCIP repository at commit
`e01e97efac2f6b8c266b4d04825f1f1eab7b8f6c`:

<https://github.com/sourcegraph/scip/blob/e01e97efac2f6b8c266b4d04825f1f1eab7b8f6c/scip.proto>

The source schema is distributed under Apache-2.0. The checked-in Python
binding is generated with:

```bash
python3.11 -m grpc_tools.protoc \
  -I scripts/schema \
  --python_out=src/pragmagraph/interchange/_schema \
  scripts/schema/scip.proto
```

Runtime consumers install `pragmagraph[scip]`; regeneration additionally
requires `grpcio-tools`.

`normalize_fixture.py` replaces only the producer-local
`metadata.project_root` before a generated index is checked in. Certification
fixtures use stable synthetic `file:///fixtures/pragmagraph/scip/...` roots so
public artifacts never expose a contributor workstation path.
