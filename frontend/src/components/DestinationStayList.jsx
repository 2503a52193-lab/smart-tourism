import { useState, useEffect, useMemo } from "react";
import {
  MapPin, Star, Calendar, Users, BedDouble, ShieldCheck,
  CheckCircle2, AlertCircle, Info, Sparkles, ArrowRight,
  Search, X, Clock, ExternalLink, Compass, Navigation, Car
} from "lucide-react";
import "./CatalogData.css";
import { json } from "../api";
import HotelLocationModal, { getGoogleMapsUrl, getDirectionsUrl, getTaxiSearchUrl, getAutoSearchUrl } from "./HotelLocationModal.jsx";

const localDate = (date) => {
  const d = date instanceof Date ? date : new Date(date);
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
};

const getTomorrow = (value) => {
  const base = value ? new Date(`${value}T00:00:00`) : new Date();
  base.setDate(base.getDate() + 1);
  return localDate(base);
};

const getFutureDate = (daysAhead = 3) => {
  const base = new Date();
  base.setDate(base.getDate() + daysAhead);
  return localDate(base);
};

export default function DestinationStayList({
  destinations = [],
  hotels = [],
  onBook,
  submitting = false,
  prefilledSearch = null,
}) {
  // Global search filters
  const [selectedDestinationId, setSelectedDestinationId] = useState("");
  const [checkIn, setCheckIn] = useState(() => getTomorrow());
  const [checkOut, setCheckOut] = useState(() => getFutureDate(3));
  const [guests, setGuests] = useState(2);
  const [roomCount, setRoomCount] = useState(1);
  const [searchQuery, setSearchQuery] = useState("");
  const [sortBy, setSortBy] = useState("rating-desc");

  // Selection states per hotel: selectedRoomTypeId
  const [selectedRoomTypes, setSelectedRoomTypes] = useState({});
  // Live availability cache: { [hotelId:roomId:checkIn:checkOut]: { loading, data, error } }
  const [availabilityCache, setAvailabilityCache] = useState({});

  // Confirmation modal state
  const [pendingBooking, setPendingBooking] = useState(null);
  const [activeMapHotel, setActiveMapHotel] = useState(null);

  // Sync prefilled search when AI Trip Generator sends a destination or dates
  useEffect(() => {
    if (prefilledSearch) {
      if (prefilledSearch.destinationId) {
        setSelectedDestinationId(String(prefilledSearch.destinationId));
      }
      if (prefilledSearch.travelers) {
        setGuests(Math.max(1, Number(prefilledSearch.travelers)));
      }
      if (prefilledSearch.rooms) {
        setRoomCount(Math.max(1, Number(prefilledSearch.rooms)));
      }
      if (prefilledSearch.checkIn) {
        setCheckIn(prefilledSearch.checkIn);
      }
      if (prefilledSearch.checkOut) {
        setCheckOut(prefilledSearch.checkOut);
      }
    }
  }, [prefilledSearch]);

  // Calculate nights
  const nights = useMemo(() => {
    if (!checkIn || !checkOut) return 0;
    const diff = new Date(`${checkOut}T00:00:00`) - new Date(`${checkIn}T00:00:00`);
    return Math.max(0, Math.round(diff / 86400000));
  }, [checkIn, checkOut]);

  const datesValid = nights > 0 && checkIn >= localDate(new Date());

  // Filtered hotels list
  const filteredHotels = useMemo(() => {
    return hotels.filter(hotel => {
      if (!hotel.active) return false;
      if (selectedDestinationId && String(hotel.destination_id) !== String(selectedDestinationId)) {
        return false;
      }
      if (searchQuery.trim()) {
        const query = searchQuery.toLowerCase();
        const matchName = hotel.name.toLowerCase().includes(query);
        const matchDest = (hotel.destination || "").toLowerCase().includes(query);
        const matchAddr = (hotel.address || "").toLowerCase().includes(query);
        const matchFacility = (hotel.facilities || []).some(f => f.toLowerCase().includes(query));
        if (!matchName && !matchDest && !matchAddr && !matchFacility) return false;
      }
      return true;
    }).sort((a, b) => {
      if (sortBy === "price-asc") return a.nightly_rate - b.nightly_rate;
      if (sortBy === "price-desc") return b.nightly_rate - a.nightly_rate;
      if (sortBy === "rating-desc") return (b.rating || 0) - (a.rating || 0);
      return a.name.localeCompare(b.name);
    });
  }, [hotels, selectedDestinationId, searchQuery, sortBy]);

  // Query availability for a specific room type and date range
  async function fetchAvailability(hotelId, roomId, inDate, outDate) {
    if (!hotelId || !roomId || !inDate || !outDate || outDate <= inDate) return;
    const cacheKey = `${hotelId}:${roomId}:${inDate}:${outDate}`;
    if (availabilityCache[cacheKey]?.loading) return;

    setAvailabilityCache(prev => ({
      ...prev,
      [cacheKey]: { loading: true, data: null, error: "" },
    }));

    try {
      const params = new URLSearchParams({
        room_type_id: roomId,
        check_in: inDate,
        check_out: outDate,
      });
      const res = await json(`/hotels/${hotelId}/availability?${params}`);
      setAvailabilityCache(prev => ({
        ...prev,
        [cacheKey]: { loading: false, data: res, error: "" },
      }));
    } catch (err) {
      setAvailabilityCache(prev => ({
        ...prev,
        [cacheKey]: { loading: false, data: null, error: err.message },
      }));
    }
  }

  // Preload availability for active rooms on filtered hotels
  useEffect(() => {
    if (!datesValid) return;
    filteredHotels.forEach(hotel => {
      const selectedRoomId = selectedRoomTypes[hotel.id] || (hotel.rooms && hotel.rooms[0]?.id);
      if (selectedRoomId) {
        void fetchAvailability(hotel.id, selectedRoomId, checkIn, checkOut);
      }
    });
  }, [filteredHotels, checkIn, checkOut, selectedRoomTypes, datesValid]);

  function handleSelectRoom(hotelId, roomId) {
    setSelectedRoomTypes(prev => ({ ...prev, [hotelId]: Number(roomId) }));
    if (datesValid) {
      void fetchAvailability(hotelId, Number(roomId), checkIn, checkOut);
    }
  }

  function handleOpenBookingModal(hotel, room, availableCount, totalCost) {
    setPendingBooking({
      hotel,
      room,
      availableCount,
      checkIn,
      checkOut,
      nights,
      guests,
      rooms: roomCount,
      nightlyRate: room.nightly_rate,
      totalAmount: totalCost,
    });
  }

  async function handleConfirmBooking() {
    if (!pendingBooking || submitting) return;
    const dest = destinations.find(d => d.id === pendingBooking.hotel.destination_id) || {
      id: pendingBooking.hotel.destination_id,
      name: pendingBooking.hotel.destination,
    };

    const bookingPayload = {
      destination_id: dest.id,
      hotel_id: pendingBooking.hotel.id,
      room_type_id: pendingBooking.room.id,
      check_in: pendingBooking.checkIn,
      check_out: pendingBooking.checkOut,
      guests: pendingBooking.guests,
      rooms: pendingBooking.rooms,
    };

    const result = await onBook(bookingPayload, dest);
    if (result) {
      setPendingBooking(null);
      // Invalidate availability cache for this room
      const cacheKey = `${pendingBooking.hotel.id}:${pendingBooking.room.id}:${pendingBooking.checkIn}:${pendingBooking.checkOut}`;
      setAvailabilityCache(prev => {
        const next = { ...prev };
        delete next[cacheKey];
        return next;
      });
      // Re-fetch availability
      void fetchAvailability(
        pendingBooking.hotel.id,
        pendingBooking.room.id,
        pendingBooking.checkIn,
        pendingBooking.checkOut
      );
    }
  }

  return (
    <div className="hotel-search-experience" id="hotel-search-section">
      {/* Search & Filter Header Strip */}
      <div className="hotel-search-filter-card">
        <div className="search-filter-heading">
          <div className="filter-title-group">
            <Search size={18} className="search-title-icon" />
            <div>
              <h3>Find & Book Stays</h3>
              <p>Search verified and sample accommodations with live inventory and date availability</p>
            </div>
          </div>
          {selectedDestinationId && (
            <button
              type="button"
              className="btn-clear-filter"
              onClick={() => setSelectedDestinationId("")}
            >
              Clear Destination Filter <X size={13} />
            </button>
          )}
        </div>

        <div className="search-inputs-grid">
          {/* Destination */}
          <div className="search-input-field">
            <label><MapPin size={14} /> Destination</label>
            <select
              value={selectedDestinationId}
              onChange={e => setSelectedDestinationId(e.target.value)}
            >
              <option value="">All Destinations ({destinations.length})</option>
              {destinations.map(d => (
                <option key={d.id} value={d.id}>{d.name} ({d.state || d.region})</option>
              ))}
            </select>
          </div>

          {/* Check-In */}
          <div className="search-input-field">
            <label><Calendar size={14} /> Check-In</label>
            <input
              type="date"
              min={localDate(new Date())}
              value={checkIn}
              onChange={e => {
                const newIn = e.target.value;
                setCheckIn(newIn);
                if (checkOut <= newIn) setCheckOut(getTomorrow(newIn));
              }}
              required
            />
          </div>

          {/* Check-Out */}
          <div className="search-input-field">
            <label><Calendar size={14} /> Check-Out</label>
            <input
              type="date"
              min={getTomorrow(checkIn)}
              value={checkOut}
              onChange={e => setCheckOut(e.target.value)}
              required
            />
          </div>

          {/* Guests */}
          <div className="search-input-field">
            <label><Users size={14} /> Guests</label>
            <select
              value={guests}
              onChange={e => setGuests(Number(e.target.value))}
            >
              {Array.from({ length: 16 }, (_, i) => i + 1).map(n => (
                <option key={n} value={n}>{n} {n === 1 ? "Guest" : "Guests"}</option>
              ))}
            </select>
          </div>

          {/* Rooms */}
          <div className="search-input-field">
            <label><BedDouble size={14} /> Rooms</label>
            <select
              value={roomCount}
              onChange={e => setRoomCount(Number(e.target.value))}
            >
              {Array.from({ length: 6 }, (_, i) => i + 1).map(n => (
                <option key={n} value={n}>{n} {n === 1 ? "Room" : "Rooms"}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Quick Filter Bar */}
        <div className="search-secondary-strip">
          <div className="search-keyword-wrap">
            <input
              type="text"
              placeholder="Search by hotel name, address, or amenities (e.g. pool, Wi-Fi)..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
            />
            {searchQuery && (
              <button type="button" className="clear-keyword" onClick={() => setSearchQuery("")}>
                <X size={14} />
              </button>
            )}
          </div>
          <div className="sort-wrap">
            <label>Sort by:</label>
            <select value={sortBy} onChange={e => setSortBy(e.target.value)}>
              <option value="rating-desc">Guest Rating: High to Low</option>
              <option value="price-asc">Nightly Rate: Low to High</option>
              <option value="price-desc">Nightly Rate: High to Low</option>
              <option value="name-asc">Alphabetical</option>
            </select>
          </div>
        </div>
      </div>

      {/* Date Validation Alert */}
      {!datesValid && (
        <div className="hotel-warning-banner" role="alert">
          <AlertCircle size={16} />
          <span>Please select valid future dates. Check-out must be after check-in.</span>
        </div>
      )}

      {/* Results Header */}
      <div className="hotel-results-count-bar">
        <span>
          Showing <strong>{filteredHotels.length}</strong> available properties
          {selectedDestinationId ? ` in ${destinations.find(d => String(d.id) === String(selectedDestinationId))?.name || "destination"}` : ""}
          {datesValid ? ` · ${nights} night${nights === 1 ? "" : "s"} (${checkIn} to ${checkOut})` : ""}
        </span>
      </div>

      {/* Hotel Cards Grid */}
      {filteredHotels.length === 0 ? (
        <div className="empty hotel-empty-state">
          <BedDouble size={36} />
          <h4>No hotels found matching your search</h4>
          <p>Try selecting a different destination or clearing your search filters above.</p>
          <button
            type="button"
            className="button secondary"
            onClick={() => { setSelectedDestinationId(""); setSearchQuery(""); }}
          >
            Reset Filters
          </button>
        </div>
      ) : (
        <div className="hotel-cards-grid">
          {filteredHotels.map(hotel => {
            const destination = destinations.find(d => d.id === hotel.destination_id);
            const bookableRooms = (hotel.rooms || []).filter(r => r.active && r.nightly_rate > 0);
            const selectedRoomId = selectedRoomTypes[hotel.id] || (bookableRooms[0]?.id ?? null);
            const selectedRoom = bookableRooms.find(r => r.id === selectedRoomId) || bookableRooms[0];

            // Live availability cache lookup
            const cacheKey = selectedRoom && datesValid ? `${hotel.id}:${selectedRoom.id}:${checkIn}:${checkOut}` : "";
            const availState = cacheKey ? availabilityCache[cacheKey] : null;
            const isLoadingAvail = availState?.loading || false;
            const availData = availState?.data;
            const availError = availState?.error;

            const availableRoomsCount = availData
              ? availData.available_rooms
              : (selectedRoom?.available_rooms ?? 0);

            // Capacity & inventory validation
            const hasInventory = datesValid && !isLoadingAvail && (availData ? availData.available : availableRoomsCount >= roomCount);
            const meetsCapacity = selectedRoom ? guests <= selectedRoom.capacity * roomCount : false;
            const canBook = datesValid && hasInventory && meetsCapacity && selectedRoom && !submitting;

            // Total price calculation
            const totalAccommodationCost = selectedRoom && datesValid
              ? selectedRoom.nightly_rate * roomCount * nights
              : null;

            return (
              <article className="hotel-premium-card" key={`hotel-${hotel.id}`} id={`hotel-card-${hotel.id}`}>
                {/* Image Section */}
                <div
                  className="hotel-card-media"
                  style={{
                    backgroundImage: `linear-gradient(180deg, rgba(18,35,26,0.1) 0%, rgba(18,35,26,0.7) 100%), url("${hotel.image_url || "https://images.unsplash.com/photo-1566073771259-6a8506099945?auto=format&fit=crop&w=1200&q=80"}")`,
                  }}
                >
                  <div className="hotel-media-badges">
                    <span className="badge-destination">
                      <MapPin size={12} /> {destination ? destination.name : (hotel.destination || "India")}
                    </span>
                    {hotel.is_demo ? (
                      <span className="badge-demo" title="Fictional demonstration property for testing">
                        <Sparkles size={11} /> Demonstration Stay
                      </span>
                    ) : (
                      <span className="badge-verified" title="Verified property listing">
                        <ShieldCheck size={11} /> Verified Listing
                      </span>
                    )}
                  </div>
                  {hotel.rating && (
                    <div className="hotel-media-rating">
                      <Star size={13} fill="#f59e0b" color="#f59e0b" />
                      <strong>{Number(hotel.rating).toFixed(1)}</strong>
                      <span>/ 5</span>
                    </div>
                  )}
                </div>

                {/* Body Details */}
                <div className="hotel-card-body">
                  <div className="hotel-title-row">
                    <h4>{hotel.name}</h4>
                    <span className="hotel-address">
                      <MapPin size={13} /> {hotel.address || `${hotel.destination || "Destination area"}, India`}
                    </span>
                  </div>

                  {/* Google Maps & Navigation Action Bar */}
                  <div className="hotel-map-actions-bar">
                    <button
                      type="button"
                      className="btn-hotel-map-action"
                      onClick={() => setActiveMapHotel(hotel)}
                      title="View hotel on Google Maps, nearby roads, and landmarks"
                    >
                      <Compass size={13} /> View on Google Maps
                    </button>
                    <button
                      type="button"
                      className="btn-hotel-map-action secondary"
                      onClick={() => setActiveMapHotel(hotel)}
                      title="Get directions & find nearby taxi or auto rickshaw stands"
                    >
                      <Navigation size={13} /> Local Transport & Directions
                    </button>
                    <a
                      href={getGoogleMapsUrl(hotel)}
                      target="_blank"
                      rel="noreferrer"
                      className="btn-hotel-map-action secondary"
                      title="Open directly in Google Maps in new tab"
                      style={{ padding: "0.35rem 0.5rem" }}
                    >
                      <ExternalLink size={12} />
                    </a>
                  </div>

                  {hotel.description && (
                    <p className="hotel-desc-text">{hotel.description}</p>
                  )}

                  {/* Policies & Times */}
                  <div className="hotel-policy-strip">
                    <span><Clock size={12} /> Check-in: {hotel.check_in_policy || "14:00"}</span>
                    <span><Clock size={12} /> Check-out: {hotel.check_out_policy || "11:00"}</span>
                    {hotel.source_url && (
                      <a href={hotel.source_url} target="_blank" rel="noreferrer" className="hotel-source-btn">
                        Official source <ExternalLink size={10} />
                      </a>
                    )}
                  </div>

                  {/* Facilities Chips */}
                  {hotel.facilities && hotel.facilities.length > 0 && (
                    <div className="hotel-facilities-tags">
                      {hotel.facilities.slice(0, 5).map(f => (
                        <span key={f} className="facility-pill">{f}</span>
                      ))}
                      {hotel.facilities.length > 5 && (
                        <span className="facility-more">+{hotel.facilities.length - 5} more</span>
                      )}
                    </div>
                  )}

                  {/* Room Types Selector */}
                  <div className="hotel-rooms-section">
                    <span className="rooms-heading">
                      <BedDouble size={14} /> Available Room Types:
                    </span>
                    {bookableRooms.length === 0 ? (
                      <p className="no-rooms-msg">No priced room inventory is currently listed for this property.</p>
                    ) : (
                      <div className="room-options-list">
                        {bookableRooms.map(room => {
                          const isSelected = selectedRoom?.id === room.id;
                          return (
                            <div
                              key={room.id}
                              className={`room-option-item ${isSelected ? "selected" : ""}`}
                              onClick={() => handleSelectRoom(hotel.id, room.id)}
                            >
                              <div className="room-radio">
                                <span className={`radio-dot ${isSelected ? "active" : ""}`} />
                              </div>
                              <div className="room-item-meta">
                                <span className="room-name">{room.name}</span>
                                <span className="room-specs">
                                  Up to {room.capacity} guests/room · {room.available_rooms ?? "Available"} listed
                                </span>
                              </div>
                              <div className="room-item-price">
                                <strong>₹{room.nightly_rate.toLocaleString("en-IN")}</strong>
                                <small>/night</small>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>

                  {/* Live Inventory Status Pill */}
                  {selectedRoom && datesValid && (
                    <div className="availability-status-strip">
                      {isLoadingAvail ? (
                        <span className="avail-status loading">
                          <Clock size={13} className="spin-icon" /> Checking date inventory for {datesValid ? `${nights} nights` : ""}…
                        </span>
                      ) : availError ? (
                        <span className="avail-status error">
                          <AlertCircle size={13} /> {availError}
                        </span>
                      ) : hasInventory ? (
                        <span className="avail-status in-stock">
                          <CheckCircle2 size={13} /> {availableRoomsCount} {availableRoomsCount === 1 ? "room" : "rooms"} available for these dates
                        </span>
                      ) : (
                        <span className="avail-status sold-out">
                          <AlertCircle size={13} /> Sold out for {checkIn} to {checkOut}. Please choose alternative dates.
                        </span>
                      )}
                      {!meetsCapacity && selectedRoom && (
                        <span className="avail-status warning">
                          <Info size={13} /> {roomCount} room(s) fits up to {selectedRoom.capacity * roomCount} guests. You have {guests} guests.
                        </span>
                      )}
                    </div>
                  )}

                  {/* Footer Price & Booking Action */}
                  <div className="hotel-card-footer">
                    <div className="price-calc-col">
                      {totalAccommodationCost !== null ? (
                        <>
                          <span className="total-label">Total for {nights} night{nights === 1 ? "" : "s"} ({roomCount} room{roomCount === 1 ? "" : "s"}):</span>
                          <strong className="total-amount">₹{totalAccommodationCost.toLocaleString("en-IN")}</strong>
                          <small className="rate-breakdown">₹{selectedRoom?.nightly_rate.toLocaleString("en-IN")}/night × {nights}n × {roomCount}r</small>
                        </>
                      ) : (
                        <>
                          <span className="total-label">Starting nightly rate:</span>
                          <strong className="total-amount">₹{hotel.nightly_rate.toLocaleString("en-IN")}</strong>
                          <small className="rate-breakdown">Select travel dates above for full total</small>
                        </>
                      )}
                    </div>

                    <button
                      type="button"
                      className="button primary book-action-btn"
                      disabled={!canBook}
                      onClick={() => handleOpenBookingModal(hotel, selectedRoom, availableRoomsCount, totalAccommodationCost)}
                    >
                      {submitting ? "Reserving…" : "Book Hotel Stay"} <ArrowRight size={15} />
                    </button>
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      )}

      {/* Interactive Booking Summary & Confirmation Modal */}
      {pendingBooking && (
        <div className="booking-modal-overlay" role="dialog" aria-modal="true">
          <div className="booking-modal-card">
            <div className="modal-header">
              <div className="modal-title-group">
                <span className="modal-eyebrow">REVIEW & CONFIRM STAY</span>
                <h3>Reservation Summary</h3>
              </div>
              <button
                type="button"
                className="modal-close-btn"
                onClick={() => setPendingBooking(null)}
                aria-label="Close"
              >
                <X size={18} />
              </button>
            </div>

            <div className="modal-body">
              {/* Hotel & Destination info */}
              <div className="modal-hotel-header">
                <h4>{pendingBooking.hotel.name}</h4>
                <p className="modal-address">
                  <MapPin size={13} /> {pendingBooking.hotel.address || pendingBooking.hotel.destination}
                </p>
                <div style={{ marginTop: "0.35rem", display: "flex", gap: "0.5rem" }}>
                  <button
                    type="button"
                    className="modal-map-link-btn"
                    onClick={() => setActiveMapHotel(pendingBooking.hotel)}
                  >
                    <Compass size={12} /> View on Google Maps & Local Transport
                  </button>
                </div>
                {pendingBooking.hotel.is_demo && (
                  <span className="modal-demo-tag">
                    <Sparkles size={11} /> Demonstration Booking (Testing only · no real payment charged)
                  </span>
                )}
              </div>

              {/* Booking Specifications Grid */}
              <div className="modal-specs-grid">
                <div className="spec-card">
                  <span className="spec-label"><Calendar size={13} /> Check-In</span>
                  <strong>{pendingBooking.checkIn}</strong>
                  <small>From {pendingBooking.hotel.check_in_policy || "14:00"}</small>
                </div>
                <div className="spec-card">
                  <span className="spec-label"><Calendar size={13} /> Check-Out</span>
                  <strong>{pendingBooking.checkOut}</strong>
                  <small>Until {pendingBooking.hotel.check_out_policy || "11:00"}</small>
                </div>
                <div className="spec-card">
                  <span className="spec-label"><BedDouble size={13} /> Room Type</span>
                  <strong>{pendingBooking.room.name}</strong>
                  <small>{pendingBooking.rooms} {pendingBooking.rooms === 1 ? "room" : "rooms"} reserved</small>
                </div>
                <div className="spec-card">
                  <span className="spec-label"><Users size={13} /> Guests & Capacity</span>
                  <strong>{pendingBooking.guests} Travelers</strong>
                  <small>Max {pendingBooking.room.capacity * pendingBooking.rooms} guests allowed</small>
                </div>
              </div>

              {/* Price Calculation Table */}
              <div className="modal-price-breakdown">
                <h5>Price Breakdown</h5>
                <div className="breakdown-row">
                  <span>Room rate ({pendingBooking.rooms} room × ₹{pendingBooking.nightlyRate.toLocaleString("en-IN")})</span>
                  <span>₹{(pendingBooking.nightlyRate * pendingBooking.rooms).toLocaleString("en-IN")} / night</span>
                </div>
                <div className="breakdown-row">
                  <span>Duration</span>
                  <span>{pendingBooking.nights} {pendingBooking.nights === 1 ? "night" : "nights"}</span>
                </div>
                <div className="breakdown-row">
                  <span>Taxes & Service Surcharges</span>
                  <span className="free-text">Included</span>
                </div>
                <div className="breakdown-total-row">
                  <strong>Total Accommodation Amount:</strong>
                  <strong className="grand-price">₹{pendingBooking.totalAmount.toLocaleString("en-IN")}</strong>
                </div>
              </div>

              {/* Policies & Safety Notice */}
              <div className="modal-policy-notice">
                <ShieldCheck size={16} />
                <div>
                  <strong>Protected Reservation</strong>
                  <p>Room inventory is deducted instantly from the database. You can manage or cancel this booking under My Trips at any time to release room inventory.</p>
                </div>
              </div>
            </div>

            <div className="modal-footer">
              <button
                type="button"
                className="button secondary"
                onClick={() => setPendingBooking(null)}
                disabled={submitting}
              >
                Modify Selection
              </button>
              <button
                type="button"
                className="button primary confirm-btn"
                onClick={handleConfirmBooking}
                disabled={submitting}
              >
                {submitting ? "Confirming Reservation…" : "Confirm Booking"} <ArrowRight size={16} />
              </button>
            </div>
          </div>
        </div>
      )}
      {/* Hotel Location & Directions Modal */}
      {activeMapHotel && (
        <HotelLocationModal
          hotel={activeMapHotel}
          onClose={() => setActiveMapHotel(null)}
        />
      )}
    </div>
  );
}
