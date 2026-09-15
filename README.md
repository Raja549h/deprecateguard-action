# DeprecateGuard Scanner

A zero-exfiltration GitHub Action that detects deprecated API calls in your codebase before they break production.

## Install

Add to any workflow (e.g. `.github/workflows/deprecateguard.yml`):

```yaml
- uses: rajj55/deprecateguard-action@v1
  with:
    github_token: ${{ secrets.GITHUB_TOKEN }}
```

## What It Detects

| Type | Description |
|---|---|
| **Hard deprecations** | Endpoints marked `deprecated: true` in the provider's OpenAPI spec |
| **Soft deprecations** | Endpoints the provider's documentation says are "no longer recommended" |

**Providers:** Stripe, Twilio

**Languages:** Python, TypeScript/JavaScript, Go

*Note: Languages like Rust, Java, C#, and Ruby are NOT currently supported.*

## Zero-Exfiltration Design

DeprecateGuard runs **entirely inside your GitHub Actions runner**. No source code leaves your repository. The scanner parses your code locally, checks it against bundled OpenAPI specs, and posts findings as PR comments — all within your own infrastructure.

## Telemetry & Accuracy

Live accuracy dashboard: [deprecateguard-status](https://rajj55.github.io/deprecateguard-status/)

Report false positives or missed detections via [deprecateguard-telemetry](https://github.com/rajj55/deprecateguard-telemetry/issues).

## Modes

- **`pr-comment`** (default): Scans changed files on pull requests and posts inline comments.
- **`scheduled-audit`**: Full repo scan, creates/updates a tracking issue with all findings.

## License

MIT
