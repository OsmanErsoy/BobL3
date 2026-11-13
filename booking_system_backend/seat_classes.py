from enum import Enum


class SeatClass(str, Enum):
    ECONOMY = "economy"
    BUSINESS = "business"
    GALAXIUM = "galaxium"


SEAT_CLASSES = [SeatClass.ECONOMY.value, SeatClass.BUSINESS.value, SeatClass.GALAXIUM.value]

DEFAULT_SEAT_CLASS = SeatClass.ECONOMY.value

SEAT_CLASS_MULTIPLIERS: dict[str, int] = {
    SeatClass.ECONOMY.value: 1,
    SeatClass.BUSINESS.value: 2,
    SeatClass.GALAXIUM.value: 4,
}


def get_seat_class_multiplier(seat_class: str) -> int:
    """Return the price multiplier for a given seat class. Defaults to 1 if unknown."""
    return SEAT_CLASS_MULTIPLIERS.get(seat_class, 1)
