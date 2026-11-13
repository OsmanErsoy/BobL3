# Seat Classes Plan (Economy, Business, Galaxium)

## Overview

**Goal:** Let passengers book a seat in one of three classes: Economy, Business or Galaxium.

**Confirmed design decisions**
- Each flight has **separate seat inventory per class** (for example 3 Economy, 2 Business, 1 Galaxium).
- `Flight.price` stays as the **base (Economy) price**. Each class applies a **price multiplier** to it (starting values: Economy 1x, Business 2x, Galaxium 4x).
- The multipliers live in **one place in the backend**. The backend returns the computed per-class price in the flight data, so the frontend does not duplicate multiplier logic.
- The class is chosen in the **booking modal**. The flight card shows a "from" price and per-class availability. The total price in the modal updates when the class changes.
- **No migration.** Delete the local `booking.db` and reseed. `seed()` runs at server startup, but `create_all` does not alter existing tables, so the old DB file must be removed.
- Seed data uses a **fixed split of about 60% Economy, 30% Business, 10% Galaxium, with at least 1 Galaxium seat** per flight.

**Current state (from code research)**
- A flight has one `price` and one `seats_available` total ([`models.py`](booking_system_backend/models.py)).
- A booking has no class ([`models.py`](booking_system_backend/models.py), [`services/booking.py`](booking_system_backend/services/booking.py)).
- Nothing in the repo references seat class, cabin or tier.
- The backend is FastAPI + SQLAlchemy + SQLite, with REST and MCP tools both defined in [`server.py`](booking_system_backend/server.py). The frontend is React + TypeScript + Vite with no tests (verification is `npm run build`).

## Open Decisions (need an answer before or during the sub-tasks)

1. **Is `seat_class` required or optional on the booking API and MCP tool?**
   - Tentative default: **optional, defaulting to `economy`**, so existing callers and tests keep working. This question was skipped by the user, so confirm it before sub-task 2.
2. **Seed totals are too small for a fixed split.** Current `seats_available` values are 5, 3, 7, 2, 1, 4, 6, 2, 3, 1. A 60/30/10 split with at least 1 Galaxium seat gives 0 Economy and 0 Business seats on the 1-seat flights.
   - Recommended: raise the seeded totals (for example 10 seats per flight, giving 6 / 3 / 1), so every class has seats.
   - Decide this before sub-task 1.

---

## Sub-Task 1: Backend data model, class constants and seed data

**Intent:** Represent the three classes and their per-class inventory and pricing in the backend, and make the demo data reflect them.

**Expected Outcomes**
- A single definition of the allowed classes and their price multipliers exists in the backend.
- `Flight` stores seat availability per class, and `Booking` stores which class was booked.
- After deleting `booking.db` and starting the server, every flight has seats in each class (per Open Decision 2) and seeded bookings have a class.

**Todo List**
- [x] Define the three class names and their multipliers in one backend location (the constants/helper approach follows existing module style).
- [x] Replace the single `seats_available` column on `Flight` with per-class available-seat columns.
- [x] Add a `seat_class` column to `Booking` (non-null).
- [x] Update `seed.py`: split each flight's seats 60/30/10 with at least 1 Galaxium seat (apply Open Decision 2), and assign a random `seat_class` to each seeded booking.
- [x] Delete the local `booking.db` and confirm the server reseeds on startup.

**Relevant Context**
- [`booking_system_backend/seat_classes.py`](booking_system_backend/seat_classes.py): Created with `SeatClass` enum, `SEAT_CLASSES = ["economy", "business", "galaxium"]`, `DEFAULT_SEAT_CLASS = "economy"`, `SEAT_CLASS_MULTIPLIERS = {"economy": 1, "business": 2, "galaxium": 4}`, and helper `get_seat_class_multiplier(seat_class: str) -> int`.
- [`booking_system_backend/models.py`](booking_system_backend/models.py): `Flight` has `economy_seats_available`, `business_seats_available`, `galaxium_seats_available`. `Booking` has non-null `seat_class`.
- [`booking_system_backend/seed.py`](booking_system_backend/seed.py): All flights seeded with 6 economy, 3 business, 1 galaxium seats (10 total); bookings seeded with random `seat_class`.
- [`booking_system_backend/db.py`](booking_system_backend/db.py): `create_all`, SQLite URL
- `booking.db` is listed in `.gitignore`

**Status:** [x] done

---

## Sub-Task 2: Backend schemas, services, REST and MCP

**Intent:** Make booking, cancelling and flight listing class-aware.

