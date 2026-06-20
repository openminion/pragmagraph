# Security Policy

## Reporting a vulnerability

Please do not open a public issue with exploit details.

Instead:

1. contact the project maintainers privately through the security reporting
   channel used for OpenMinion, or
2. if that channel is unavailable, open a minimal private coordination thread
   without exploit details and request a secure handoff path.

## Scope

This package's security posture follows the same general rules as OpenMinion:

1. report vulnerabilities privately first,
2. do not publish proof-of-exploit details before maintainers have had time to
   assess and respond,
3. include affected version, reproduction steps, and impact summary when
   possible.

## Package boundary

`pragmagraph` is a standalone package. Security reports should say whether the
issue affects:

1. the public standalone package surface (`src/pragmagraph/`),
2. fixture or contract tooling that is repository-local but ships with the
   repo, or
3. runtime/service behavior that belongs outside this package boundary
   (for example hosted transports, OpenMinion provider wiring, or browser
   workbench runtime concerns).

## Dependency note

If an issue depends on the optional precise parser family, git-history tooling,
or a larger host runtime, call that out explicitly. That helps determine
whether the problem is in the package-owned observed-fact substrate or in an
external integration path.
