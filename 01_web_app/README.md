# Module 01: Web App

## Status

**Active in the website request flow.** This is a Next.js 16.3.8 App Router app with a Thai-language build form and recommendation results.

## What works

- Collects budget, use case, preferred CPU/GPU brand, existing parts, socket, and optional PSU wattage.
- Validates and normalizes form data in `lib/schema.ts` before submission.
- Calls Module 02, keeps a conversation ID for follow-up requests, and supports request cancellation and idempotency keys.
- Shows compatibility status, conflicts, incomplete-service warnings, product links, and unknown prices/stock without converting missing values to zero.

## Run and verify

```powershell
npm ci
npm run dev
```

Open `http://localhost:3000`. `NEXT_PUBLIC_API_BASE_URL` defaults to `http://localhost:8000` and can be overridden in `.env.local`.

```powershell
npm run build
npm audit
```

There is no automated browser/UI test suite yet. The production build and type check currently pass; npm audit reports no advisories for the locked dependencies.

## Remaining work

- Add browser-level tests for form validation, retry/error states, and partial results.
- Add clearer input for other compatibility-critical specifications as real catalog data becomes available.
- Replace the development-token flow through a production identity provider when deploying publicly.