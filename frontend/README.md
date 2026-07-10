# ResearchHub Frontend

## API Client

Create a local env file from the example:

```bash
cp .env.example .env.local
```

Set the FastAPI base URL in `.env.local`:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

Use the backend origin only, without `/health` or `/api/v1` at the end. Restart
`npm run dev` after changing this value because Next.js reads public env values
when the dev server starts.

The API client foundation lives in `lib/api`. It provides:

- `apiFetch<T>()` for typed backend calls.
- Central `ApiError` handling for FastAPI error responses.
- Optional bearer token attachment through `getAccessToken`.
- Shared TypeScript types matching the current FastAPI response schemas.

Smoke-test `/health` from a client or server module:

```ts
import { getHealth } from "@/lib/api";

const health = await getHealth();
// { status: "healthy" }
```

Authenticated calls can attach a token later without auth screens:

```ts
import { apiFetch, type PaperListItem, type PaginationResponse } from "@/lib/api";

const papers = await apiFetch<PaginationResponse<PaperListItem>>(
  "/api/v1/papers",
  {
    getAccessToken: () => localStorage.getItem("access_token"),
    query: { page: 1, limit: 10 },
  },
);
```

## Auth Foundation

The auth routes live at:

- `/login`
- `/register`
- `/app`

The browser token strategy for this stage is intentionally simple:

- Store the access token under `researchhub.accessToken` in `localStorage`.
- Store the refresh token under `researchhub.refreshToken` in `localStorage`.
- Clear both keys on logout or unrecoverable authentication failure.
- Retry authenticated API calls once after a `401` by rotating the refresh token
  through `POST /api/v1/auth/refresh`.

Registration uses `POST /api/v1/auth/register`, then immediately logs in with
the same credentials through `POST /api/v1/auth/login` because the backend
register endpoint returns a user object rather than a token pair.

## Development

```bash
npm run dev
```

With the backend running at `http://localhost:8000`, the app shell shows a small
API status indicator:

- `Loading` while `/health` is being checked.
- `Connected` when `/health` returns `{"status":"healthy"}`.
- `Disconnected` when the request fails or the backend reports another status.
