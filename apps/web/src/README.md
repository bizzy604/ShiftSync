# Web Source Guide (`apps/web/src`)

This folder contains all frontend application logic.

## Layout
- `auth/`: authentication context and protected-route helpers.
- `components/`: reusable UI building blocks and providers.
- `lib/api/`: API client, types, and React Query hooks.
- `pages/`: role-based screens (`admin`, `manager`, `staff`, `common`).
- `styles.css`: global styling entry.

## Maintainability Rules
- Keep API side effects in `lib/api/hooks.ts` to centralize cache invalidation.
- Keep route-level composition in `main.tsx`; avoid business logic there.
- Keep pages orchestration-focused and delegate reusable UI to `components/`.
- Prefer strongly typed API contracts in `lib/api/types.ts`.

## When Adding Features
1. Add/extend API client functions and response types first.
2. Add/extend query/mutation hooks with invalidation strategy.
3. Compose UI in page components using those hooks.
4. Update README files if folder responsibilities change.
