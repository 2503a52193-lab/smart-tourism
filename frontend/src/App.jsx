import { useEffect, useState } from "react";
import { Link, Navigate, Route, Routes, useNavigate } from "react-router-dom";
import { ArrowRight, Compass, LogOut, MapPin, ShieldCheck, Sparkles, Bookmark, Calendar, Users, DollarSign, Clock, Trash2, ChevronDown, ChevronUp, Navigation, Car, ExternalLink } from "lucide-react";
import { json, token } from "./api";
import Admin from "./components/Admin.jsx";
import DestinationStayList from "./components/DestinationStayList.jsx";
import ItineraryGenerator from "./components/ItineraryGenerator.jsx";
import HotelLocationModal, { getGoogleMapsUrl, getDirectionsUrl, getTaxiSearchUrl, getAutoSearchUrl } from "./components/HotelLocationModal.jsx";

function Auth({ role }) {
  const [registering, setRegistering] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();
  const admin = role === "admin";

  async function submit(event) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setBusy(true); setError("");
    try {
      if (registering) {
        const credentials = {
          name: form.get("name"), email: form.get("email"), password: form.get("password"),
        };
        await json("/auth/register", { method: "POST", body: JSON.stringify(credentials) });
        const result = await json("/auth/login", { method: "POST", body: JSON.stringify({
          email: credentials.email, password: credentials.password, role: "customer",
        }) });
        localStorage.setItem("tourism_token", result.token);
        localStorage.setItem("tourism_user", JSON.stringify(result.user));
        navigate("/dashboard");
      } else {
        const result = await json("/auth/login", { method: "POST", body: JSON.stringify({
          email: form.get("email"), password: form.get("password"), role,
        }) });
        localStorage.setItem("tourism_token", result.token);
        localStorage.setItem("tourism_user", JSON.stringify(result.user));
        navigate(admin ? "/admin" : "/dashboard");
      }
    } catch (err) { setError(err.message); }
    finally { setBusy(false); }
  }

  return <main className={`auth-page ${admin ? "admin-auth" : ""}`}>
    <section className="auth-visual">
      <div className="visual-brand"><Compass size={22} /> roamly<span>.</span></div>
      <div className="visual-copy">
        <span className="eyebrow">{admin ? "MANAGEMENT PORTAL" : "YOUR NEXT CHAPTER"}</span>
        <h1>{admin ? "A clearer view of every journey." : "The world is closer than you think."}</h1>
        <p>{admin ? "Thoughtful tools to help your team make every trip count." : "Find your place in the world. We'll take care of the details."}</p>
      </div>
      <span className="visual-caption"><MapPin size={15} /> {admin ? "Travel operations, thoughtfully managed" : "A quiet morning in the hills of Kerala"}</span>
    </section>
    <section className="auth-form-wrap">
      <Link className="mobile-brand" to="/"><Compass /> roamly<span>.</span></Link>
      <div className="auth-form">
        <span className="eyebrow">{admin ? "ADMIN ACCESS" : registering ? "JOIN THE JOURNEY" : "WELCOME BACK"}</span>
        <h2>{admin ? "Admin sign in" : registering ? "Create your account" : "Sign in to Roamly"}</h2>
        <p className="muted">{admin ? "Use your authorized administrator account." : registering ? "Your next adventure begins here." : "Pick up where your next adventure begins."}</p>
        {error && <div className="alert">{error}</div>}
        <form onSubmit={submit}>
          {registering && <label>Full name<input name="name" autoComplete="name" required maxLength="120" placeholder="Your name" /></label>}
          <label>{admin ? "Admin username or email" : "Email address"}<input name="email" type={admin ? "text" : "email"} autoComplete={admin ? "username" : "email"} required placeholder={admin ? "Admin username or email" : "you@example.com"} /></label>
          <label>Password<input name="password" type="password" autoComplete={registering ? "new-password" : "current-password"} minLength={registering ? 10 : undefined} required placeholder={registering ? "At least 10 characters" : admin ? "Admin password" : "Your password"} /></label>
          <button className="button primary full" disabled={busy}>{busy ? "Please wait…" : admin ? "Sign in to admin" : registering ? "Create account" : "Sign in"} <ArrowRight size={17} /></button>
        </form>
        {!admin && <p className="switch-auth">{registering ? "Already have an account?" : "New to Roamly?"} <button onClick={() => { setRegistering(!registering); setError(""); }}>{registering ? "Sign in" : "Create an account"}</button></p>}
        <div className="auth-foot"><ShieldCheck size={15} /> Protected, private, and made for better journeys</div>
      </div>
      <Link className="admin-switch" to={admin ? "/" : "/admin/login"}>{admin ? "Customer sign in" : "Administrator sign in"} <ArrowRight size={14} /></Link>
    </section>
  </main>;
}

