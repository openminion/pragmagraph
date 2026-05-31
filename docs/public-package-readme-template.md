# Public Package README Template

Last updated: 2026-05-31
Status: Active

Purpose: document the shared public README header and safety-section format used
by OpenMinion-owned standalone packages.

## In scope

1. Top-level `README.md` files for standalone packages such as `sophiagraph`
   and `pragmagraph`.
2. First-viewport package presentation for GitHub and PyPI.
3. Trust, license, and brand-use sections that should appear near the top of a
   public package README.

## Out of scope

1. OpenMinion runtime module README files under `openminion/src/openminion/`.
2. Package-specific feature lists, API documentation, and release instructions.
3. Generated website pages or broader brand guidelines.

## When to use

1. Use this template when creating or refreshing a public README for an
   OpenMinion-owned standalone package.
2. Prefer the hosted brand logo URL when it exists:
   `https://www.openminion.com/brand/<package>-logo.png`.
3. If the hosted logo does not exist yet, use a repo-local asset under
   `docs/assets/` and include it in the package manifest if the package ships a
   source distribution.
4. Keep the opening paragraph package-specific. Do not copy another package's
   ownership claims or name-origin explanation unless they are true for the new
   package.

## Template

```md
<p align="center">
  <img src="<logo-path-or-url>" alt="<Project> logo" width="128" />
</p>

<h1 align="center"><Project></h1>

<p align="center">
  <strong><One-sentence package tagline.></strong>
</p>

<p align="center">
  <a href="https://github.com/openminion/<package>">GitHub</a>
  · <a href="https://pypi.org/project/<package>/">PyPI</a>
  · <a href="https://www.openminion.com">Website</a>
  · <a href="https://x.com/OpenMinion">X</a>
</p>

<p align="center">
  <a href="https://pypi.org/project/<package>/"><img alt="PyPI" src="https://img.shields.io/pypi/v/<package>?color=3775A9"></a>
  <a href="https://pypi.org/project/<package>/"><img alt="Python" src="https://img.shields.io/pypi/pyversions/<package>"></a>
  <a href="LICENSE"><img alt="License" src="https://img.shields.io/badge/license-Apache--2.0-blue"></a>
  <img alt="Status" src="https://img.shields.io/badge/status-<status-label>-5B8DEF">
</p>

`<package>` is <one concise package definition>. <Optional name-origin or
ownership-boundary sentence, if useful and true.>

## Trust and Brand Safety

- Official GitHub: `https://github.com/openminion/<package>`
- Official PyPI: `https://pypi.org/project/<package>/`
- Official website: `https://www.openminion.com`
- Official X account: `https://x.com/OpenMinion`

`<package>` has no official token, coin, NFT, airdrop, staking program,
treasury product, or investment offering. Any claim otherwise is unauthorized
and should be treated as a scam.

## License and brand-use boundary

- Source code license: `Apache-2.0`
- Brand/trademark grant: `none`

The software license grants rights to use, modify, and redistribute the code.
It does **not** grant rights to use the <Project> or OpenMinion names, logos,
branding, website identity, or social identity except for truthful
attribution. Forks, clones, and derivative distributions must not present
themselves as the official <Project> project or imply affiliation, endorsement,
or maintenance by <Project> or OpenMinion contributors unless that is actually
true.
```

## Badge guidance

1. Use PyPI and Python-version badges for published Python packages.
2. Use the Apache-2.0 license badge when the package ships with the standard
   project license.
3. Keep the status label short. Preferred examples:
   1. `published%20alpha`
   2. `publish--ready%20alpha`
   3. `alpha`
4. Do not add badges for unconfigured CI, unavailable docs, or services the
   package does not actually use.

## Success criteria

1. New package READMEs have a consistent first viewport across GitHub and PyPI.
2. The top block exposes official links before any long package details.
3. Trust and brand-use warnings are present near the top of every public
   package README.
4. Package-specific claims stay accurate instead of copying another package's
   semantics.
