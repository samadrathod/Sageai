---
name: Gemini API Key Setup (Direct Key)
description: This project uses GEMINI_API_KEY directly, bypassing the AI integrations proxy
---

# Gemini Direct API Key

**Why:** User provided their own GEMINI_API_KEY secret. The standard lib/integrations-gemini-ai template requires AI_INTEGRATIONS_GEMINI_BASE_URL (Replit proxy), which is not configured.

**How to apply:**
- Both `lib/integrations-gemini-ai/src/client.ts` and `lib/integrations-gemini-ai/src/image/client.ts` check `GEMINI_API_KEY || AI_INTEGRATIONS_GEMINI_API_KEY`
- `AI_INTEGRATIONS_GEMINI_BASE_URL` is optional — if not set, no httpOptions.baseUrl is passed (uses Google's default endpoint)
- The `@google/genai` package must NOT be in the `external` array of `artifacts/api-server/build.mjs` — it was removed from the `@google/*` glob to allow bundling
