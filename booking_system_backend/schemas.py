from pydantic import BaseModel, EmailStr, model_validator
from typing import Optional
from seat_classes import DEFAULT_SEAT_CLASS, SEAT_CLASS_MULTIPLIERS


class FlightOut(BaseModel):
    flight_id: int
    origin: str
    destination: str
    departure_time: str
    arrival_time: str
    price: int
    seats_available: int
    seats_available_by_class: dict[str, int]
    prices_by_class: dict[str, int]

    class Config:
        from_attributes = True

    @model_validator(mode="before")
    @classmethod
    def compute_fields(cls, data):
        if not isinstance(data, dict):
            eco = getattr(data, "economy_seats_available", 0)
            bus = getattr(data, "business_seats_available", 0)
            gal = getattr(data, "galaxium_seats_available", 0)
            base_price = getattr(data, "price", 0)
            total_seats = eco + bus + gal
            seats_by_class = {
                "economy": eco,
                "business": bus,
                "galaxium": gal,
            }
            prices_by_class = {
                cls_name: base_price * mult
                for cls_name, mult in SEAT_CLASS_MULTIPLIERS.items()
            }
            return {
                "flight_id": getattr(data, "flight_id"),
                "origin": getattr(data, "origin"),
                "destination": getattr(data, "destination"),
                "departure_time": getattr(data, "departure_time"),
                "arrival_time": getattr(data, "arrival_time"),
                "price": base_price,
                "seats_available": getattr(data, "seats_available", total_seats),
                "seats_available_by_class": getattr(data, "seats_available_by_class", seats_by_class),
                "prices_by_class": getattr(data, "prices_by_class", prices_by_class),
            }
        else:
            base_price = data.get("price", 0)
            seats_by_class = data.get("seats_available_by_class")
            if seats_by_class is None:
                eco = data.get("economy_seats_available", 0)
                bus = data.get("business_seats_available", 0)
                gal = data.get("galaxium_seats_available", 0)
                seats_by_class = {
                    "economy": eco,
                    "business": bus,
                    "galaxium": gal,
                }
                data["seats_available_by_class"] = seats_by_class

            if "seats_available" not in data:
                data["seats_available"] = sum(seats_by_class.values())

            if "prices_by_class" not in data:
                data["prices_by_class"] = {
                    cls_name: base_price * mult
                    for cls_name, mult in SEAT_CLASS_MULTIPLIERS.items()
                }
            return data


class BookingRequest(BaseModel):
    user_id: int
    name: str
    flight_id: int
    seat_class: Optional[str] = DEFAULT_SEAT_CLASS


class BookingOut(BaseModel):
    booking_id: int
    user_id: int
    flight_id: int
    seat_class: str
    status: str
    booking_time: str

    class Config:
        from_attributes = True


class UserRegistration(BaseModel):
    name: str
    email: EmailStr


class UserOut(BaseModel):
    user_id: int
    name: str
    email: str

    class Config:
        from_attributes = True


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    error_code: str
    details: Optional[str] = None
