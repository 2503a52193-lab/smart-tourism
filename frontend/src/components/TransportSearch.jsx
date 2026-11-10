import { useState, useEffect } from "react";
import {
  Bus, Train, Calendar, MapPin, Users, ArrowRight, ExternalLink,
  ShieldCheck, Clock, Compass, Phone, ChevronRight, X, Sparkles, Filter, AlertCircle
} from "lucide-react";
import { json } from "../api";
import "./TransportSearch.css";

const money = val => `₹${Math.round(Number(val || 0)).toLocaleString("en-IN")}`;

const POPULAR_ROUTES = [
  { from: "Hyderabad", to: "Chennai" },
  { from: "Chennai", to: "Hyderabad" },
  { from: "Hyderabad", to: "Bengaluru" },
  { from: "Bengaluru", to: "Hyderabad" },
  { from: "Hyderabad", to: "Goa" },
  { from: "Goa", to: "Hyderabad" },
  { from: "Delhi", to: "Agra" },
  { from: "Agra", to: "Delhi" },
  { from: "Mumbai", to: "Goa" },
  { from: "Goa", to: "Mumbai" },
  { from: "Chennai", to: "Ooty" },
  { from: "Ooty", to: "Chennai" },
  { from: "Delhi", to: "Manali" },
  { from: "Bengaluru", to: "Mysuru" },
  { from: "Delhi", to: "Varanasi" },
];