**Expected Outcomes**
- `GET /flights` and the `list_flights` MCP tool return per-class availability and per-class price for each flight.
- Booking takes a `seat_class`, checks availability for that class only, decrements that class, and returns the class on the booking.
- Cancelling a booking returns the seat to the booking's own class.
- An invalid class, or a sold-out class, returns the existing structured `ErrorResponse` style (new error codes for invalid class and class sold out).

**Todo List**
- [x] Update `FlightOut` with per-class seats and per-class prices (computed from base price and multipliers).
- [x] Update `BookingRequest` and `BookingOut` with `seat_class` (validation per Open Decision 1).
- [x] Update `book_flight`: validate the class, check that class's availability, decrement it, store the class on the booking.
- [x] Update `cancel_booking`: increment the seat count for the booking's class.
- [x] Update the `POST /book` REST endpoint and the `book_flight` MCP tool to accept `seat_class`.
- [x] Update tool and endpoint descriptions so MCP clients can discover the allowed classes.

**Relevant Context**
- [`booking_system_backend/schemas.py`](booking_system_backend/schemas.py)
- [`booking_system_backend/services/booking.py`](booking_system_backend/services/booking.py): `book_flight`, `cancel_booking`
- [`booking_system_backend/services/flight.py`](booking_system_backend/services/flight.py): `list_flights`
- [`booking_system_backend/server.py`](booking_system_backend/server.py): `/flights`, `/book`, MCP tools
- Existing error pattern: `ErrorResponse(error, error_code, details)`

**Notes for downstream sub-tasks:**
- **FlightOut JSON Shape:**
```json
{
  "flight_id": 1,
  "origin": "Earth",
  "destination": "Mars",
  "departure_time": "2099-01-01T09:00:00Z",
  "arrival_time": "2099-01-01T17:00:00Z",
  "price": 1000000,
  "seats_available": 10,
  "seats_available_by_class": {
    "economy": 6,
    "business": 3,
    "galaxium": 1
  },
  "prices_by_class": {
    "economy": 1000000,
    "business": 2000000,
    "galaxium": 4000000
  }
}
```
- **BookingRequest JSON Shape:**
```json
{
  "user_id": 1,
  "name": "Alice",
  "flight_id": 1,
  "seat_class": "economy" // optional, defaults to "economy"
}
```
- **BookingOut JSON Shape:**
```json
{
  "booking_id": 1,
  "user_id": 1,
  "flight_id": 1,
  "seat_class": "economy",
  "status": "booked",
  "booking_time": "2026-11-13T10:51:07.193407"
}
```
- **Error Codes:**
  - `INVALID_SEAT_CLASS`: `"The seat class '{seat_class}' is invalid. Allowed seat classes are: economy, business, galaxium."`
  - `NO_SEATS_AVAILABLE`: `"No seats available in {Class} class for flight {flight_id}. Please check other classes or try again later if seats become available."`

**Status:** [x] done

---

## Sub-Task 3: Backend tests

**Intent:** Keep the existing suite green and cover the new behaviour.

**Expected Outcomes**
- Existing tests are updated for the new schema and pass.
- New tests cover per-class booking, per-class pricing, sold-out class, invalid class and cancellation restoring the right class.

**Todo List**
- [x] Update fixtures (the sample flight in `conftest.py` uses `seats_available`) to the per-class columns.
- [x] Update existing service and REST tests that assert on `seats_available` or booking payloads.
- [x] Add tests: book each class; price equals base times multiplier; a sold-out class does not block the other classes; invalid class is rejected; cancel restores the correct class.
- [x] Run `pytest` from `booking_system_backend`.

**Relevant Context**
- [`booking_system_backend/tests/conftest.py`](booking_system_backend/tests/conftest.py): in-memory SQLite, sample fixtures
- [`booking_system_backend/tests/test_services.py`](booking_system_backend/tests/test_services.py)
- [`booking_system_backend/tests/test_rest.py`](booking_system_backend/tests/test_rest.py)

**Notes:**
- `pytest` from `booking_system_backend` (project `.venv`): 61 passed. Only `tests/conftest.py`, `tests/test_services.py` and `tests/test_rest.py` changed; no application code was changed and no bugs were found.
- `conftest.py`: `sample_flight_data` uses the per-class seat columns; `sample_booking_data` includes `seat_class`.
- Test files use small helpers (`add_user_and_flight` / `add_flight`) to create flights with per-class seats; directly created `Booking` objects now set `seat_class`.
- New coverage (services and REST): book each class (parametrized; matching class decremented, others untouched), default economy when omitted (and `None` in the service), case-insensitive class, invalid/empty class -> `INVALID_SEAT_CLASS` with no seat consumed, sold-out class -> `NO_SEATS_AVAILABLE` without blocking other classes, cancel restores the booking's own class (parametrized), `GET /flights` exposes `seats_available`, `seats_available_by_class` and `prices_by_class` (base x multiplier).
- Remaining pytest warnings are pre-existing deprecation warnings in application code (`declarative_base`, class-based pydantic `Config`, `datetime.utcnow`).

