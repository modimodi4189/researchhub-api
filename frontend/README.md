# ResearchHub Frontend

## API Client

Set the FastAPI base URL in `.env.local`:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

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

## Development

```bash
npm run dev
```