export default function TransportSearch({
  prefilledOrigin = "",
  prefilledDestination = "",
  destinations = [],
}) {
  const [category, setCategory] = useState("all"); // "all", "bus", "train"
  const [origin, setOrigin] = useState(prefilledOrigin || "");
  const [destination, setDestination] = useState(prefilledDestination || "");
  const [travelDate, setTravelDate] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() + 1);
    return d.toISOString().split("T")[0];
  });
  const [travelers, setTravelers] = useState(2);
  const [sortBy, setSortBy] = useState("cheapest"); // "cheapest", "expensive", "departure", "fastest"

  const [services, setServices] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [activeModalService, setActiveModalService] = useState(null);

  // Sync if prefilled props change
  useEffect(() => {
    if (prefilledOrigin) setOrigin(prefilledOrigin);
    if (prefilledDestination) setDestination(prefilledDestination);
  }, [prefilledOrigin, prefilledDestination]);

  async function searchTransport(catOverride = null, originOverride = null, destOverride = null) {
    setLoading(true);
    setError("");
    const targetCat = catOverride !== null ? catOverride : category;
    const targetOrigin = originOverride !== null ? originOverride : origin;
    const targetDest = destOverride !== null ? destOverride : destination;

    try {
      const params = new URLSearchParams();
      if (targetCat && targetCat !== "all") params.set("mode", targetCat);
      if (targetOrigin.trim()) params.set("from", targetOrigin.trim());
      if (targetDest.trim()) params.set("to", targetDest.trim());
      if (travelDate) params.set("date", travelDate);
      if (sortBy) params.set("sort", sortBy);

      const data = await json(`/transport/services?${params.toString()}`);
      setServices(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err.message || "Failed to retrieve transport options.");
    } finally {
      setLoading(false);
    }
  }

  // Initial load and category change
  useEffect(() => {
    searchTransport(category);
  }, [category]);

  function handleFormSubmit(e) {
    if (e) e.preventDefault();
    searchTransport(category, origin, destination);
  }

  function handleSelectQuickRoute(route) {
    setOrigin(route.from);
    setDestination(route.to);
    searchTransport(category, route.from, route.to);
  }

  // Sort services client-side as well for instant responsiveness
  let sortedServices = [...services];
  sortedServices.sort((a, b) => {
    if (sortBy === "cheapest") {
      return a.ticket_price - b.ticket_price;
    }
    if (sortBy === "expensive") {
      return b.ticket_price - a.ticket_price;
    }
    if (sortBy === "departure") {
      return (a.departure_time || "").localeCompare(b.departure_time || "");
    }
    if (sortBy === "fastest") {
      const getMins = dStr => {
        if (!dStr) return 9999;
        const hMatch = dStr.match(/(\d+)\s*h/);
        const mMatch = dStr.match(/(\d+)\s*m/);
        return (hMatch ? parseInt(hMatch[1]) * 60 : 0) + (mMatch ? parseInt(mMatch[1]) : 0);
      };
      return getMins(a.duration) - getMins(b.duration);
    }
    return 0;
  });

  const busCount = sortedServices.filter(s => s.mode === "bus").length;
  const trainCount = sortedServices.filter(s => s.mode === "train").length;

  return (
    <section id="transport-search" className="transport-search-block">
      {/* Header */}
      <div className="transport-search-header">
        <span className="eyebrow">TRANSPORT MANAGEMENT SYSTEM</span>
        <h2>Intercity Buses & Trains</h2>
        <p>Explore, compare, and reserve verified Bus and Train schedules and estimated fares across India.</p>
      </div>

      {/* Category Tabs: Buses and Trains Only */}
      <div className="transport-category-pills">
        <button
          type="button"
          className={`cat-pill ${category === "all" ? "active" : ""}`}
          onClick={() => { setCategory("all"); }}
        >
          <Compass size={16} /> All Transport <span className="count-tag">{sortedServices.length}</span>
        </button>
        <button
          type="button"
          className={`cat-pill ${category === "bus" ? "active" : ""}`}
          onClick={() => { setCategory("bus"); }}
        >
          <Bus size={16} /> Buses <span className="count-tag">{busCount}</span>
        </button>
        <button
          type="button"
          className={`cat-pill ${category === "train" ? "active" : ""}`}
          onClick={() => { setCategory("train"); }}
        >
          <Train size={16} /> Trains <span className="count-tag">{trainCount}</span>
        </button>
      </div>

      {/* Search Input Bar */}
      <form className="transport-form-grid" onSubmit={handleFormSubmit}>
        <div className="transport-field-group">
          <label><MapPin size={13} /> Starting City (From)</label>
          <div className="transport-input-wrapper">
            <MapPin size={16} className="field-icon" />
            <input
              type="text"
              placeholder="e.g. Hyderabad, Bengaluru, Delhi, Mumbai, Chennai"
              value={origin}
              onChange={e => setOrigin(e.target.value)}
              list="popular-origins"
            />
            <datalist id="popular-origins">
              <option value="Hyderabad" />
              <option value="Bengaluru" />
              <option value="Chennai" />
              <option value="Goa" />
              <option value="Mumbai" />
              <option value="Delhi" />
              <option value="Agra" />
              <option value="Jaipur" />
              <option value="Varanasi" />
              <option value="Rishikesh" />
              <option value="Mysuru" />
              <option value="Ooty" />
              <option value="Manali" />
              <option value="Kerala" />
              <option value="Tamil Nadu" />
            </datalist>
          </div>
        </div>

        {/* Swap / Reverse Route Button */}
        <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "center", paddingBottom: "0.25rem" }}>
          <button
            type="button"
            className="button secondary"
            style={{
              padding: "0.55rem 0.85rem",
              fontSize: "0.82rem",
              display: "flex",
              alignItems: "center",
              gap: "0.35rem",
              borderRadius: "8px",
              background: "#f1f5f9",
              border: "1px solid #cbd5e1",
              cursor: "pointer",
              fontWeight: 600,
              color: "#334155"
            }}
            title="Swap Starting City and Destination to reverse route"
            onClick={() => {
              const newOrigin = destination;
              const newDest = origin;
              setOrigin(newOrigin);
              setDestination(newDest);
              searchTransport(category, newOrigin, newDest);
            }}
          >
            ⇄ Swap
          </button>
        </div>

        <div className="transport-field-group">
          <label><MapPin size={13} /> Destination (To)</label>
          <div className="transport-input-wrapper">
            <MapPin size={16} className="field-icon" />
            <input
              type="text"
              placeholder="e.g. Goa, Chennai, Mysuru, Agra, Ooty, Manali"
              value={destination}
              onChange={e => setDestination(e.target.value)}
              list="popular-destinations"
            />
            <datalist id="popular-destinations">
              {destinations && destinations.map(d => (
                <option key={d.id} value={d.name} />
              ))}
              <option value="Goa" />
              <option value="Chennai" />
              <option value="Mysuru" />
              <option value="Agra" />
              <option value="Ooty" />
              <option value="Manali" />
              <option value="Jaipur" />
              <option value="Varanasi" />
              <option value="Rishikesh" />
              <option value="Hyderabad" />
              <option value="Bengaluru" />
              <option value="Mumbai" />
              <option value="Delhi" />
              <option value="Kerala" />
              <option value="Tamil Nadu" />
            </datalist>
          </div>
        </div>

        <div className="transport-field-group">
          <label><Calendar size={13} /> Travel Date</label>
          <div className="transport-input-wrapper">
            <Calendar size={16} className="field-icon" />
            <input
              type="date"
              value={travelDate}
              onChange={e => setTravelDate(e.target.value)}
            />
          </div>
        </div>

        <div className="transport-field-group">
          <label><Users size={13} /> Number of Travellers</label>
          <div className="transport-input-wrapper">
            <Users size={16} className="field-icon" />
            <select
              value={travelers}
              onChange={e => setTravelers(Number(e.target.value))}
            >
              {[1, 2, 3, 4, 5, 6, 8, 10].map(n => (
                <option key={n} value={n}>{n} {n === 1 ? "Traveller" : "Travellers"}</option>
              ))}
            </select>
          </div>
        </div>

        <button type="submit" className="transport-search-submit" disabled={loading}>
          {loading ? "Searching…" : "Search"} <ArrowRight size={16} />
        </button>
      </form>

      {/* Popular Route Shortcuts */}
      <div className="quick-routes-row">
        <span>Popular Corridors:</span>
        {POPULAR_ROUTES.map((r, idx) => (
          <button
            key={idx}
            type="button"
            className="quick-route-chip"
            onClick={() => handleSelectQuickRoute(r)}
          >
            {r.from} ➔ {r.to}
          </button>
        ))}
      </div>

      {error && <div className="alert mt-3 mb-3">{error}</div>}

      {/* Results Sort & Count Bar */}
      <div className="transport-results-topline">
        <span className="transport-results-count">
          <strong>Found {sortedServices.length} transport options</strong> ({busCount} {busCount === 1 ? "bus" : "buses"}, {trainCount} {trainCount === 1 ? "train" : "trains"})
          {origin ? ` from ${origin}` : ""} {destination ? ` to ${destination}` : ""} for {travelers} {travelers === 1 ? "traveller" : "travellers"}
        </span>
        <div className="transport-sort-controls">
          <span>Sort by:</span>
          <select
            className="transport-sort-select"
            value={sortBy}
            onChange={e => {
              setSortBy(e.target.value);
              searchTransport(category, origin, destination);
            }}
          >
            <option value="cheapest">Lowest Fare</option>
            <option value="expensive">Highest Fare</option>
            <option value="departure">Departure Time (Earliest)</option>
            <option value="fastest">Duration (Fastest First)</option>
          </select>
        </div>
      </div>

      {/* Cards List */}
      {sortedServices.length === 0 ? (
        <div className="transport-empty-state">
          <Compass size={38} />
          <h4>No Transport Options Found</h4>
          <p>
            We couldn't find scheduled demo {category !== "all" ? category : "bus or train"} routes matching
            {origin ? ` "${origin}"` : ""} to {destination ? ` "${destination}"` : ""}.
          </p>
          <p style={{ fontSize: "0.88rem", color: "#617d6f", marginTop: "-0.5rem" }}>
            Try popular test corridors: <strong>Hyderabad ➔ Goa</strong>, <strong>Hyderabad ➔ Chennai</strong>, <strong>Bengaluru ➔ Mysuru</strong>, <strong>Delhi ➔ Agra</strong>, <strong>Mumbai ➔ Goa</strong>, or <strong>Chennai ➔ Ooty</strong>.
          </p>
          <button
            type="button"
            className="button secondary"
            onClick={() => {
              setOrigin("");
              setDestination("");
              setCategory("all");
              searchTransport("all", "", "");
            }}
          >
            View All Catalog Routes
          </button>
        </div>
      ) : (
        <div className="transport-cards-list">
          {sortedServices.map(item => {
            const isBus = item.mode === "bus";
            const isTrain = item.mode === "train";
            const perPersonFare = item.ticket_price;
            const totalTripFare = perPersonFare * travelers;

            return (
              <article key={item.id} className="transport-card">
                {/* Col 1: Operator / Train Number and Type */}
                <div className="t-col-operator">
                  <div style={{ display: "flex", alignItems: "center", gap: "0.45rem", flexWrap: "wrap" }}>
                    <span className={`t-category-badge badge-${isBus ? "bus" : "train"}`}>
                      {isBus && <Bus size={12} />}
                      {isTrain && <Train size={12} />}
                      {isBus ? "Bus" : "Train"}
                    </span>
                    <span className="t-verify-pill estimate">
                      <ShieldCheck size={11} /> Sample / Demo Service
                    </span>
                    {item.booking_status && (
                      <span className="t-status-pill" style={{
                        fontSize: "0.72rem",
                        padding: "2px 8px",
                        borderRadius: "10px",
                        background: item.booking_status.toLowerCase().includes("fast") || item.booking_status.toLowerCase().includes("few") ? "#fef3c7" : "#e6f4ea",
                        color: item.booking_status.toLowerCase().includes("fast") || item.booking_status.toLowerCase().includes("few") ? "#92400e" : "#137333",
                        fontWeight: 600,
                      }}>
                        {item.booking_status}
                      </span>
                    )}
                  </div>
                  <h4 className="t-operator-name">
                    {isTrain ? (item.service_name || item.operator) : item.operator}
                  </h4>
                  {isBus && item.service_name && <span className="t-service-name">{item.service_name}</span>}
                  {item.service_type && <span className="t-type-tag">{item.service_type}</span>}
                  {item.available_seats && (
                    <span style={{ fontSize: "0.8rem", color: "#456153", display: "inline-flex", alignItems: "center", gap: "0.25rem", marginTop: "2px" }}>
                      💺 {item.available_seats} demo seats available
                    </span>
                  )}
                </div>

                {/* Col 2: Route, Timings, Duration, Boarding & Dropping Points */}
                <div className="t-col-schedule">
                  <div className="t-route-visual">
                    <div className="t-node origin">
                      <span className="t-time">{item.departure_time}</span>
                      <span className="t-station" title={item.origin_station || item.origin}>
                        {item.origin_station || item.origin}
                      </span>
                    </div>

                    <div className="t-route-line-wrap">
                      <span className="t-duration-label"><Clock size={11} /> {item.duration || "Direct"}</span>
                      <div className="t-route-line" />
                      {item.distance_km && <span className="t-distance-label">{item.distance_km}</span>}
                    </div>

                    <div className="t-node destination">
                      <span className="t-time">{item.arrival_time}</span>
                      <span className="t-station" title={item.destination_station || item.destination}>
                        {item.destination_station || item.destination}
                      </span>
                    </div>
                  </div>

                  {/* Connecting Railhead Notice for Hill Stations */}
                  {item.mode === "train" && (item.destination === "Ooty" || item.destination === "Manali" || item.destination_station?.includes("MTP") || item.destination_station?.includes("Chandigarh") || item.destination_station?.includes("Kalka")) && (
                    <div style={{
                      fontSize: "0.76rem",
                      color: "#92400e",
                      background: "#fef3c7",
                      padding: "4px 8px",
                      borderRadius: "6px",
                      margin: "4px 0",
                      border: "1px solid #fde68a",
                      display: "flex",
                      alignItems: "center",
                      gap: "0.3rem"
                    }}>
                      <AlertCircle size={12} />
                      <span><strong>Connecting Rail Service:</strong> Express train terminates at nearby railhead with road / toy-train transfer to {item.destination}.</span>
                    </div>
                  )}

                  {/* Boarding and Dropping Points */}
                  <div className="t-boarding-dropping-row" style={{ fontSize: "0.78rem", color: "#4f695c", margin: "6px 0 2px" }}>
                    {item.boarding_point && (
                      <div><strong>Boarding:</strong> {item.boarding_point}</div>
                    )}
                    {item.dropping_point && (
                      <div><strong>Dropping:</strong> {item.dropping_point}</div>
                    )}
                  </div>

                  {/* Available Classes */}
                  {item.available_classes && (
                    <div className="t-classes-row">
                      <span style={{ fontSize: "0.74rem", color: "#617d6f", alignSelf: "center" }}>Classes:</span>
                      {item.available_classes.split(",").map((c, idx) => (
                        <span key={idx} className="t-class-pill">{c.trim()}</span>
                      ))}
                    </div>
                  )}

                  {item.contact_number && (
                    <span style={{ fontSize: "0.78rem", color: "#5d7568", display: "inline-flex", alignItems: "center", gap: "0.3rem" }}>
                      <Phone size={12} /> Helpline: {item.contact_number}
                    </span>
                  )}
                </div>

                {/* Col 3: Price and Total Fare Calculation */}
                <div className="t-col-action">
                  <div className="t-price-box">
                    <div style={{ display: "flex", alignItems: "baseline", gap: "0.25rem" }}>
                      <span className="t-fare-amount">{money(perPersonFare)}</span>
                      <span className="t-fare-unit">/ person</span>
                    </div>
                    <div className="t-total-calc-box" style={{
                      marginTop: "4px",
                      padding: "4px 8px",
                      background: "#f0fdf4",
                      borderRadius: "6px",
                      border: "1px solid #bbf7d0",
                      fontSize: "0.82rem",
                      color: "#166534"
                    }}>
                      <strong>Total: {money(totalTripFare)}</strong>
                      <span style={{ display: "block", fontSize: "0.74rem", color: "#15803d" }}>
                        ({money(perPersonFare)} × {travelers} {travelers === 1 ? "traveller" : "travellers"})
                      </span>
                    </div>
                  </div>

                  <div className="t-action-buttons">
                    <button
                      type="button"
                      className="btn-t-details"
                      onClick={() => setActiveModalService(item)}
                    >
                      View Details
                    </button>
                    {item.booking_url ? (
                      <a
                        href={item.booking_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="btn-t-book"
                        title={isTrain ? "Book tickets on IRCTC official portal" : "Book seats on official bus portal"}
                      >
                        Book on Official Site <ExternalLink size={13} />
                      </a>
                    ) : (
                      <button
                        type="button"
                        className="btn-t-book"
                        onClick={() => setActiveModalService(item)}
                      >
                        Book Details
                      </button>
                    )}
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      )}

      {/* Details Modal */}
      {activeModalService && (
        <div className="transport-modal-overlay" onClick={() => setActiveModalService(null)}>
          <div className="transport-modal-card" onClick={e => e.stopPropagation()}>
            <button
              type="button"
              className="t-modal-close"
              onClick={() => setActiveModalService(null)}
            >
              <X size={18} />
            </button>

            <div className="t-modal-header">
              <span className={`t-category-badge badge-${activeModalService.mode === "bus" ? "bus" : "train"}`}>
                {activeModalService.mode.toUpperCase()}
              </span>
              <h3>{activeModalService.operator} {activeModalService.service_name ? `· ${activeModalService.service_name}` : ""}</h3>
              <p>{activeModalService.origin} to {activeModalService.destination} · Sample Demo Service</p>
            </div>

            <div className="t-modal-grid">
              <div className="t-modal-item">
                <span className="t-modal-label">Departure</span>
                <span className="t-modal-val">{activeModalService.departure_time}</span>
                <small style={{ color: "#617d6f" }}>{activeModalService.origin_station || activeModalService.origin}</small>
              </div>

              <div className="t-modal-item">
                <span className="t-modal-label">Arrival</span>
                <span className="t-modal-val">{activeModalService.arrival_time}</span>
                <small style={{ color: "#617d6f" }}>{activeModalService.destination_station || activeModalService.destination}</small>
              </div>

              <div className="t-modal-item">
                <span className="t-modal-label">Journey Duration</span>
                <span className="t-modal-val">{activeModalService.duration || "Direct route"}</span>
              </div>

              <div className="t-modal-item">
                <span className="t-modal-label">Estimated Distance</span>
                <span className="t-modal-val">{activeModalService.distance_km || "Regional route"}</span>
              </div>

              <div className="t-modal-item">
                <span className="t-modal-label">Service / Vehicle Type</span>
                <span className="t-modal-val">{activeModalService.service_type || "Standard Class"}</span>
              </div>

              <div className="t-modal-item">
                <span className="t-modal-label">Demo Booking Status</span>
                <span className="t-modal-val" style={{ color: "#164e37", fontWeight: 700 }}>
                  {activeModalService.booking_status || `Available (${activeModalService.available_seats || 30} seats)`}
                </span>
              </div>

              {activeModalService.boarding_point && (
                <div className="t-modal-item" style={{ gridColumn: "1 / -1" }}>
                  <span className="t-modal-label">Boarding Point</span>
                  <span className="t-modal-val" style={{ fontSize: "0.92rem" }}>{activeModalService.boarding_point}</span>
                </div>
              )}

              {activeModalService.dropping_point && (
                <div className="t-modal-item" style={{ gridColumn: "1 / -1" }}>
                  <span className="t-modal-label">Dropping Point</span>
                  <span className="t-modal-val" style={{ fontSize: "0.92rem" }}>{activeModalService.dropping_point}</span>
                </div>
              )}

              <div className="t-modal-item" style={{ gridColumn: "1 / -1" }}>
                <span className="t-modal-label">Fare Calculation</span>
                <span className="t-modal-val" style={{ color: "#164e37" }}>
                  {money(activeModalService.ticket_price)} per person · <strong>Total {money(activeModalService.ticket_price * travelers)}</strong> for {travelers} travellers
                </span>
              </div>
            </div>

            {/* Train Class Fares Breakdown if available */}
            {activeModalService.class_fares && Object.keys(activeModalService.class_fares).length > 0 && (
              <div style={{ marginTop: "1rem" }}>
                <h5 style={{ margin: "0 0 0.5rem", color: "#1e382b" }}>Available Classes & Estimated Fares</h5>
                <table className="t-modal-fares-table">
                  <thead>
                    <tr>
                      <th>Travel Class</th>
                      <th>Class Description</th>
                      <th>Fare per Passenger</th>
                      <th>Total ({travelers} travellers)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(activeModalService.class_fares).map(([cls, fare]) => (
                      <tr key={cls}>
                        <td><strong>{cls}</strong></td>
                        <td>
                          {cls === "1A" ? "AC First Class" :
                           cls === "2A" ? "AC 2-Tier Sleeper" :
                           cls === "3A" ? "AC 3-Tier Sleeper" :
                           cls === "SL" ? "Sleeper Class" :
                           cls === "CC" ? "AC Chair Car" :
                           cls === "EC" ? "Executive Chair Car" :
                           cls === "2S" ? "Second Seater" :
                           cls === "EV" ? "Vistadome AC Coach" :
                           cls === "FC" ? "First Class Heritage" : cls}
                        </td>
                        <td><strong>{money(fare)}</strong></td>
                        <td><strong>{money(Number(fare) * travelers)}</strong></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {activeModalService.contact_number && (
              <div style={{ margin: "1rem 0", fontSize: "0.88rem", color: "#324b3e" }}>
                <strong>Direct Operator Helpline:</strong> {activeModalService.contact_number}
              </div>
            )}

            <div className="t-modal-portal-note">
              <strong>Official Booking Portal Guidance:</strong>
              {activeModalService.mode === "train" ? (
                <span> Confirmed train tickets can be booked online via Indian Railways official portal (IRCTC). Enter your IRCTC account details and passenger list to complete your booking with official PNR generation.</span>
              ) : (
                <span> Bus tickets are booked through the verified operator's booking portal or RTC official booking system. Check seat layouts and pickup points prior to checkout.</span>
              )}
            </div>

            <div className="t-modal-actions">
              <button
                type="button"
                className="btn-t-details"
                onClick={() => setActiveModalService(null)}
              >
                Close
              </button>
              {activeModalService.booking_url && (
                <a
                  href={activeModalService.booking_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn-t-book"
                >
                  Continue to Official Booking Website <ExternalLink size={14} />
                </a>
              )}
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
