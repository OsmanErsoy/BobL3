import type { SeatClass } from '../types';

// Display order (cheapest to most premium) and labels for seat classes
export const SEAT_CLASSES: SeatClass[] = ['economy', 'business', 'galaxium'];

export const SEAT_CLASS_LABELS: Record<SeatClass, string> = {
  economy: 'Economy',
  business: 'Business',
  galaxium: 'Galaxium',
};

// Lowest class price among classes that still have seats; falls back to the
// lowest price overall when every class is sold out.
export const getFromPrice = (
  prices: Record<SeatClass, number>,
  seats: Record<SeatClass, number>
): number => {
  const available = SEAT_CLASSES.filter((c) => seats[c] > 0).map((c) => prices[c]);
  const candidates = available.length > 0 ? available : SEAT_CLASSES.map((c) => prices[c]);
  return Math.min(...candidates);
};

// Made with Bob
