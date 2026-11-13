import type { Flight } from '../../types';
import { Card, Button } from '../common';
import { Plane, Clock, DollarSign, Users } from 'lucide-react';
import { formatCurrency, formatDate, formatTime, calculateDuration } from '../../utils/formatters';
import { SEAT_CLASSES, SEAT_CLASS_LABELS, getFromPrice } from '../../utils/seatClasses';
import { motion } from 'framer-motion';

interface FlightCardProps {
  flight: Flight;
  onBook: (flight: Flight) => void;
}

export const FlightCard = ({ flight, onBook }: FlightCardProps) => {
  const isLowSeats = flight.seats_available <= 2;
  const isSoldOut = flight.seats_available === 0;
  const fromPrice = getFromPrice(flight.prices_by_class, flight.seats_available_by_class);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -4 }}
      transition={{ duration: 0.3 }}
    >
      <Card className="h-full flex flex-col">
        {/* Route Header */}
        <div className="flex items-center justify-between mb-4 pb-4 border-b border-white/10">
          <div className="flex items-center gap-3">
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
        </div>

        {/* Flight Details */}
        <div className="space-y-3 mb-6 flex-1">
          {/* Departure & Arrival */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-xs text-star-white/60 mb-1">Departure</p>
              <p className="text-sm font-medium text-star-white">
                {formatDate(flight.departure_time, 'MMM dd, yyyy')}
              </p>
              <p className="text-lg font-bold text-cosmic-purple">
                {formatTime(flight.departure_time)}
              </p>
            </div>
            <div>
              <p className="text-xs text-star-white/60 mb-1">Arrival</p>
              <p className="text-sm font-medium text-star-white">
                {formatDate(flight.arrival_time, 'MMM dd, yyyy')}
              </p>
              <p className="text-lg font-bold text-cosmic-purple">
                {formatTime(flight.arrival_time)}
              </p>
            </div>
          </div>

          {/* Duration */}
          <div className="flex items-center gap-2 text-star-white/70">
            <Clock size={16} />
            <span className="text-sm">
              Duration: {calculateDuration(flight.departure_time, flight.arrival_time)}
            </span>
          </div>

          {/* Price */}
          <div className="flex items-center gap-2">
            <DollarSign size={16} className="text-alien-green" />
            <span className="text-sm text-star-white/60">from</span>
            <span className="text-2xl font-bold text-star-white">
              {formatCurrency(fromPrice)}
            </span>
            <span className="text-sm text-star-white/60">per seat</span>
          </div>

          {/* Seats Available */}
          <div className="flex items-center gap-2">
            <Users size={16} className={isLowSeats ? 'text-solar-orange' : 'text-star-white/70'} />
            <span className={`text-sm ${isLowSeats ? 'text-solar-orange font-semibold' : 'text-star-white/70'}`}>
              {isSoldOut ? 'Sold Out' : `${flight.seats_available} seats available`}
            </span>
          </div>

          {/* Per-class availability */}
          <div className="grid grid-cols-3 gap-2">
            {SEAT_CLASSES.map((seatClass) => {
              const seats = flight.seats_available_by_class[seatClass];
              return (
                <div
                  key={seatClass}
                  className="rounded-lg border border-white/10 bg-white/5 px-2 py-1.5 text-center"
                >
                  <p className="text-xs text-star-white/60">{SEAT_CLASS_LABELS[seatClass]}</p>
                  <p
                    className={`text-sm font-semibold ${
                      seats === 0 ? 'text-star-white/40' : 'text-star-white'
                    }`}
                  >
                    {seats === 0 ? 'Sold out' : `${seats} left`}
                  </p>
                </div>
              );
            })}
          </div>
        </div>

        {/* Book Button */}
        <Button
          onClick={() => onBook(flight)}
          disabled={isSoldOut}
          className="w-full"
        >
          {isSoldOut ? 'Sold Out' : 'Book Now'}
        </Button>
      </Card>
    </motion.div>
  );
};

// Made with Bob
