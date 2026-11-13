# AGENTS.md

This file provides guidance to agents when working with code in this repository.

## Commands
- Run everything: `./start.sh` (backend :8080, frontend :5173). Backend alone: `.venv/bin/python server.py` from `booking_system_backend/`.
- Backend tests MUST run from `booking_system_backend/` (`pytest.ini` + `conftest.py` rely on that cwd). Tests are grouped in classes. Single test: `.venv/bin/python -m pytest "tests/test_services.py::TestBookingService::test_name" -q`, or filter with `-k cancel`.
- Frontend: `npm run build` (`tsc -b && vite build`) is the only type-check; there are no frontend tests. `npm run lint` is ESLint.

## Backend gotchas (`booking_system_backend/`)
- `seed()` runs on every server startup (`lifespan` in `server.py`) and deletes all users, flights and bookings. Data does not persist across restarts.
- `create_all` never alters existing tables. After changing `models.py`, delete `booking.db` (gitignored) or the server returns 500s.
- Business errors are returned as `ErrorResponse` objects with HTTP 200, not raised or sent as 4xx. The MCP tools in `server.py` do the opposite and raise `Exception`. Follow the `ErrorResponse(error, error_code, details)` pattern in `services/`.
- REST routes have no prefix (`/flights`, `/book`, `/cancel/{id}`). The backend README documents `/api/...`, which is wrong.
- REST routes and MCP tools in `server.py` are parallel definitions of the same operations. Change both together. The MCP app is mounted at `/mcp`.
- Seat classes: `seat_classes.py` is the single source of truth (economy 1x, business 2x, galaxium 4x of `Flight.price`). Per-class prices are computed in `schemas.FlightOut`, never stored. `Flight.seats_available` no longer exists as a column; `FlightOut.seats_available` is the sum of the three `*_seats_available` columns.
- Tests use in-memory SQLite and monkeypatch `server.SessionLocal` and `server.seed` (see `tests/conftest.py`). New tests must use those fixtures, not `booking.db`.

## Frontend gotchas (`booking_system_frontend/`)
- API errors do not arrive as thrown `AxiosError`s: the interceptor in `src/services/api.ts` rejects with the backend's `ErrorResponse` body (or a synthetic `NETWORK_ERROR`). A successful call can also resolve to an `ErrorResponse`; check it with `isErrorResponse()`.
- Class labels, order and the "from" price helper live in `src/utils/seatClasses.ts`. Use them instead of hardcoding class names. Prices come from `flight.prices_by_class`, never `flight.price` (that is the Economy base price).
- Money is formatted with `formatCurrency` in `src/utils/formatters.ts` (USD, no decimals).

## Style
- Frontend `.ts`/`.tsx` files and most backend modules end with a `// Made with Bob` footer comment; keep it where present. `services/*.py` do not have it.
- Python uses plain `Session` functions in `services/` (no classes) and Pydantic `*Out` schemas in `schemas.py`.

## Project Level Rules
- Always include concise JSDoc strings for every public function.
- Be very concise in your wording.
- Write a summary of every interaction into the folder `internal-monologue/`. Name the file starting with a timestamp, followed by a concise description of the interaction. Example: 2026-01-15_update-readme.md
