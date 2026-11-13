# Galaxium Booking System

A unified booking system for Galaxium Travels that serves both **REST API** and **MCP (Model Context Protocol)** from a single server.

## Features

- **Dual Protocol Support**: Same business logic exposed via REST and MCP
- **Single Server**: One codebase, one port, both protocols
- **SQLite Database**: Simple file-based storage for demos
- **Seat Classes**: Economy, Business and Galaxium, each with its own seat inventory and price
- **Demo Data**: Pre-seeded with space travel flights and users

## Quick Start

### Install Dependencies

```bash
cd booking_system
pip install -r requirements.txt
```

### Run the Server

```bash
python server.py
```

The server starts on port **8080** with:
- REST endpoints at `/api/*`
- MCP tools at `/mcp`
- Health check at `/`

## API Reference

### REST Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/flights` | List all available flights with per-class seats and prices |
| POST | `/api/book` | Book a flight (optional `seat_class`) |
| GET | `/api/bookings/{user_id}` | Get user's bookings |
| POST | `/api/cancel/{booking_id}` | Cancel a booking |
| POST | `/api/register` | Register a new user |
| GET | `/api/user?name=...&email=...` | Get user by name and email |

### MCP Tools

| Tool | Description |
|------|-------------|
| `list_flights` | List all available flights with per-class seats and prices |
| `book_flight` | Book a seat on a flight (optional `seat_class`: `economy`, `business`, `galaxium`) |
| `get_bookings` | Get user's bookings |
| `cancel_booking` | Cancel a booking |
| `register_user` | Register a new user |
| `get_user_id` | Get user by name and email |

## Seat Classes

Each flight has separate seat inventory per class. `Flight.price` is the base (Economy) price; the price of a class is the base price times its multiplier. The classes and multipliers are defined in `seat_classes.py`.

| Class | Multiplier |
|-------|------------|
| `economy` | 1x |
| `business` | 2x |
| `galaxium` | 4x |

- `seat_class` is optional on `POST /api/book` and the `book_flight` MCP tool, and defaults to `economy`. Values are case-insensitive.
- Booking decrements only the chosen class; a sold-out class does not block the other classes.
- Cancelling a booking returns the seat to the booking's own class.

Errors use the standard `ErrorResponse` shape (`error`, `error_code`, `details`):

| `error_code` | When |
|--------------|------|
| `INVALID_SEAT_CLASS` | `seat_class` is not one of `economy`, `business`, `galaxium` |
| `NO_SEATS_AVAILABLE` | The requested class has no seats left on that flight |

### Response shapes

`GET /api/flights` (each flight). `price` is the base (Economy) price and `seats_available` is the total across classes:

```json
{
  "flight_id": 1,
  "origin": "Earth",
  "destination": "Mars",
  "departure_time": "2099-01-01T09:00:00Z",
  "arrival_time": "2099-01-01T17:00:00Z",
  "price": 1000000,
  "seats_available": 10,
  "seats_available_by_class": {"economy": 6, "business": 3, "galaxium": 1},
  "prices_by_class": {"economy": 1000000, "business": 2000000, "galaxium": 4000000}
}
```

`POST /api/book` and `GET /api/bookings/{user_id}` (each booking):

```json
{
  "booking_id": 1,
  "user_id": 1,
  "flight_id": 1,
  "seat_class": "business",
  "status": "booked",
  "booking_time": "2026-11-13T10:51:07.193407"
}
```

## Usage Examples

### REST API

```bash
# List flights
curl http://localhost:8080/api/flights

# Register a user
curl -X POST http://localhost:8080/api/register \
  -H "Content-Type: application/json" \
  -d '{"name": "John Doe", "email": "john@example.com"}'

# Book a flight (seat_class is optional and defaults to economy)
curl -X POST http://localhost:8080/api/book \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1, "name": "Alice", "flight_id": 1}'

# Book a Business seat
curl -X POST http://localhost:8080/api/book \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1, "name": "Alice", "flight_id": 1, "seat_class": "business"}'

# Get bookings
curl http://localhost:8080/api/bookings/1

# Cancel a booking
curl -X POST http://localhost:8080/api/cancel/1
```

### MCP (with Claude Code or MCP Inspector)

Connect to `http://localhost:8080/mcp` and use the available tools:

```
list_flights()
register_user(name="John Doe", email="john@example.com")
book_flight(user_id=1, name="Alice", flight_id=1)
book_flight(user_id=1, name="Alice", flight_id=1, seat_class="galaxium")
get_bookings(user_id=1)
cancel_booking(booking_id=1)
```

## Testing

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_services.py
pytest tests/test_rest.py
```

## Project Structure

```
booking_system/
├── server.py          # Main server - exposes REST & MCP
├── services/          # Business logic layer
│   ├── booking.py     # Booking operations
│   ├── flight.py      # Flight operations
│   └── user.py        # User operations
├── models.py          # SQLAlchemy ORM models
├── seat_classes.py    # Seat class names and price multipliers
├── schemas.py         # Pydantic request/response schemas
├── db.py              # Database configuration
├── seed.py            # Demo data seeding
├── tests/             # Test suite
│   ├── test_services.py
│   └── test_rest.py
├── requirements.txt
├── Dockerfile
└── pytest.ini
```

## Demo Data

The server seeds the database with:
- **10 users**: Alice, Bob, Charlie, Diana, Eve, Frank, Grace, Heidi, Ivan, Judy
- **10 flights**: Interplanetary routes (Earth, Mars, Moon, Venus, Jupiter, Europa, Pluto), each with 10 seats split 6 Economy / 3 Business / 1 Galaxium
- **20 bookings**: Random bookings across users and flights, each with a random seat class

## Data Model

- `User`: `user_id`, `name`, `email`
- `Flight`: `flight_id`, `origin`, `destination`, `departure_time`, `arrival_time`, `price` (base/Economy price), `economy_seats_available`, `business_seats_available`, `galaxium_seats_available`
- `Booking`: `booking_id`, `user_id`, `flight_id`, `seat_class`, `status`, `booking_time`

There is no migration: `create_all` does not alter existing tables, so after a schema change delete `booking.db` and restart the server to reseed.

## Docker

```bash
# Build
docker build -t galaxium-booking .

# Run
docker run -p 8080:8080 galaxium-booking
```

## Architecture

The system uses a **service layer** pattern:

1. **Services** (`services/`) - Pure business logic functions
2. **Server** (`server.py`) - Thin wrappers exposing services via REST and MCP
3. **Models** (`models.py`) - SQLAlchemy ORM definitions
4. **Schemas** (`schemas.py`) - Pydantic validation schemas

This architecture ensures:
- Business logic is tested independently of transport layer
- Same validation and error handling for both REST and MCP
- Easy to add new transport layers (GraphQL, gRPC, etc.)