**Status:** [x] done

---

## Sub-Task 4: Frontend types and flight card

**Intent:** Show passengers the class options on the flight list without letting them choose yet.

**Expected Outcomes**
- TypeScript types match the new backend responses.
- Each flight card shows a "from" price (the lowest class price) and the available seats per class.
- A card is "Sold Out" only when every class has 0 seats.

**Todo List**
- [x] Add a seat class union type and update `Flight`, `Booking` and `BookingRequest` in the types file.
- [x] Update `FlightCard` price display to "from" price and add per-class availability.
- [x] Update the sold-out logic and the "Book Now" disabled state to use the total across classes.
- [x] Check the `Flights.tsx` search and filter logic for any use of the old `seats_available` field.

**Relevant Context**
- [`booking_system_frontend/src/types/index.ts`](booking_system_frontend/src/types/index.ts)
- [`booking_system_frontend/src/components/flights/FlightCard.tsx`](booking_system_frontend/src/components/flights/FlightCard.tsx): price at about lines 74-80, seats at about lines 83-88
- [`booking_system_frontend/src/pages/Flights.tsx`](booking_system_frontend/src/pages/Flights.tsx)
- [`booking_system_frontend/src/utils/formatters.ts`](booking_system_frontend/src/utils/formatters.ts): `formatCurrency`
- Styling uses Tailwind with the project's design tokens (`cosmic-purple`, `nebula-pink`, `alien-green`, and others).

**Notes for downstream sub-tasks:**
- [`types/index.ts`](booking_system_frontend/src/types/index.ts): added `SeatClass = 'economy' | 'business' | 'galaxium'`; `Flight` now has `seats_available_by_class` and `prices_by_class` (both `Record<SeatClass, number>`; `price` is the base/Economy price and `seats_available` the total); `Booking.seat_class: SeatClass`; `BookingRequest.seat_class?: SeatClass`.
- New helper file [`utils/seatClasses.ts`](booking_system_frontend/src/utils/seatClasses.ts) exports `SEAT_CLASSES` (display order array), `SEAT_CLASS_LABELS` (`Record<SeatClass, string>`: Economy/Business/Galaxium) and `getFromPrice(prices, seats)` (lowest price among classes with seats, else lowest overall). Reuse `SEAT_CLASSES`/`SEAT_CLASS_LABELS` in the modal selector and booking card.
- [`FlightCard.tsx`](booking_system_frontend/src/components/flights/FlightCard.tsx): shows "from {price} per seat", the total seats line, and a 3-column per-class grid ("N left" / "Sold out"). `isSoldOut` still uses `flight.seats_available === 0` (backend total), which disables Book Now.
- `Flights.tsx` only filters by origin/destination/search text; it uses no seat or price fields, so it was not changed.
- Still using `flight.price` (Economy price, no class awareness) and left for Sub-Task 5: `BookingModal.tsx` line ~131 and `BookingCard.tsx` line ~97. They compile; `Booking.seat_class` is typed but not displayed yet.
- Verification: `npm run build` passes (tsc + vite); dev server on 5173 returns 200 and serves `FlightCard.tsx`; `GET /flights` on 8080 returns the new fields.

**Status:** [x] done

---

## Sub-Task 5: Frontend booking modal and booking card

**Intent:** Let the passenger pick a class and see it afterwards.

**Expected Outcomes**
- The booking modal has a class selector. Sold-out classes are disabled, and a default class is preselected.
- The total price in the modal updates when the class changes.
- Booking sends `seat_class` to the backend.
- "My Bookings" shows the class and the price for that class on each booking.

**Todo List**
- [x] Add a class selector to `BookingModal` using the per-class prices and availability from the flight data.
- [x] Update the Total Price display to use the selected class's price.
- [x] Pass `seat_class` in the `bookFlight` request. `api.ts` passes the payload through, so it should need no change.
- [x] Update `BookingCard` to show the booking's class and the matching price.
- [x] Run `npm run build` in `booking_system_frontend` to type-check.

**Relevant Context**
- [`booking_system_frontend/src/components/bookings/BookingModal.tsx`](booking_system_frontend/src/components/bookings/BookingModal.tsx): price summary at about lines 125-133
- [`booking_system_frontend/src/components/bookings/BookingCard.tsx`](booking_system_frontend/src/components/bookings/BookingCard.tsx): price at about lines 94-99
- [`booking_system_frontend/src/pages/MyBookings.tsx`](booking_system_frontend/src/pages/MyBookings.tsx): joins bookings with flights
- [`booking_system_frontend/src/services/api.ts`](booking_system_frontend/src/services/api.ts)

