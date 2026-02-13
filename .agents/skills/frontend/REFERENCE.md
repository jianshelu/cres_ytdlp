# Frontend Reference

Extended procedures for the `frontend` skill. Keep `SKILL.md` as the compact rule source.

## 1) Frontend File Map

- App routes: `web/src/app/**/page.tsx`
- Shared UI: `web/src/app/components/*.tsx`
- Route clients: `web/src/app/**/<Name>Client.tsx`
- Styling:
  - global: `web/src/app/globals.css`
  - module-scoped: `web/src/app/*.module.css`
- Frontend API proxies: `web/src/app/api/**/route.ts`

## 2) Server/Client Split

- Use server components when:
  - Reading local files (`data.json`) or server-only env vars
  - Resolving request headers/base URLs
  - Fetching backend data with no client interaction required
- Use client components when:
  - State, filtering, sorting, media controls, or user interaction is required
  - Browser APIs/events are needed

## 3) Data and Media Handling Patterns

- Prefer defensive parsing for `data.json`:
  - Validate array root
  - Normalize optional strings
  - Filter invalid records before rendering
- For media URLs:
  - Normalize malformed protocol forms (`http:/...` -> `http://...`)
  - Preserve path semantics while percent-encoding segments
  - Provide fallback states if media cannot load
- Avoid hard-failing UI on missing thumbnail/transcript/audio:
  - Show clear fallback text
  - Provide open-link fallback where possible

## 4) CSS Change Strategy

- Reuse existing variables (`--background`, `--foreground`, `--accent`, etc.).
- Add scoped class blocks for new UI surfaces.
- Keep responsive behavior explicit with existing breakpoints.
- Avoid global selector side effects that could change unrelated pages.

## 5) Validation Checklist

1. Build:
   - `cd web`
   - `npm run build`
2. Manual route smoke:
   - Home route still renders and links work
   - Changed route renders with empty and non-empty data
   - Media fallback behavior works when source is unavailable
3. Regression check:
   - `/video/[id]` still loads media/transcript
   - `/transcriptions` and `/sentence` still fetch and render

## 6) Rollback Pattern

1. Revert the edited frontend files for the task.
2. Rebuild frontend:
   - `cd web && npm run build`
3. Re-test changed routes and baseline routes.

## 7) Troubleshooting

- Build passes locally but runtime route fails:
  - Check server/client boundary (`use client` placement)
  - Verify fetch URL and request timeout assumptions
- Media not loading:
  - Verify URL normalization and MinIO host mapping logic
  - Open normalized URL directly in browser
- Hydration warnings:
  - Move browser-only logic to client component hooks
  - Avoid non-deterministic values rendered on server and client
