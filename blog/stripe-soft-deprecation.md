# Stripe doesn't mark /v1/charges as deprecated — here's why that matters

I ran a scanner across a codebase last week and found a call to `stripe.Charge.create`. Stripe's own documentation says the endpoint is "no longer recommended — use the Payment Intents API to initiate a new payment instead."

But their OpenAPI spec does not mark it `deprecated: true`.

That means every tool that checks the spec thinks this endpoint is fine. It isn't.

## Why this happens

API deprecations are communicated in two ways:

1. **Machine-readable.** The OpenAPI spec sets `deprecated: true` on the operation or path. This is easy to detect and most tooling looks for it.
2. **In prose.** The operation's description field contains a sentence like "no longer recommended" or "use X instead." This is the way most real deprecations are actually announced, and almost nothing detects it.

Stripe uses the second form for `/v1/charges`. Twilio does the same for several endpoints. So does AWS in parts of its SDK documentation.

## Why it matters

A deprecated endpoint still works today. It will not work forever. When the provider sunsets it, every call site breaks at once — usually in production, usually on a Tuesday, usually without warning.

The cost of finding and migrating one call site today is trivial. The cost of finding all of them across a service during an incident is not.

The gap is not that teams don't care. It's that the standard tooling they trust — dependency checkers, OpenAPI diff tools, CI scanners — is looking at a flag the provider didn't set.

## What detection looks like

A scanner that covers both cases checks the OpenAPI spec for the boolean flag, and separately checks the description field for known deprecation phrases. When it finds a prose match, it emits the finding with a distinct label so the user can tell the difference between "the spec formally deprecated this" and "the docs say don't use it."

Example finding:

```
SOFT_DEPRECATION: test.py:2 - stripe.Charge.create -> https://api.stripe.com/v1/charges
Context: "This method is no longer recommended."
Spec version: 2026-08-26.dahlia
```

## What I built

[DeprecateGuard](https://github.com/marketplace/actions/deprecateguard-scanner) is a GitHub Action that scans Python, TypeScript, and Go repos for calls to deprecated Stripe and Twilio endpoints. It detects both the OpenAPI `deprecated: true` flag and the prose "no longer recommended" class of deprecation, and it labels them separately so the difference is visible.

It runs entirely inside the user's GitHub Actions runner. No source code leaves the repository.

Install is three lines of YAML:

```yaml
- uses: rajj55/deprecateguard-action@v1
  with:
    github_token: ${{ secrets.GITHUB_TOKEN }}
```

If you've run into this same gap — deprecations that no standard tool catches — I'd be interested to hear about it. It seems to be more common than the tooling assumes.
