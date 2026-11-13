import { useEffect, useState } from 'react';
import type { Flight, SeatClass } from '../../types';
import { Modal, Button } from '../common';
import { Plane, Calendar, Clock, DollarSign } from 'lucide-react';
import { formatCurrency, formatDate, calculateDuration } from '../../utils/formatters';
import { bookFlight, isErrorResponse } from '../../services/api';
import { useUser } from '../../hooks/useUser';
import { SEAT_CLASSES, SEAT_CLASS_LABELS } from '../../utils/seatClasses';
import toast from 'react-hot-toast';

interface BookingModalProps {
  isOpen: boolean;
  onClose: () => void;
  flight: Flight | null;
  onSuccess: () => void;
}

// Cheapest class that still has seats; null when every class is sold out
const getDefaultSeatClass = (flight: Flight): SeatClass | null => {
  const available = SEAT_CLASSES.filter((c) => flight.seats_available_by_class[c] > 0);
  if (available.length === 0) return null;
  return available.reduce((best, c) =>
    flight.prices_by_class[c] < flight.prices_by_class[best] ? c : best
  );
};

export const BookingModal = ({ isOpen, onClose, flight, onSuccess }: BookingModalProps) => {
  const { user } = useUser();
  const [isLoading, setIsLoading] = useState(false);
  const [selectedClass, setSelectedClass] = useState<SeatClass | null>(null);

  // Reset the selection whenever the modal opens or the flight changes
  useEffect(() => {
    setSelectedClass(null);
  }, [isOpen, flight?.flight_id]);

  if (!flight) return null;

  // Fall back to the default if nothing is chosen or the chosen class is sold out
  const seatClass =
    selectedClass && flight.seats_available_by_class[selectedClass] > 0
      ? selectedClass
      : getDefaultSeatClass(flight);

  const handleConfirmBooking = async () => {
    if (!user) {
      toast.error('Please sign in to book a flight');
      return;
    }
    if (!seatClass) {
      toast.error('Please select an available seat class');
      return;
    }

    setIsLoading(true);

    try {
      const result = await bookFlight({
        user_id: user.user_id,
        name: user.name,
        flight_id: flight.flight_id,
        seat_class: seatClass,
      });

      if (isErrorResponse(result)) {
        toast.error(result.details || result.error);
        return;
      }

      toast.success('Flight booked successfully!');
      onSuccess();
      onClose();
    } catch (error: any) {
      toast.error(error.details || error.error || 'Failed to book flight');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Confirm Your Booking"
      size="md"
    >
      <div className="space-y-6">
        {/* Flight Summary */}
        <div className="glass-card p-4 bg-white/5">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 rounded-lg bg-cosmic-gradient">
              <Plane className="text-white" size={24} />
            </div>
            <div>
              <h3 className="text-xl font-bold text-star-white">
                {flight.origin} → {flight.destination}
              </h3>
              <p className="text-sm text-star-white/60">
                Flight #{flight.flight_id}
              </p>
            </div>
          </div>

          <div className="space-y-3">
            {/* Departure */}
            <div className="flex items-start gap-3">
              <Calendar className="text-cosmic-purple mt-1" size={20} />
              <div>
                <p className="text-xs text-star-white/60">Departure</p>
                <p className="text-star-white font-medium">
                  {formatDate(flight.departure_time)}
                </p>
              </div>
            </div>

            {/* Arrival */}
            <div className="flex items-start gap-3">
              <Calendar className="text-cosmic-purple mt-1" size={20} />
              <div>
                <p className="text-xs text-star-white/60">Arrival</p>
                <p className="text-star-white font-medium">
                  {formatDate(flight.arrival_time)}
                </p>
              </div>
            </div>

            {/* Duration */}
            <div className="flex items-start gap-3">
              <Clock className="text-cosmic-purple mt-1" size={20} />
              <div>
                <p className="text-xs text-star-white/60">Duration</p>
                <p className="text-star-white font-medium">
                  {calculateDuration(flight.departure_time, flight.arrival_time)}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Passenger Info */}
        {user && (
          <div className="glass-card p-4 bg-white/5">
            <h4 className="text-sm font-semibold text-star-white mb-2">
              Passenger Information
            </h4>
            <p className="text-star-white">{user.name}</p>
            <p className="text-star-white/60 text-sm">{user.email}</p>
          </div>
        )}

        {/* Seat Class */}
        <fieldset className="glass-card p-4 bg-white/5">
          <legend className="sr-only">Seat class</legend>
          <h4 className="text-sm font-semibold text-star-white mb-3" aria-hidden="true">
            Seat Class
          </h4>
          <div className="grid grid-cols-3 gap-3">
            {SEAT_CLASSES.map((c) => {
              const seatsLeft = flight.seats_available_by_class[c];
              const soldOut = seatsLeft === 0;
              const isSelected = seatClass === c;
              return (
                <label
                  key={c}
                  className={`block rounded-lg border p-3 text-center transition-colors focus-within:ring-2 focus-within:ring-cosmic-purple ${
                    soldOut
                      ? 'border-white/10 opacity-50 cursor-not-allowed'
                      : isSelected
                      ? 'border-cosmic-purple bg-cosmic-purple/20 cursor-pointer'
                      : 'border-white/10 hover:border-white/30 cursor-pointer'
                  }`}
                >
                  <input
                    type="radio"
                    name="seat-class"
                    value={c}
                    checked={isSelected}
                    disabled={soldOut}
                    onChange={() => setSelectedClass(c)}
                    className="sr-only"
                  />
                  <span className="block text-sm font-semibold text-star-white">
                    {SEAT_CLASS_LABELS[c]}
                  </span>
                  <span className="block text-sm text-star-white/80">
                    {formatCurrency(flight.prices_by_class[c])}
                  </span>
                  <span
                    className={`block text-xs ${
                      soldOut ? 'text-red-500' : 'text-star-white/60'
                    }`}
                  >
                    {soldOut ? 'Sold out' : `${seatsLeft} left`}
                  </span>
                </label>
              );
            })}
          </div>
        </fieldset>

        {/* Price */}
        <div className="flex items-center justify-between p-4 glass-card bg-cosmic-gradient">
          <div className="flex items-center gap-2">
            <DollarSign className="text-white" size={24} />
            <span className="text-white font-semibold">Total Price</span>
          </div>
          <span className="text-2xl font-bold text-white">
            {seatClass ? formatCurrency(flight.prices_by_class[seatClass]) : '—'}
          </span>
        </div>

        {/* Actions */}
        <div className="flex gap-3">
          <Button
            variant="secondary"
            onClick={onClose}
            disabled={isLoading}
            className="flex-1"
          >
            Cancel
          </Button>
          <Button
            onClick={handleConfirmBooking}
            isLoading={isLoading}
            disabled={!seatClass}
            className="flex-1"
          >
            Confirm Booking
          </Button>
        </div>

        <p className="text-xs text-star-white/60 text-center">
          By confirming, you agree to our terms and conditions
        </p>
      </div>
    </Modal>
  );
};

// Made with Bob
