import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from models import User, Flight, Booking
from seat_classes import SEAT_CLASSES, SEAT_CLASS_MULTIPLIERS


def add_flight(db_session, economy=3, business=1, galaxium=1, price=1000000):
    """Add a flight with the given per-class seats and return it."""
    db_session.add(Flight(
        origin="Earth",
        destination="Mars",
        departure_time="2099-01-01T09:00:00Z",
        arrival_time="2099-01-01T17:00:00Z",
        price=price,
        economy_seats_available=economy,
        business_seats_available=business,
        galaxium_seats_available=galaxium
    ))
    db_session.commit()
    return db_session.query(Flight).first()


class TestFlightsEndpoint:
    """Test /flights endpoint."""

    def test_get_flights_empty(self, client, db_session):
        """Test getting flights when database is empty."""
        response = client.get("/flights")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_flights_with_data(self, client, db_session):
        """Test getting flights with data."""
        add_flight(db_session)

        response = client.get("/flights")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["origin"] == "Earth"
        assert data[0]["destination"] == "Mars"

    def test_get_flights_exposes_seats_by_class(self, client, db_session):
        """Test /flights returns total and per-class seat availability."""
        add_flight(db_session, economy=6, business=3, galaxium=1)

        data = client.get("/flights").json()
        assert data[0]["seats_available"] == 10
        assert data[0]["seats_available_by_class"] == {
            "economy": 6,
            "business": 3,
            "galaxium": 1,
        }

    def test_get_flights_exposes_prices_by_class(self, client, db_session):
        """Test /flights returns per-class prices computed from the base price."""
        add_flight(db_session, price=1000000)

        data = client.get("/flights").json()
        assert data[0]["price"] == 1000000
        assert data[0]["prices_by_class"] == {
            "economy": 1000000,
            "business": 2000000,
            "galaxium": 4000000,
        }
        for seat_class in SEAT_CLASSES:
            assert data[0]["prices_by_class"][seat_class] == 1000000 * SEAT_CLASS_MULTIPLIERS[seat_class]


class TestRegisterEndpoint:
    """Test /register endpoint."""

    def test_register_success(self, client, db_session, sample_user_data):
        """Test successful user registration."""
        response = client.post("/register", json=sample_user_data)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == sample_user_data["name"]
        assert data["email"] == sample_user_data["email"]
        assert "user_id" in data

    def test_register_duplicate_email(self, client, db_session, sample_user_data):
        """Test registration with duplicate email."""
        client.post("/register", json=sample_user_data)
        response = client.post("/register", json=sample_user_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] == False
        assert data["error_code"] == "EMAIL_EXISTS"


