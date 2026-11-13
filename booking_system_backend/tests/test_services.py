import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from models import User, Flight, Booking
from schemas import ErrorResponse, FlightOut
from seat_classes import SEAT_CLASSES, SEAT_CLASS_MULTIPLIERS
from services import flight, user, booking


def add_user_and_flight(db_session, economy=3, business=1, galaxium=1, price=1000000):
    """Add a user and a flight with the given per-class seats; return both."""
    db_session.add(User(name="Test User", email="test@example.com"))
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
    return db_session.query(User).first(), db_session.query(Flight).first()


def seats_by_class(flight_obj):
    """Return the per-class seat counts of a flight as a dict."""
    return {
        "economy": flight_obj.economy_seats_available,
        "business": flight_obj.business_seats_available,
        "galaxium": flight_obj.galaxium_seats_available,
    }


class TestFlightService:
    """Test flight service functions."""

    def test_list_flights_empty(self, db_session):
        """Test listing flights when database is empty."""
        result = flight.list_flights(db_session)
        assert result == []

    def test_list_flights_with_data(self, db_session):
        """Test listing flights with data in database."""
        db_session.add(Flight(
            origin="Earth",
            destination="Mars",
            departure_time="2099-01-01T09:00:00Z",
            arrival_time="2099-01-01T17:00:00Z",
            price=1000000,
            economy_seats_available=3,
            business_seats_available=1,
            galaxium_seats_available=1
        ))
        db_session.commit()

        result = flight.list_flights(db_session)
        assert len(result) == 1
        assert result[0].origin == "Earth"
        assert result[0].destination == "Mars"

    def test_list_flights_exposes_seats_by_class(self, db_session):
        """Test flight listing returns total and per-class seat availability."""
        add_user_and_flight(db_session, economy=6, business=3, galaxium=1)

        result = flight.list_flights(db_session)
        assert result[0].seats_available == 10
        assert result[0].seats_available_by_class == {
            "economy": 6,
            "business": 3,
            "galaxium": 1,
        }

    @pytest.mark.parametrize("seat_class", SEAT_CLASSES)
    def test_list_flights_price_by_class(self, db_session, seat_class):
        """Test per-class price equals base price times the class multiplier."""
        add_user_and_flight(db_session, price=1000000)

        result = flight.list_flights(db_session)
        assert result[0].price == 1000000
        assert result[0].prices_by_class[seat_class] == 1000000 * SEAT_CLASS_MULTIPLIERS[seat_class]

    def test_list_flights_prices_by_class_values(self, db_session):
        """Test the concrete multipliers: economy 1x, business 2x, galaxium 4x."""
        add_user_and_flight(db_session, price=1000000)

        result = flight.list_flights(db_session)
        assert result[0].prices_by_class == {
            "economy": 1000000,
            "business": 2000000,
            "galaxium": 4000000,
        }

    def test_flight_out_total_is_sum_of_classes(self, db_session):
        """Test FlightOut total seats is the sum of all class seats."""
        _, flight_obj = add_user_and_flight(db_session, economy=2, business=0, galaxium=1)

        result = FlightOut.model_validate(flight_obj)
        assert result.seats_available == 3
        assert result.seats_available_by_class["business"] == 0


class TestUserService:
    """Test user service functions."""

    def test_register_user_success(self, db_session):
        """Test successful user registration."""
        result = user.register_user(db_session, "Test User", "test@example.com")
        assert result.name == "Test User"
        assert result.email == "test@example.com"
        assert result.user_id > 0

    def test_register_user_duplicate_email(self, db_session):
        """Test registration with duplicate email."""
        user.register_user(db_session, "User 1", "test@example.com")
        result = user.register_user(db_session, "User 2", "test@example.com")

        assert isinstance(result, ErrorResponse)
        assert result.error_code == "EMAIL_EXISTS"

    def test_get_user_success(self, db_session):
        """Test successful user retrieval."""
        db_session.add(User(name="Test User", email="test@example.com"))
        db_session.commit()

        result = user.get_user(db_session, "Test User", "test@example.com")
        assert result.name == "Test User"
        assert result.email == "test@example.com"

    def test_get_user_not_found(self, db_session):
        """Test user retrieval when not found."""
        result = user.get_user(db_session, "NonExistent", "none@example.com")
        assert isinstance(result, ErrorResponse)
        assert result.error_code == "USER_NOT_FOUND"


