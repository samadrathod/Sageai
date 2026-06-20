---
name: esbuild externals — @google/* pattern
description: The api-server build.mjs had @google/* externalized which blocked @google/genai bundling
---

# esbuild Externals Fix

**Why:** `artifacts/api-server/build.mjs` had `"@google/*"` in the external array, which caused `@google/genai` to be externalized (not bundled). At runtime Node couldn't find it because it's a workspace dependency, not installed as a standalone node_module in the right location.

**Fix applied:** Removed `"@google/*"` from the externals list in `build.mjs`. `@google-cloud/*` and `googleapis` remain external (they have their own native bindings that shouldn't be bundled).

**How to apply:** If a new `@google/` package is added to api-server, verify it bundles correctly. Only externalize packages that have native addons or are too large / have dynamic require patterns that break esbuild.