**Notes:**
- [`BookingModal.tsx`](booking_system_frontend/src/components/bookings/BookingModal.tsx): added a radio-group class selector (`<fieldset>` with visually hidden native radios inside styled labels, so keyboard and screen readers work). Each option shows the class label, `prices_by_class[c]` and "N left" / "Sold out"; sold-out radios are `disabled`. The default is the cheapest class with seats (`getDefaultSeatClass`); if every class is sold out, nothing is selected, Total Price shows "—" and Confirm Booking is disabled. Selection state is reset via `useEffect` on `[isOpen, flight?.flight_id]`, and the effective class falls back to the default if the stored choice is missing or sold out. Total Price uses `prices_by_class[seatClass]`, and `bookFlight` sends `seat_class`.
- [`BookingCard.tsx`](booking_system_frontend/src/components/bookings/BookingCard.tsx): new "Class" row (label from `SEAT_CLASS_LABELS`, falls back to the raw value) and the Price row now uses `flight.prices_by_class[booking.seat_class]`, showing "—" if the class price is missing. When the flight is not found, the card also shows the class. `MyBookings.tsx` needed no change (it already passes the joined flight and reloads bookings and flights after cancel).
- `services/api.ts` unchanged (`bookFlight` posts the `BookingRequest` as is). `Flights.tsx` unchanged: `handleBookingSuccess` already calls `loadFlights()`, so per-class counts refresh after booking.
- Verification: `npm run build` passes. Live backend via curl on flight 1 (Alice, user 1): booked business (#21) and galaxium (#22); `GET /bookings/1` returned the right `seat_class` for each; `GET /flights` went from 6/3/1 to 6/2/0 (total 10 to 8); `POST /cancel` on both restored 6/3/1. The two bookings remain in the DB with status `cancelled`. The UI itself was not exercised in a browser.

**Status:** [x] done

---

## Sub-Task 6: Documentation and end-to-end check

**Intent:** Keep the docs accurate and verify the whole flow.

**Expected Outcomes**
- READMEs describe the classes, the multipliers and the new `seat_class` field.
- A manual end-to-end run works: book each class, see the class and price in "My Bookings", cancel, and see the seat count restored.

**Todo List**
- [x] Update the root README (demo data section), the backend README (endpoints and MCP tools) and the frontend README where they describe booking or flights.
- [x] Reset `booking.db`, start both apps (see `start.sh`), and run through the flow by hand.
- [x] Run `pytest` and `npm run build` one final time.

**Relevant Context**
- [`README.md`](README.md), [`booking_system_backend/README.md`](booking_system_backend/README.md), [`booking_system_frontend/README.md`](booking_system_frontend/README.md)
- [`start.sh`](start.sh)

**Notes:**
- Root README: added a Seat Classes feature bullet, a "Choose a Class" step in the user guide, a multiplier table, and updated Demo Data (6/3/1 split, bookings with classes).
- Backend README: endpoint/MCP descriptions, a Seat Classes section (multipliers, optional `seat_class` defaulting to `economy`, `INVALID_SEAT_CLASS` / `NO_SEATS_AVAILABLE`, FlightOut and BookingOut examples), curl/MCP examples, `seat_classes.py` in the project structure, a Data Model section, and updated seeded data. Also removed a stray `doc` line in the Demo Data section.
- Frontend README: Seat Classes feature, `utils/seatClasses.ts` in the structure, API notes, and the booking/manage user flows (class selector, class and price on My Bookings).
- Live end-to-end check (curl, Alice user 1, flight 1): for economy/business/galaxium, `POST /book` -> `GET /bookings/1` showed the right class -> `GET /flights` decremented only that class (prices 1,000,000 / 2,000,000 / 4,000,000) -> `POST /cancel` restored 6/3/1. A second galaxium booking returned `NO_SEATS_AVAILABLE` while economy still booked; `seat_class: "first"` returned `INVALID_SEAT_CLASS`; omitting `seat_class` booked economy. All created bookings were cancelled.
- Reseeded afterwards: backend stopped, `booking.db` deleted, restarted with `.venv/bin/python server.py` on 127.0.0.1:8080; `GET /flights` shows 6/3/1 (total 10) for all 10 flights. The Vite dev server on 5173 was left running.
- Final checks: `python -m pytest -q` -> 61 passed; `npm run build` -> passes.
- Pre-existing, not changed: the live REST routes have no `/api` prefix (`/flights`, `/book`, ...), although the backend README documents `/api/*` and `/api/flights` returns 404.

**Status:** [x] done
