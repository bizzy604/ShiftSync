# ShiftSync Web App (`apps/web`)

React + TypeScript single-page application for ShiftSync users.

## Stack
- React 18
- TypeScript
- Vite
- TanStack Query
- React Router

## Run
```bash
npm --workspace apps/web install
npm --workspace apps/web run dev
```

## Build
```bash
npm --workspace apps/web run build
npm --workspace apps/web run preview
```

## Environment
- `VITE_API_BASE_URL`: backend API base (for example `http://localhost:8000/api/v1`).

## Extend
1. Add pages in `src/pages/<role>/`.
2. Add shared components in `src/components/`.
3. Add API contracts in `src/lib/api/types.ts` and hooks in `src/lib/api/hooks.ts`.
4. Keep role-based navigation aligned with `src/main.tsx` route guards.