function Protected({ role, children }) {
  let user;
  try { user = JSON.parse(localStorage.getItem("tourism_user")); } catch { user = null; }
  if (!token() || !user || user.role !== role) return <Navigate to={role === "admin" ? "/admin/login" : "/"} replace />;
  return children;
}

function CustomerDashboard() {
  const [user] = useState(() => JSON.parse(localStorage.getItem("tourism_user") || "{}"));
  const [destinations, setDestinations] = useState([]);
  const [hotels, setHotels] = useState([]);
  const [bookings, setBookings] = useState([]);
  const [itineraries, setItineraries] = useState([]);
  const [myTripsTab, setMyTripsTab] = useState("itineraries");
  const [expandedItineraryId, setExpandedItineraryId] = useState(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [bookingConfirmation, setBookingConfirmation] = useState(null);
  const [bookingSubmitting, setBookingSubmitting] = useState(false);
  const [prefilledStaySearch, setPrefilledStaySearch] = useState(null);
  const [activeMapHotel, setActiveMapHotel] = useState(null);
  const navigate = useNavigate();

  async function load() {
    try {
      const [d, h, b, itins] = await Promise.all([
        json("/destinations"), json("/hotels"), json("/bookings"),
        json("/itineraries").catch(() => []),
      ]);
      setDestinations(d); setHotels(h); setBookings(b); setItineraries(itins);
    } catch (err) { setError(err.message); }
  }

  useEffect(() => { load(); }, []);

  async function book(bookingPayloadOrEvent, destination) {
    if (bookingSubmitting) return null;
    setError("");
    setBookingSubmitting(true);
    let payload = {};
    if (bookingPayloadOrEvent && !bookingPayloadOrEvent.preventDefault && typeof bookingPayloadOrEvent === "object") {
      payload = bookingPayloadOrEvent;
    } else if (bookingPayloadOrEvent && bookingPayloadOrEvent.currentTarget) {
      bookingPayloadOrEvent.preventDefault();
      const form = new FormData(bookingPayloadOrEvent.currentTarget);
      const hotel = hotels.find(item => item.id === Number(form.get("hotel_id")) && item.destination_id === destination.id);
      if (!hotel) {
        setError("Select a hotel for this destination.");
        setBookingSubmitting(false);
        return null;
      }
      payload = {
        destination_id: destination.id,
        hotel_id: hotel.id,
        check_in: form.get("check_in"),
        room_type_id: form.get("room_type_id") ? Number(form.get("room_type_id")) : null,
        check_out: form.get("check_out"),
        guests: Number(form.get("guests")),
        rooms: Number(form.get("rooms") || 1),
      };
    }
    try {
      const result = await json("/bookings", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      setBookingConfirmation(result.booking);
      setSuccess(`Booking confirmed! Reference #${result.booking.booking_reference || result.booking.id} has been added to My Trips.`);
      await load();
      return result.booking;
    } catch (err) {
      setError(err.message);
      return null;
    } finally {
      setBookingSubmitting(false);
    }
  }

  function handleBookAccommodationFromItinerary(itinInfo) {
    setPrefilledStaySearch({
      destinationId: itinInfo.destinationId,
      travelers: itinInfo.travelers,
      rooms: itinInfo.rooms,
      nights: itinInfo.nights,
    });
    const el = document.getElementById("discover") || document.getElementById("hotel-search-section");
    if (el) {
      el.scrollIntoView({ behavior: "smooth" });
    }
  }

  async function cancelHotelBooking(booking) {
    try {
      await json(`/bookings/${booking.id}`, { method: "PATCH", body: JSON.stringify({ status: "cancelled" }) });
      setSuccess(`Booking #${booking.booking_reference || booking.id} was cancelled and its room inventory was restored.`);
      await load();
    } catch (err) { setError(err.message); }
  }

  async function deleteSavedItinerary(itinerary) {
    if (!window.confirm(`Are you sure you want to remove "${itinerary.title}"?`)) return;
    try {
      await json(`/itineraries/${itinerary.id}`, { method: "DELETE" });
      setSuccess(`Itinerary "${itinerary.title}" was removed.`);
      await load();
    } catch (err) { setError(err.message); }
  }

  function logout() { localStorage.removeItem("tourism_token"); localStorage.removeItem("tourism_user"); navigate("/"); }

  return <div className="customer-app">
    <header className="topbar">
      <Link to="/dashboard" className="brand"><Compass /> roamly<span>.</span></Link>
      <nav>
        <a href="#itinerary-planner">AI Trip Planner</a>
        <a href="#discover">Destinations & stays</a>
        <a href="#my-trips">My trips ({itineraries.length + bookings.length})</a>
      </nav>
      <div className="top-user">
        <span className="avatar">{(user.name || "T").slice(0, 1).toUpperCase()}</span>
        <span>{user.name}</span>
        <button className="icon-button" onClick={logout} title="Log out"><LogOut size={18} /></button>
      </div>
    </header>

    <main className="customer-content">
      <section className="welcome">
        <div>
          <span className="eyebrow">YOUR TRAVEL SPACE</span>
          <h1>Good things are <em>out there</em>, {user.name?.split(" ")[0] || "traveler"}.</h1>
          <p>Generate intelligent day-by-day itineraries, explore verified stays, and manage your trips.</p>
        </div>
        <div className="welcome-icon"><Sparkles size={32} /></div>
      </section>

      {error && <div className="alert">{error}<button onClick={() => setError("")}>Dismiss</button></div>}
      {success && <div className="success">{success}<button onClick={() => setSuccess("")}>Dismiss</button></div>}

      {bookingConfirmation && <section className="booking-confirmation" aria-live="polite">
        <div>
          <span className="eyebrow" style={{ color: bookingConfirmation.status === "confirmed" ? "#166534" : "#9a691c" }}>
            {bookingConfirmation.status === "confirmed" ? "✓ BOOKING CONFIRMED (SUCCESS)" : "BOOKING SUBMITTED · AWAITING ADMIN CONFIRMATION"}
          </span>
          <h2>Booking #{bookingConfirmation.booking_reference || bookingConfirmation.id}</h2>
        </div>
        <p><strong>{bookingConfirmation.hotel}</strong> · {bookingConfirmation.destination}</p>
        {bookingConfirmation.hotel_address && <p style={{ fontSize: "0.85rem", color: "#4f685c", margin: "2px 0" }}>📍 {bookingConfirmation.hotel_address}</p>}
        <p>{bookingConfirmation.check_in} — {bookingConfirmation.check_out} · {bookingConfirmation.guests} guests · {bookingConfirmation.rooms} {bookingConfirmation.rooms === 1 ? "room" : "rooms"} · {bookingConfirmation.room_type || "Room"}</p>
        <p>
          Total amount: <strong>₹{bookingConfirmation.amount.toLocaleString("en-IN")}</strong> ·{" "}
          <span className={`status status-${bookingConfirmation.status}`} style={{ fontWeight: 700 }}>
            {bookingConfirmation.status === "confirmed" ? "✓ Confirmed" : "⏳ Pending Confirmation"}
          </span>
        </p>

        {/* Local Transport & Directions Actions */}
        <div className="confirmation-map-actions">
          <span className="confirmation-map-heading">Local Transport & Directions</span>
          <div className="confirmation-btn-group">
            <button
              type="button"
              className="btn-conf-action map-btn"
              onClick={() => setActiveMapHotel({
                name: bookingConfirmation.hotel,
                address: bookingConfirmation.hotel_address,
                destination: bookingConfirmation.destination,
                google_maps_url: bookingConfirmation.hotel_google_maps_url,
                latitude: bookingConfirmation.hotel_latitude,
                longitude: bookingConfirmation.hotel_longitude,
              })}
            >
              <Compass size={13} /> View on Google Maps
            </button>
            <a
              href={getDirectionsUrl({
                name: bookingConfirmation.hotel,
                address: bookingConfirmation.hotel_address,
                destination: bookingConfirmation.destination,
                latitude: bookingConfirmation.hotel_latitude,
                longitude: bookingConfirmation.hotel_longitude,
              })}
              target="_blank"
              rel="noreferrer"
              className="btn-conf-action dir-btn"
            >
              <Navigation size={13} /> Get Directions <ExternalLink size={11} />
            </a>
            <a
              href={getTaxiSearchUrl({
                name: bookingConfirmation.hotel,
                address: bookingConfirmation.hotel_address,
                destination: bookingConfirmation.destination,
              })}
              target="_blank"
              rel="noreferrer"
              className="btn-conf-action taxi-btn"
            >
              <Car size={13} /> Find Taxi <ExternalLink size={11} />
            </a>
            <a
              href={getAutoSearchUrl({
                name: bookingConfirmation.hotel,
                address: bookingConfirmation.hotel_address,
                destination: bookingConfirmation.destination,
              })}
              target="_blank"
              rel="noreferrer"
              className="btn-conf-action auto-btn"
            >
              🛺 Find Auto <ExternalLink size={11} />
            </a>
          </div>
        </div>

        <div style={{ marginTop: "0.85rem", display: "flex", gap: "0.75rem", alignItems: "center" }}>
          <a href="#my-trips" onClick={() => setMyTripsTab("hotels")}>View in My Bookings →</a>
          <button type="button" onClick={() => setBookingConfirmation(null)}>Dismiss</button>
        </div>
      </section>}

      <div id="itinerary-planner">
        <ItineraryGenerator
          destinations={destinations}
          hotels={hotels}
          onItinerarySaved={() => load()}
          onBookAccommodation={handleBookAccommodationFromItinerary}
        />
      </div>

      <section id="discover" className="section-block">
        <div className="section-heading">
          <div>
            <span className="eyebrow">DESTINATIONS & HOTELS</span>
            <h2>Find a place to stay</h2>
          </div>
          <span className="muted">{destinations.length} destinations · {hotels.length} hotels</span>
        </div>
        <DestinationStayList
          destinations={destinations}
          hotels={hotels}
          onBook={book}
          submitting={bookingSubmitting}
          prefilledSearch={prefilledStaySearch}
        />
      </section>

      <section id="my-trips" className="section-block trips-section">
        <div className="section-heading">
          <div>
            <span className="eyebrow">YOUR JOURNEY, ALL IN ONE PLACE</span>
            <h2>My trips</h2>
          </div>
          <div className="trip-tabs-switch">
            <button
              type="button"
              className={`trip-switch-btn ${myTripsTab === "itineraries" ? "active" : ""}`}
              onClick={() => setMyTripsTab("itineraries")}
            >
              <Bookmark size={15} /> Saved Itineraries <span className="count-pill">{itineraries.length}</span>
            </button>
            <button
              type="button"
              className={`trip-switch-btn ${myTripsTab === "hotels" ? "active" : ""}`}
              onClick={() => setMyTripsTab("hotels")}
            >
              <Compass size={15} /> Hotel Bookings <span className="count-pill">{bookings.length}</span>
            </button>
          </div>
        </div>

        {myTripsTab === "itineraries" ? (
          itineraries.length === 0 ? (
            <div className="empty">
              <Bookmark size={26} />
              <span>No saved itineraries yet. Use the AI Trip Planner above to generate and save your plan.</span>
            </div>
          ) : (
            <div className="saved-itineraries-container">
              {itineraries.map(it => {
                const isExpanded = expandedItineraryId === it.id;
                return (
                  <article className="saved-itinerary-card" key={`itin-${it.id}`}>
                    <div className="itin-card-header">
                      {it.destination_image && (
                        <div className="itin-card-image">
                          <img
                            src={it.destination_image}
                            alt={it.destination_name}
                            loading="lazy"
                            onError={(e) => {
                              e.target.onerror = null;
                              e.target.src = "https://images.unsplash.com/photo-1488646953014-85cb44e25828?auto=format&fit=crop&w=800&q=80";
                            }}
                          />
                        </div>
                      )}
                      <div className="itin-card-summary">
                        <div className="itin-badges-line">
                          <span className="itin-badge-location"><MapPin size={11} /> {it.destination_name}</span>
                          <span className={`itin-badge-budget ${it.within_budget ? "within" : "over"}`}>
                            {it.within_budget ? "Within Budget" : "Over Budget"}
                          </span>
                          <span className="itin-badge-engine">
                            {it.generation_mode === "ai_live" ? "AI Live" : "Smart Engine"}
                          </span>
                        </div>
                        <h3>{it.title}</h3>
                        <div className="itin-specs-line">
                          <span><Calendar size={13} /> {it.days} Days</span>
                          <span><Users size={13} /> {it.travelers} {it.travelers === 1 ? "Person" : "Persons"}</span>
                          <span><DollarSign size={13} /> Budget: ₹{Math.round(it.budget_per_person).toLocaleString("en-IN")} / person</span>
                        </div>
                        <div className="itin-breakdown-row">
                          <span title="Accommodation">🏨 Stay: ₹{Math.round(it.estimated_accommodation).toLocaleString("en-IN")}</span>
                          <span title="Transport">🚗 Trans: ₹{Math.round(it.estimated_transport).toLocaleString("en-IN")}</span>
                          <span title="Food">🍽️ Food: ₹{Math.round(it.estimated_food).toLocaleString("en-IN")}</span>
                          <span title="Sightseeing">🎟️ Sights: ₹{Math.round(it.estimated_sightseeing).toLocaleString("en-IN")}</span>
                        </div>
                      </div>
                      <div className="itin-card-right">
                        <span className="itin-price-title">Total Estimated</span>
                        <strong className="itin-price-amount">₹{Math.round(it.total_estimated_cost).toLocaleString("en-IN")}</strong>
                        <div className="itin-action-btns">
                          <button
                            type="button"
                            className="btn-action-schedule"
                            onClick={() => setExpandedItineraryId(isExpanded ? null : it.id)}
                          >
                            {isExpanded ? <span>Hide Schedule <ChevronUp size={13} /></span> : <span>View Plan <ChevronDown size={13} /></span>}
                          </button>
                          <button
                            type="button"
                            className="btn-action-delete"
                            onClick={() => deleteSavedItinerary(it)}
                            title="Delete Saved Itinerary"
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </div>
                    </div>

                    {isExpanded && it.itinerary_data && Array.isArray(it.itinerary_data) && (
                      <div className="itin-schedule-expansion">
                        <div className="expansion-title">
                          <h4>Detailed Daily Schedule</h4>
                          <span className="muted">{it.days} Days Itinerary for {it.travelers} Person(s)</span>
                        </div>
                        <div className="expansion-days-grid">
                          {it.itinerary_data.map(day => (
                            <div className="expansion-day-col" key={day.day}>
                              <div className="day-col-header">
                                <span className="day-pill">Day {day.day}</span>
                                <h5>{day.title}</h5>
                              </div>
                              <div className="day-col-slots">
                                {day.schedule && day.schedule.map((slot, sIdx) => (
                                  <div className="day-slot-card" key={sIdx}>
                                    <div className="slot-timing"><Clock size={11} /> {slot.time_slot}</div>
                                    <h6>{slot.name}</h6>
                                    <p>{slot.description}</p>
                                    {slot.suggested_activity && (
                                      <div className="slot-advice">💡 {slot.suggested_activity}</div>
                                    )}
                                    <div className="slot-footer-tags">
                                      <span>⏱️ {slot.duration_text || `${slot.duration_hours} hrs`}</span>
                                      <span>🎟️ {slot.entry_fee > 0 ? `₹${slot.entry_fee}` : "Free"}</span>
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </article>
                );
              })}
            </div>
          )
        ) : (
          bookings.length === 0 ? (
            <div className="empty"><Compass size={26} /><span>No hotel bookings yet. Find a place to stay above.</span></div>
          ) : (
            <div className="trip-list">
              {bookings.some(b => b.status === "confirmed") && (
                <div style={{ background: "#e8f5ed", border: "1px solid #bce2cb", borderRadius: "8px", padding: "11px 16px", marginBottom: "14px", display: "flex", alignItems: "center", gap: "9px", color: "#166534", fontSize: "12px", fontWeight: "600" }}>
                  <span style={{ fontSize: "15px" }}>🎉</span>
                  <span>
                    You have <strong>{bookings.filter(b => b.status === "confirmed").length} confirmed hotel booking(s)</strong>! Your stay has been approved by the administrator. Use the map buttons below for turn-by-turn directions.
                  </span>
                </div>
              )}
              {bookings.map(b => (
                <article className="trip-row" key={`hotel-${b.id}`} style={{ borderColor: b.status === "confirmed" ? "#bce2cb" : undefined, background: b.status === "confirmed" ? "#fcfffd" : undefined }}>
                  <div className="trip-icon" style={{ background: b.status === "confirmed" ? "#e6f4eb" : undefined, color: b.status === "confirmed" ? "#166534" : undefined }}>
                    <MapPin />
                  </div>
                  <div className="trip-info">
                    <strong>{b.hotel} · {b.destination}</strong>
                    <span>Booking #{b.booking_reference || b.id} · {b.room_type || "Room"} · {b.check_in} — {b.check_out} · {b.guests} guests · {b.rooms} {b.rooms === 1 ? "room" : "rooms"}</span>
                    {b.hotel_address && <small style={{ display: "block", color: "#617c6e", marginTop: "2px" }}>📍 {b.hotel_address}</small>}
                    
                    {b.status === "confirmed" && (
                      <div style={{ display: "inline-flex", alignItems: "center", gap: "6px", background: "#e8f5ed", color: "#166534", padding: "3px 8px", borderRadius: "5px", fontSize: "11px", fontWeight: "600", marginTop: "5px" }}>
                        <span>✓ Booking Confirmed & Verified by Admin · Active Reservation</span>
                      </div>
                    )}
                    {b.status === "pending" && (
                      <div style={{ display: "inline-flex", alignItems: "center", gap: "6px", background: "#fff8ed", color: "#9a691c", padding: "3px 8px", borderRadius: "5px", fontSize: "11px", fontWeight: "500", marginTop: "5px" }}>
                        <span>⏳ Pending Admin Confirmation · Room inventory is held</span>
                      </div>
                    )}

                    <div className="trip-map-actions">
                      <button
                        type="button"
                        className="btn-trip-pill"
                        onClick={() => setActiveMapHotel({
                          name: b.hotel,
                          address: b.hotel_address,
                          destination: b.destination,
                          google_maps_url: b.hotel_google_maps_url,
                          latitude: b.hotel_latitude,
                          longitude: b.hotel_longitude,
                        })}
                        title="View on interactive Google Maps"
                      >
                        <Compass size={11} /> View on Google Maps
                      </button>
                      <a
                        href={getDirectionsUrl({
                          name: b.hotel,
                          address: b.hotel_address,
                          destination: b.destination,
                          latitude: b.hotel_latitude,
                          longitude: b.hotel_longitude,
                        })}
                        target="_blank"
                        rel="noreferrer"
                        className="btn-trip-pill"
                        title="Get directions to hotel on Google Maps"
                      >
                        <Navigation size={11} /> Get Directions
                      </a>
                      <a
                        href={getTaxiSearchUrl({
                          name: b.hotel,
                          address: b.hotel_address,
                          destination: b.destination,
                        })}
                        target="_blank"
                        rel="noreferrer"
                        className="btn-trip-pill"
                        title="Find nearby taxi stands on Google Maps"
                      >
                        <Car size={11} /> Find Taxi
                      </a>
                      <a
                        href={getAutoSearchUrl({
                          name: b.hotel,
                          address: b.hotel_address,
                          destination: b.destination,
                        })}
                        target="_blank"
                        rel="noreferrer"
                        className="btn-trip-pill"
                        title="Find nearby auto rickshaw stands on Google Maps"
                      >
                        🛺 Find Auto
                      </a>
                    </div>
                  </div>
                  <strong>₹{b.amount.toLocaleString("en-IN")}</strong>
                  <span className={`status status-${b.status}`}>
                    {b.status === "confirmed" ? "✓ Confirmed" : b.status === "pending" ? "⏳ Pending" : b.status}
                  </span>
                  {b.status === "pending" && (
                    <button className="cancel-trip" type="button" onClick={() => cancelHotelBooking(b)}>
                      Cancel booking
                    </button>
                  )}
                </article>
              ))}
            </div>
          )
        )}
      </section>
    </main>
    <footer className="customer-footer">Roam thoughtfully. Come back with stories. <span>© Roamly</span></footer>
    {activeMapHotel && (
      <HotelLocationModal
        hotel={activeMapHotel}
        onClose={() => setActiveMapHotel(null)}
      />
    )}
  </div>;
}

export default function App() {
  return <Routes>
    <Route path="/" element={<Auth role="customer" />} />
    <Route path="/admin/login" element={<Auth role="admin" />} />
    <Route path="/dashboard" element={<Protected role="customer"><CustomerDashboard /></Protected>} />
    <Route path="/transport" element={<Navigate to="/dashboard" replace />} />
    <Route path="/admin" element={<Protected role="admin"><Admin /></Protected>} />
    <Route path="*" element={<Navigate to="/" replace />} />
  </Routes>;
}