class TestBookingService:
    """Test booking service functions."""

    def test_book_flight_success(self, db_session):
        """Test successful flight booking."""
        user_obj, flight_obj = add_user_and_flight(db_session)

        result = booking.book_flight(db_session, user_obj.user_id, "Test User", flight_obj.flight_id)
        assert result.status == "booked"
        assert result.user_id == user_obj.user_id
        assert result.flight_id == flight_obj.flight_id

        # Verify seat was decremented
        db_session.refresh(flight_obj)
        assert flight_obj.economy_seats_available == 2

    def test_book_flight_not_found(self, db_session):
        """Test booking non-existent flight."""
        db_session.add(User(name="Test User", email="test@example.com"))
        db_session.commit()
        user_obj = db_session.query(User).first()

        result = booking.book_flight(db_session, user_obj.user_id, "Test User", 999)
        assert isinstance(result, ErrorResponse)
        assert result.error_code == "FLIGHT_NOT_FOUND"

    def test_book_flight_no_seats(self, db_session):
        """Test booking when no seats available."""
        user_obj, flight_obj = add_user_and_flight(db_session, economy=0, business=0, galaxium=0)

        result = booking.book_flight(db_session, user_obj.user_id, "Test User", flight_obj.flight_id)
        assert isinstance(result, ErrorResponse)
        assert result.error_code == "NO_SEATS_AVAILABLE"

    def test_book_flight_user_not_found(self, db_session):
        """Test booking with non-existent user."""
        db_session.add(Flight(
            origin="Earth",
            destination="Mars",
            departure_time="2099-01-01T09:00:00Z",
            arrival_time="2099-01-01T17:00:00Z",
            price=1000000,
            economy_seats_available=3,
            business_seats_available=1,
            galaxium_seats_available=1
        ))
        db_session.commit()
        flight_obj = db_session.query(Flight).first()

        result = booking.book_flight(db_session, 999, "Fake User", flight_obj.flight_id)
        assert isinstance(result, ErrorResponse)
        assert result.error_code == "USER_NOT_FOUND"

    def test_book_flight_name_mismatch(self, db_session):
        """Test booking with wrong name for user ID."""
        db_session.add(User(name="Real Name", email="test@example.com"))
        db_session.add(Flight(
            origin="Earth",
            destination="Mars",
            departure_time="2099-01-01T09:00:00Z",
            arrival_time="2099-01-01T17:00:00Z",
            price=1000000,
            economy_seats_available=3,
            business_seats_available=1,
            galaxium_seats_available=1
        ))
        db_session.commit()

        user_obj = db_session.query(User).first()
        flight_obj = db_session.query(Flight).first()

        result = booking.book_flight(db_session, user_obj.user_id, "Wrong Name", flight_obj.flight_id)
        assert isinstance(result, ErrorResponse)
        assert result.error_code == "NAME_MISMATCH"

    @pytest.mark.parametrize("seat_class", SEAT_CLASSES)
    def test_book_flight_each_class(self, db_session, seat_class):
        """Test booking each class stores the class and only decrements that class."""
        user_obj, flight_obj = add_user_and_flight(db_session, economy=3, business=2, galaxium=1)
        before = seats_by_class(flight_obj)

        result = booking.book_flight(
            db_session, user_obj.user_id, "Test User", flight_obj.flight_id, seat_class
        )
        assert not isinstance(result, ErrorResponse)
        assert result.seat_class == seat_class
        assert result.status == "booked"

        stored = db_session.query(Booking).first()
        assert stored.seat_class == seat_class

        db_session.refresh(flight_obj)
        after = seats_by_class(flight_obj)
        for cls_name in SEAT_CLASSES:
            expected = before[cls_name] - 1 if cls_name == seat_class else before[cls_name]
            assert after[cls_name] == expected

    def test_book_flight_default_class_is_economy(self, db_session):
        """Test the seat class defaults to economy when omitted."""
        user_obj, flight_obj = add_user_and_flight(db_session, economy=3, business=2, galaxium=1)

        result = booking.book_flight(db_session, user_obj.user_id, "Test User", flight_obj.flight_id)
        assert result.seat_class == "economy"

        db_session.refresh(flight_obj)
        assert seats_by_class(flight_obj) == {"economy": 2, "business": 2, "galaxium": 1}

    def test_book_flight_none_class_defaults_to_economy(self, db_session):
        """Test an explicit None seat class falls back to economy."""
        user_obj, flight_obj = add_user_and_flight(db_session)

        result = booking.book_flight(
            db_session, user_obj.user_id, "Test User", flight_obj.flight_id, None
        )
        assert result.seat_class == "economy"

    def test_book_flight_class_is_case_insensitive(self, db_session):
        """Test seat class matching ignores case and stores the normalized value."""
        user_obj, flight_obj = add_user_and_flight(db_session)

        result = booking.book_flight(
            db_session, user_obj.user_id, "Test User", flight_obj.flight_id, "Business"
        )
        assert result.seat_class == "business"

    def test_book_flight_invalid_class(self, db_session):
        """Test an invalid seat class is rejected and no seat is consumed."""
        user_obj, flight_obj = add_user_and_flight(db_session)
        before = seats_by_class(flight_obj)

        result = booking.book_flight(
            db_session, user_obj.user_id, "Test User", flight_obj.flight_id, "first_class"
        )
        assert isinstance(result, ErrorResponse)
        assert result.error_code == "INVALID_SEAT_CLASS"
        assert "economy, business, galaxium" in result.details

        db_session.refresh(flight_obj)
        assert seats_by_class(flight_obj) == before
        assert db_session.query(Booking).count() == 0

    def test_book_flight_empty_class_is_invalid(self, db_session):
        """Test an empty seat class string is rejected."""
        user_obj, flight_obj = add_user_and_flight(db_session)

        result = booking.book_flight(
            db_session, user_obj.user_id, "Test User", flight_obj.flight_id, ""
        )
        assert isinstance(result, ErrorResponse)
        assert result.error_code == "INVALID_SEAT_CLASS"

    def test_book_flight_sold_out_class(self, db_session):
        """Test a sold-out class returns NO_SEATS_AVAILABLE naming that class."""
        user_obj, flight_obj = add_user_and_flight(db_session, economy=3, business=2, galaxium=0)

        result = booking.book_flight(
            db_session, user_obj.user_id, "Test User", flight_obj.flight_id, "galaxium"
        )
        assert isinstance(result, ErrorResponse)
        assert result.error_code == "NO_SEATS_AVAILABLE"
        assert "Galaxium" in result.details
        assert db_session.query(Booking).count() == 0

    def test_book_flight_sold_out_class_does_not_block_others(self, db_session):
        """Test a sold-out class does not prevent booking the other classes."""
        user_obj, flight_obj = add_user_and_flight(db_session, economy=0, business=1, galaxium=1)

        economy_result = booking.book_flight(
            db_session, user_obj.user_id, "Test User", flight_obj.flight_id, "economy"
        )
        assert isinstance(economy_result, ErrorResponse)
        assert economy_result.error_code == "NO_SEATS_AVAILABLE"

        business_result = booking.book_flight(
            db_session, user_obj.user_id, "Test User", flight_obj.flight_id, "business"
        )
        galaxium_result = booking.book_flight(
            db_session, user_obj.user_id, "Test User", flight_obj.flight_id, "galaxium"
        )
        assert business_result.seat_class == "business"
        assert galaxium_result.seat_class == "galaxium"

        db_session.refresh(flight_obj)
        assert seats_by_class(flight_obj) == {"economy": 0, "business": 0, "galaxium": 0}

    def test_book_flight_class_sells_out_after_last_seat(self, db_session):
        """Test booking the last seat of a class makes the next booking fail."""
        user_obj, flight_obj = add_user_and_flight(db_session, economy=3, business=2, galaxium=1)

        first = booking.book_flight(
            db_session, user_obj.user_id, "Test User", flight_obj.flight_id, "galaxium"
        )
        second = booking.book_flight(
            db_session, user_obj.user_id, "Test User", flight_obj.flight_id, "galaxium"
        )
        assert first.status == "booked"
        assert isinstance(second, ErrorResponse)
        assert second.error_code == "NO_SEATS_AVAILABLE"

    def test_cancel_booking_success(self, db_session):
        """Test successful booking cancellation."""
        user_obj, flight_obj = add_user_and_flight(db_session, economy=2, business=1, galaxium=1)

        db_session.add(Booking(
            user_id=user_obj.user_id,
            flight_id=flight_obj.flight_id,
            seat_class="economy",
            status="booked",
            booking_time="2099-01-01T10:00:00Z"
        ))
        db_session.commit()

        booking_obj = db_session.query(Booking).first()
        result = booking.cancel_booking(db_session, booking_obj.booking_id)

        assert result.status == "cancelled"

        # Verify seat was restored
        db_session.refresh(flight_obj)
        assert flight_obj.economy_seats_available == 3

    @pytest.mark.parametrize("seat_class", SEAT_CLASSES)
    def test_cancel_booking_restores_correct_class(self, db_session, seat_class):
        """Test cancelling restores the seat to the booking's own class only."""
        user_obj, flight_obj = add_user_and_flight(db_session, economy=3, business=2, galaxium=1)
        before = seats_by_class(flight_obj)

        booked = booking.book_flight(
            db_session, user_obj.user_id, "Test User", flight_obj.flight_id, seat_class
        )
        db_session.refresh(flight_obj)
        assert seats_by_class(flight_obj)[seat_class] == before[seat_class] - 1

        cancelled = booking.cancel_booking(db_session, booked.booking_id)
        assert cancelled.status == "cancelled"
        assert cancelled.seat_class == seat_class

        db_session.refresh(flight_obj)
        assert seats_by_class(flight_obj) == before

    def test_cancel_booking_reopens_sold_out_class(self, db_session):
        """Test a sold-out class can be booked again after a cancellation."""
        user_obj, flight_obj = add_user_and_flight(db_session, economy=3, business=2, galaxium=1)

        booked = booking.book_flight(
            db_session, user_obj.user_id, "Test User", flight_obj.flight_id, "galaxium"
        )
        booking.cancel_booking(db_session, booked.booking_id)

        again = booking.book_flight(
            db_session, user_obj.user_id, "Test User", flight_obj.flight_id, "galaxium"
        )
        assert again.status == "booked"
        assert again.seat_class == "galaxium"

    def test_cancel_booking_not_found(self, db_session):
        """Test cancelling non-existent booking."""
        result = booking.cancel_booking(db_session, 999)
        assert isinstance(result, ErrorResponse)
        assert result.error_code == "BOOKING_NOT_FOUND"

    def test_cancel_booking_already_cancelled(self, db_session):
        """Test cancelling already cancelled booking."""
        user_obj, flight_obj = add_user_and_flight(db_session)

        db_session.add(Booking(
            user_id=user_obj.user_id,
            flight_id=flight_obj.flight_id,
            seat_class="economy",
            status="cancelled",
            booking_time="2099-01-01T10:00:00Z"
        ))
        db_session.commit()

        booking_obj = db_session.query(Booking).first()
        result = booking.cancel_booking(db_session, booking_obj.booking_id)

        assert isinstance(result, ErrorResponse)
        assert result.error_code == "ALREADY_CANCELLED"

    def test_get_bookings_success(self, db_session):
        """Test getting user bookings."""
        user_obj, flight_obj = add_user_and_flight(db_session)

        db_session.add(Booking(
            user_id=user_obj.user_id,
            flight_id=flight_obj.flight_id,
            seat_class="business",
            status="booked",
            booking_time="2099-01-01T10:00:00Z"
        ))
        db_session.commit()

        result = booking.get_bookings(db_session, user_obj.user_id)
        assert len(result) == 1
        assert result[0].status == "booked"
        assert result[0].seat_class == "business"

    def test_get_bookings_empty(self, db_session):
        """Test getting bookings when user has none."""
        result = booking.get_bookings(db_session, 999)
        assert result == []