class TestUserEndpoint:
    """Test /user endpoint."""

    def test_get_user_success(self, client, db_session, sample_user_data):
        """Test successful user retrieval."""
        client.post("/register", json=sample_user_data)

        response = client.get(
            "/user",
            params={"name": sample_user_data["name"], "email": sample_user_data["email"]}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == sample_user_data["name"]

    def test_get_user_not_found(self, client, db_session):
        """Test user retrieval when not found."""
        response = client.get(
            "/user",
            params={"name": "NonExistent", "email": "none@example.com"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == False
        assert data["error_code"] == "USER_NOT_FOUND"


class TestBookEndpoint:
    """Test /book endpoint."""

    def test_book_flight_success(self, client, db_session, sample_user_data):
        """Test successful flight booking."""
        # Register user
        user_response = client.post("/register", json=sample_user_data)
        user_id = user_response.json()["user_id"]

        # Create flight
        flight = add_flight(db_session)

        # Book flight
        response = client.post("/book", json={
            "user_id": user_id,
            "name": sample_user_data["name"],
            "flight_id": flight.flight_id
        })

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "booked"
        assert data["user_id"] == user_id

    def test_book_flight_not_found(self, client, db_session, sample_user_data):
        """Test booking non-existent flight."""
        user_response = client.post("/register", json=sample_user_data)
        user_id = user_response.json()["user_id"]

        response = client.post("/book", json={
            "user_id": user_id,
            "name": sample_user_data["name"],
            "flight_id": 999
        })

        assert response.status_code == 200
        data = response.json()
        assert data["success"] == False
        assert data["error_code"] == "FLIGHT_NOT_FOUND"

    @pytest.mark.parametrize("seat_class", SEAT_CLASSES)
    def test_book_flight_each_class(self, client, db_session, sample_user_data, seat_class):
        """Test booking each class returns the class and decrements only that class."""
        user_id = client.post("/register", json=sample_user_data).json()["user_id"]
        flight = add_flight(db_session, economy=3, business=2, galaxium=1)

        response = client.post("/book", json={
            "user_id": user_id,
            "name": sample_user_data["name"],
            "flight_id": flight.flight_id,
            "seat_class": seat_class
        })
        assert response.status_code == 200
        assert response.json()["seat_class"] == seat_class

        by_class = client.get("/flights").json()[0]["seats_available_by_class"]
        initial = {"economy": 3, "business": 2, "galaxium": 1}
        for cls_name in SEAT_CLASSES:
            expected = initial[cls_name] - 1 if cls_name == seat_class else initial[cls_name]
            assert by_class[cls_name] == expected

    def test_book_flight_default_class_is_economy(self, client, db_session, sample_user_data):
        """Test omitting seat_class books economy."""
        user_id = client.post("/register", json=sample_user_data).json()["user_id"]
        flight = add_flight(db_session, economy=3, business=2, galaxium=1)

        response = client.post("/book", json={
            "user_id": user_id,
            "name": sample_user_data["name"],
            "flight_id": flight.flight_id
        })
        assert response.status_code == 200
        assert response.json()["seat_class"] == "economy"

        by_class = client.get("/flights").json()[0]["seats_available_by_class"]
        assert by_class == {"economy": 2, "business": 2, "galaxium": 1}

    def test_book_flight_invalid_class(self, client, db_session, sample_user_data):
        """Test an invalid seat class returns INVALID_SEAT_CLASS."""
        user_id = client.post("/register", json=sample_user_data).json()["user_id"]
        flight = add_flight(db_session)

        response = client.post("/book", json={
            "user_id": user_id,
            "name": sample_user_data["name"],
            "flight_id": flight.flight_id,
            "seat_class": "first_class"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == False
        assert data["error_code"] == "INVALID_SEAT_CLASS"

    def test_book_flight_sold_out_class(self, client, db_session, sample_user_data):
        """Test a sold-out class returns NO_SEATS_AVAILABLE while others stay bookable."""
        user_id = client.post("/register", json=sample_user_data).json()["user_id"]
        flight = add_flight(db_session, economy=2, business=1, galaxium=0)

        sold_out = client.post("/book", json={
            "user_id": user_id,
            "name": sample_user_data["name"],
            "flight_id": flight.flight_id,
            "seat_class": "galaxium"
        })
        data = sold_out.json()
        assert data["success"] == False
        assert data["error_code"] == "NO_SEATS_AVAILABLE"

        other = client.post("/book", json={
            "user_id": user_id,
            "name": sample_user_data["name"],
            "flight_id": flight.flight_id,
            "seat_class": "business"
        })
        assert other.json()["status"] == "booked"
        assert other.json()["seat_class"] == "business"


class TestBookingsEndpoint:
    """Test /bookings/{user_id} endpoint."""

    def test_get_bookings_success(self, client, db_session, sample_user_data):
        """Test getting user bookings."""
        # Register user
        user_response = client.post("/register", json=sample_user_data)
        user_id = user_response.json()["user_id"]

        # Create flight and booking
        flight = add_flight(db_session)

        db_session.add(Booking(
            user_id=user_id,
            flight_id=flight.flight_id,
            seat_class="galaxium",
            status="booked",
            booking_time="2099-01-01T10:00:00Z"
        ))
        db_session.commit()

        response = client.get(f"/bookings/{user_id}")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["status"] == "booked"
        assert data[0]["seat_class"] == "galaxium"

    def test_get_bookings_empty(self, client, db_session):
        """Test getting bookings when user has none."""
        response = client.get("/bookings/999")
        assert response.status_code == 200
        assert response.json() == []


class TestCancelEndpoint:
    """Test /cancel/{booking_id} endpoint."""

    def test_cancel_booking_success(self, client, db_session, sample_user_data):
        """Test successful booking cancellation."""
        # Register user
        user_response = client.post("/register", json=sample_user_data)
        user_id = user_response.json()["user_id"]

        # Create flight and booking
        flight = add_flight(db_session, economy=2, business=1, galaxium=1)

        db_session.add(Booking(
            user_id=user_id,
            flight_id=flight.flight_id,
            seat_class="economy",
            status="booked",
            booking_time="2099-01-01T10:00:00Z"
        ))
        db_session.commit()
        booking = db_session.query(Booking).first()

        response = client.post(f"/cancel/{booking.booking_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"

    @pytest.mark.parametrize("seat_class", SEAT_CLASSES)
    def test_cancel_booking_restores_correct_class(self, client, db_session, sample_user_data, seat_class):
        """Test cancelling via REST restores the seat to the booking's class."""
        user_id = client.post("/register", json=sample_user_data).json()["user_id"]
        flight = add_flight(db_session, economy=3, business=2, galaxium=1)
        initial = {"economy": 3, "business": 2, "galaxium": 1}

        booked = client.post("/book", json={
            "user_id": user_id,
            "name": sample_user_data["name"],
            "flight_id": flight.flight_id,
            "seat_class": seat_class
        }).json()

        cancelled = client.post(f"/cancel/{booked['booking_id']}").json()
        assert cancelled["status"] == "cancelled"
        assert cancelled["seat_class"] == seat_class

        by_class = client.get("/flights").json()[0]["seats_available_by_class"]
        assert by_class == initial

    def test_cancel_booking_not_found(self, client, db_session):
        """Test cancelling non-existent booking."""
        response = client.post("/cancel/999")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == False
        assert data["error_code"] == "BOOKING_NOT_FOUND"


class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_check(self, client, db_session):
        """Test health check returns OK."""
        response = client.get("/")
        assert response.status_code == 200
        assert response.json() == {"status": "OK"}
