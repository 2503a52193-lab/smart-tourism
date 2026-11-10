import { useState, useRef, useMemo } from "react";
import {
  ArrowRight, Sparkles, MapPin, Calendar, Users, DollarSign, Clock,
  Utensils, Building2, Ticket, CheckCircle2, AlertTriangle,
  Bookmark, RefreshCw, Edit3, ChevronDown, ChevronUp, Info, Compass,
  Bus, Train, ExternalLink, ShieldCheck, X, Zap, Check
} from "lucide-react";
import { json } from "../api";
import "./ItineraryGenerator.css";
import "./TransportSearch.css";

const money = amount => `₹${Math.round(Number(amount || 0)).toLocaleString("en-IN")}`;
const todayIso = new Date().toISOString().split("T")[0];

function parseDurationMinutes(durStr) {
  if (!durStr) return 9999;
  const hMatch = durStr.match(/(\d+)\s*h/);
  const mMatch = durStr.match(/(\d+)\s*m/);
  return (hMatch ? parseInt(hMatch[1]) * 60 : 0) + (mMatch ? parseInt(mMatch[1]) : 0);
}

function formatJourneyDateTime(dateIsoStr, depTime, arrTimeStr) {
  if (!dateIsoStr) return { depDateText: "", arrDateText: "", isNextDay: false, cleanArrTime: arrTimeStr };
  
  const [y, m, d] = dateIsoStr.split("-").map(Number);
  const depDateObj = new Date(y, m - 1, d);
  const dateOptions = { weekday: "short", day: "numeric", month: "short", year: "numeric" };
  const depDateText = depDateObj.toLocaleDateString("en-IN", dateOptions);
  
  let daysOffset = 0;
  let cleanArrTime = arrTimeStr || "";
  if (arrTimeStr && (arrTimeStr.includes("+1") || arrTimeStr.toLowerCase().includes("next"))) {
    daysOffset = 1;
    cleanArrTime = arrTimeStr.replace(/\(\+1\s*day\)/i, "").replace(/\(\+1d\)/i, "").trim();
  } else if (arrTimeStr && arrTimeStr.includes("+2")) {
    daysOffset = 2;
    cleanArrTime = arrTimeStr.replace(/\(\+2\s*days\)/i, "").replace(/\(\+2d\)/i, "").trim();
  }
  
  const arrDateObj = new Date(y, m - 1, d + daysOffset);
  const arrDateText = arrDateObj.toLocaleDateString("en-IN", dateOptions);
  
  return {
    depDateText,
    arrDateText,
    isNextDay: daysOffset > 0,
    daysOffset,
    cleanArrTime,
  };
}

export default function ItineraryGenerator({ destinations, hotels, onItinerarySaved, onBookAccommodation, onSearchTransport }) {
  const [budget, setBudget] = useState("12000");
  const [travelers, setTravelers] = useState(2);
  const [days, setDays] = useState(3);
  const [origin, setOrigin] = useState("");
  const [destinationId, setDestinationId] = useState("");
  const [selectedInterests, setSelectedInterests] = useState([]);
  const [activeTab, setActiveTab] = useState("itinerary"); // "itinerary", "hotels", or "transport"
  const [activeItinTransportCategory, setActiveItinTransportCategory] = useState("all");
  const [selectedTransportModal, setSelectedTransportModal] = useState(null);

  // Transport Only Mode States
  const [transportOrigin, setTransportOrigin] = useState("Hyderabad");
  const [transportDestination, setTransportDestination] = useState("Chennai");
  const [transportDate, setTransportDate] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() + 1);
    return d.toISOString().split("T")[0];
  });
  const [transportTravelers, setTransportTravelers] = useState(2);
  const [transportSortBy, setTransportSortBy] = useState("cheapest");
  const [transportCategory, setTransportCategory] = useState("all");
  const [transportLoading, setTransportLoading] = useState(false);
  const [transportError, setTransportError] = useState("");
  const [transportResult, setTransportResult] = useState(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [itineraryResult, setItineraryResult] = useState(null);
  const [hotelResult, setHotelResult] = useState(null);
  const [saving, setSaving] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);
  const [savedItineraryId, setSavedItineraryId] = useState(null);

  const formRef = useRef(null);
  const resultsRef = useRef(null);

  const availableInterests = [
    "Heritage & History", "Nature & Scenic", "Beaches",
    "Culture & Arts", "Spiritual & Temples", "Food & Culinary"
  ];

  function toggleInterest(interest) {
    setSelectedInterests(prev =>
      prev.includes(interest) ? prev.filter(i => i !== interest) : [...prev, interest]
    );
  }

  async function handleGenerateItinerary(e, overrideDestId = null) {
    if (e) e.preventDefault();
    setLoading(true);
    setError("");
    setSavedSuccess(false);
    const targetDestId = overrideDestId !== null ? overrideDestId : (destinationId || null);

    try {
      const res = await json("/itineraries/generate", {
        method: "POST",
        body: JSON.stringify({
          budget_per_person: Number(budget),
          travelers: Number(travelers),
          days: Number(days),
          destination_id: targetDestId ? Number(targetDestId) : null,
          origin: origin.trim(),
          interests: selectedInterests,
        }),
      });
      setItineraryResult(res);
      setActiveTab("itinerary");
      setTimeout(() => {
        resultsRef.current?.scrollIntoView({ behavior: "smooth" });
      }, 100);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleFindHotels(e) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const res = await json("/assistant/recommendations", {
        method: "POST",
        body: JSON.stringify({
          budget_per_person: Number(budget),
          travelers: Number(travelers),
          nights: Number(days),
          destination_id: destinationId || null,
        }),
      });
      setHotelResult(res);
      setActiveTab("hotels");
      setTimeout(() => {
        resultsRef.current?.scrollIntoView({ behavior: "smooth" });
      }, 100);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleSearchTransportOnly(e, origOverride = null, destOverride = null) {
    if (e) e.preventDefault();
    const fromCity = (origOverride !== null ? origOverride : transportOrigin).trim();
    const toCity = (destOverride !== null ? destOverride : transportDestination).trim();

    if (!fromCity || !toCity) {
      setTransportError("Please enter both a starting city and a destination.");
      return;
    }
    if (fromCity.toLowerCase() === toCity.toLowerCase()) {
      setTransportError("Starting city and destination must be different. Please choose two distinct locations.");
      return;
    }
    if (transportDate < todayIso) {
      setTransportError("Please choose a current or future travel date. Past dates cannot be selected.");
      return;
    }

    setTransportLoading(true);
    setTransportError("");
    try {
      const params = new URLSearchParams({
        from: fromCity,
        to: toCity,
        date: transportDate,
        mode: "all",
        sort: transportSortBy,
      });
      const data = await json(`/transport/services?${params.toString()}`);
      setTransportResult({
        origin: fromCity,
        destination: toCity,
        date: transportDate,
        travelers: Number(transportTravelers),
        services: Array.isArray(data) ? data : [],
      });
      setActiveTab("transport");
      setTimeout(() => {
        resultsRef.current?.scrollIntoView({ behavior: "smooth" });
      }, 100);
    } catch (err) {
      setTransportError(err.message || "Failed to search transport options.");
    } finally {
      setTransportLoading(false);
    }
  }

  async function saveCurrentItinerary() {
    if (!itineraryResult || saving) return;
    setSaving(true);
    setError("");
    try {
      const res = await json("/itineraries", {
        method: "POST",
        body: JSON.stringify({
          destination_id: itineraryResult.destination.id,
          title: itineraryResult.title,
          days: itineraryResult.days,
          travelers: itineraryResult.travelers,
          budget_per_person: itineraryResult.budget_per_person,
          total_budget: itineraryResult.total_budget,
          estimated_accommodation: itineraryResult.estimated_accommodation,
          estimated_transport: itineraryResult.estimated_transport,
          estimated_food: itineraryResult.estimated_food,
          estimated_sightseeing: itineraryResult.estimated_sightseeing,
          total_estimated_cost: itineraryResult.total_estimated_cost,
          cost_per_person: itineraryResult.cost_per_person,
          remaining_budget: itineraryResult.remaining_budget,
          within_budget: itineraryResult.within_budget,
          itinerary_data: itineraryResult.daily_schedule,
          generation_mode: itineraryResult.generation_mode,
        }),
      });
      setSavedSuccess(true);
      setSavedItineraryId(res.itinerary.id);
      if (onItinerarySaved) onItinerarySaved(res.itinerary);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  function handleEditInputs() {
    formRef.current?.scrollIntoView({ behavior: "smooth" });
  }

  const hotelOptions = hotelResult
    ? (hotelResult.matches.length ? hotelResult.matches : hotelResult.alternatives)
    : [];

  const sortedServices = useMemo(() => {
    if (!transportResult?.services) return [];
    const list = [...transportResult.services];
    if (transportSortBy === "cheapest") {
      list.sort((a, b) => a.ticket_price - b.ticket_price);
    } else if (transportSortBy === "expensive") {
      list.sort((a, b) => b.ticket_price - a.ticket_price);
    } else if (transportSortBy === "departure_asc") {
      list.sort((a, b) => (a.departure_time || "").localeCompare(b.departure_time || ""));
    } else if (transportSortBy === "duration_asc") {
      list.sort((a, b) => parseDurationMinutes(a.duration) - parseDurationMinutes(b.duration));
    }
    return list;
  }, [transportResult, transportSortBy]);

  const transportBuses = useMemo(() => {
    return sortedServices.filter(s => s.mode === "bus");
  }, [sortedServices]);

  const transportTrains = useMemo(() => {
    return sortedServices.filter(s => s.mode === "train");
  }, [sortedServices]);

  const aiRecommendations = useMemo(() => {
    if (!transportResult?.services || transportResult.services.length === 0) return null;
    const all = transportResult.services;
    const buses = all.filter(s => s.mode === "bus");
    const trains = all.filter(s => s.mode === "train");

    const cheapestBus = buses.length > 0
      ? [...buses].sort((a, b) => a.ticket_price - b.ticket_price)[0]
      : null;

    const cheapestTrain = trains.length > 0
      ? [...trains].sort((a, b) => a.ticket_price - b.ticket_price)[0]
      : null;

    const fastest = [...all].sort((a, b) => parseDurationMinutes(a.duration) - parseDurationMinutes(b.duration))[0];
    const bestValue = [...all].sort((a, b) => a.ticket_price - b.ticket_price)[0];

    return {
      cheapestBus,
      cheapestTrain,
      fastest,
      bestValue,
    };
  }, [transportResult]);

  return (
    <section className="section-block itinerary-generator-section" ref={formRef}>
      <div className="itinerary-header">
        <div className="itinerary-title-badge">
          <Sparkles size={15} /> AI TRIP ITINERARY & STAY PLANNER
        </div>
        <h2>Generate your tailored travel plan</h2>
        <p>
          Enter your trip parameters to receive a customized day-by-day itinerary with attractions,
          activities, visit durations, and an itemized cost estimate.
        </p>
      </div>

      <div className="planner-tabs">
        <button
          type="button"
          className={`tab-btn ${activeTab === "itinerary" ? "active" : ""}`}
          onClick={() => setActiveTab("itinerary")}
        >
          <Sparkles size={16} /> Complete AI Itinerary & Budget
        </button>
        <button
          type="button"
          className={`tab-btn ${activeTab === "hotels" ? "active" : ""}`}
          onClick={() => setActiveTab("hotels")}
        >
          <Building2 size={16} /> Hotels Only
        </button>
        <button
          type="button"
          className={`tab-btn ${activeTab === "transport" ? "active" : ""}`}
          onClick={() => setActiveTab("transport")}
        >
          <Bus size={16} /> Transport Only
        </button>
      </div>

      {activeTab !== "transport" && (
        <form className="itinerary-form" onSubmit={activeTab === "itinerary" ? handleGenerateItinerary : handleFindHotels}>
          <div className="form-grid">
            <label className="form-field">
              <span className="field-label"><DollarSign size={13} /> Budget per person (₹)</span>
              <input
                type="number"
                min="100"
                max="10000000"
                step="50"
                required
                value={budget}
                onChange={e => setBudget(e.target.value)}
                placeholder="e.g. 12000"
              />
              <span className="field-hint">Lodging, transport, food & tickets</span>
            </label>

            <label className="form-field">
              <span className="field-label"><Users size={13} /> People travelling</span>
              <input
                type="number"
                min="1"
                max="20"
                required
                value={travelers}
                onChange={e => setTravelers(e.target.value)}
              />
              <span className="field-hint">Group or solo travellers</span>
            </label>

            <label className="form-field">
              <span className="field-label"><Calendar size={13} /> Trip duration (Days)</span>
              <input
                type="number"
                min="1"
                max="14"
                required
                value={days}
                onChange={e => setDays(e.target.value)}
              />
              <span className="field-hint">1 to 14 days</span>
            </label>

            <label className="form-field">
              <span className="field-label"><Compass size={13} /> Starting City (Origin) <span className="opt-tag">Recommended</span></span>
              <input
                type="text"
                value={origin}
                onChange={e => setOrigin(e.target.value)}
                placeholder="e.g. Hyderabad, Bengaluru, Delhi, Mumbai, Chennai"
                list="itin-starting-cities"
              />
              <datalist id="itin-starting-cities">
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
              <span className="field-hint">Used for matching buses & trains and budget transit calculation</span>
            </label>

            <label className="form-field">
              <span className="field-label"><MapPin size={13} /> Destination <span className="opt-tag">Optional</span></span>
              <select
                value={destinationId}
                onChange={e => setDestinationId(e.target.value)}
              >
                <option value="">Any destination (AI Recommends)</option>
                {destinations.map(d => (
                  <option key={d.id} value={d.id}>{d.name} ({d.state || d.region})</option>
                ))}
              </select>
              <span className="field-hint">Leave blank for recommendations</span>
            </label>
          </div>

          {activeTab === "itinerary" && (
            <div className="interests-selector">
              <span className="interests-title">Trip Interests & Style (Optional):</span>
              <div className="interests-chips">
                {availableInterests.map(interest => {
                  const isSelected = selectedInterests.includes(interest);
                  return (
                    <button
                      key={interest}
                      type="button"
                      className={`interest-chip ${isSelected ? "selected" : ""}`}
                      onClick={() => toggleInterest(interest)}
                    >
                      {interest}
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          <div className="form-actions">
            <button
              type="submit"
              className="button primary generate-btn"
              disabled={loading}
            >
              {loading ? (
                <span><RefreshCw size={16} className="spin-icon" /> Generating Itinerary…</span>
              ) : activeTab === "itinerary" ? (
                <span>Generate AI Itinerary <ArrowRight size={16} /></span>
              ) : (
                <span>Find Hotels <ArrowRight size={16} /></span>
              )}
            </button>
          </div>
        </form>
      )}

      {/* TRANSPORT ONLY SEARCH FORM */}
      {activeTab === "transport" && (
        <form className="itinerary-form transport-only-form" onSubmit={handleSearchTransportOnly}>
          <div className="form-grid">
            <label className="form-field">
              <span className="field-label"><Compass size={13} /> Starting City (From)</span>
              <input
                type="text"
                required
                value={transportOrigin}
                onChange={e => setTransportOrigin(e.target.value)}
                placeholder="e.g. Hyderabad, Bengaluru, Delhi, Mumbai, Chennai"
                list="transport-only-origins"
              />
              <datalist id="transport-only-origins">
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
              <span className="field-hint">City of departure</span>
            </label>

            {/* Reverse / Swap Direction Button */}
            <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "center", paddingBottom: "1.75rem" }}>
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
                title="Swap Starting City and Destination to reverse direction"
                onClick={() => {
                  const newOrig = transportDestination;
                  const newDest = transportOrigin;
                  setTransportOrigin(newOrig);
                  setTransportDestination(newDest);
                  if (transportResult) {
                    handleSearchTransportOnly(null, newOrig, newDest);
                  }
                }}
              >
                ⇄ Swap
              </button>
            </div>

            <label className="form-field">
              <span className="field-label"><MapPin size={13} /> Destination City (To)</span>
              <input
                type="text"
                required
                value={transportDestination}
                onChange={e => setTransportDestination(e.target.value)}
                placeholder="e.g. Chennai, Goa, Bengaluru, Agra, Ooty, Manali"
                list="transport-only-dests"
              />
              <datalist id="transport-only-dests">
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
              <span className="field-hint">Arrival destination</span>
            </label>

            <label className="form-field">
              <span className="field-label"><Calendar size={13} /> Travel Date</span>
              <input
                type="date"
                required
                min={todayIso}
                value={transportDate}
                onChange={e => setTransportDate(e.target.value)}
              />
              <span className="field-hint">Daily demo departures available for all dates</span>
            </label>

            <label className="form-field">
              <span className="field-label"><Users size={13} /> Number of Travellers</span>
              <select
                value={transportTravelers}
                onChange={e => setTransportTravelers(Number(e.target.value))}
              >
                {[1, 2, 3, 4, 5, 6, 8, 10, 12, 15, 20].map(n => (
                  <option key={n} value={n}>{n} {n === 1 ? "Traveller" : "Travellers"}</option>
                ))}
              </select>
              <span className="field-hint">Group fare calculated dynamically</span>
            </label>
          </div>

          <div className="form-actions">
            <button
              type="submit"
              className="button primary generate-btn"
              disabled={transportLoading}
            >
              {transportLoading ? (
                <span><RefreshCw size={16} className="spin-icon" /> Searching Buses & Trains…</span>
              ) : (
                <span>Search Transport <ArrowRight size={16} /></span>
              )}
            </button>
          </div>
        </form>
      )}

      {error && <div className="alert mt-4" role="alert">{error}</div>}
      {activeTab === "transport" && transportError && <div className="alert mt-4" role="alert">{transportError}</div>}

      {/* ITINERARY RESULT VIEW */}
      {activeTab === "itinerary" && itineraryResult && (
        <div className="itinerary-results" ref={resultsRef} aria-live="polite">
          {/* Engine & Source Badge */}
          <div className="engine-disclaimer-bar">
            <div className="engine-badge">
              <Sparkles size={14} />
              <span>{itineraryResult.generation_label}</span>
            </div>
            <p className="disclaimer-text">
              <Info size={14} /> {itineraryResult.pricing_disclaimer}
            </p>
          </div>

          {/* Hero Banner for Destination */}
          <div className="itinerary-hero-card">
            <div className="hero-img-wrap">
              <img
                src={itineraryResult.destination.image_url || "https://images.unsplash.com/photo-1512343879784-a960bf40e7f2?auto=format&fit=crop&w=1200&q=80"}
                alt={itineraryResult.destination.name}
                loading="lazy"
                onError={(e) => {
                  e.target.onerror = null;
                  e.target.src = "https://images.unsplash.com/photo-1512343879784-a960bf40e7f2?auto=format&fit=crop&w=1200&q=80";
                }}
              />
              <div className="hero-overlay" />
              <div className="hero-content">
                <div className="hero-tags">
                  <span className="hero-tag destination-tag">
                    <MapPin size={13} /> {itineraryResult.destination.name}, {itineraryResult.destination.state || itineraryResult.destination.region}
                  </span>
                  <span className={`hero-tag budget-tag ${itineraryResult.within_budget ? "within" : "over"}`}>
                    {itineraryResult.within_budget ? "✓ Within Budget" : "⚠ Over Budget"}
                  </span>
                </div>
                <h2>{itineraryResult.title}</h2>
                <p className="hero-desc">{itineraryResult.destination.description}</p>
                <div className="hero-meta">
                  <span><strong>Duration:</strong> {itineraryResult.days} Days / {itineraryResult.accommodation_details.nights} Nights</span>
                  <span><strong>Travelers:</strong> {itineraryResult.travelers} Persons</span>
                  <span><strong>Best Season:</strong> {itineraryResult.destination.best_time_to_visit || "October to March"}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Action Bar */}
          <div className="itinerary-action-bar">
            <div className="action-buttons-group">
              <button
                type="button"
                className="btn-action save-btn"
                onClick={saveCurrentItinerary}
                disabled={saving || savedSuccess}
              >
                <Bookmark size={15} />
                {saving ? "Saving…" : savedSuccess ? "✓ Itinerary Saved to My Trips" : "Save Itinerary"}
              </button>
              <button
                type="button"
                className="btn-action primary-btn book-stay-btn"
                style={{ background: "#0f766e", borderColor: "#0d5f58" }}
                onClick={() => {
                  if (onBookAccommodation && itineraryResult?.destination) {
                    onBookAccommodation({
                      destinationId: itineraryResult.destination.id,
                      destinationName: itineraryResult.destination.name,
                      travelers: itineraryResult.travelers,
                      rooms: Math.ceil(itineraryResult.travelers / 2),
                      nights: itineraryResult.days > 1 ? itineraryResult.days - 1 : 1,
                      days: itineraryResult.days,
                    });
                  }
                }}
              >
                <Building2 size={15} /> Find & Book Stays
              </button>
              <button
                type="button"
                className="btn-action secondary-btn"
                onClick={handleEditInputs}
              >
                <Edit3 size={15} /> Edit Inputs
              </button>
              <button
                type="button"
                className="btn-action secondary-btn"
                onClick={() => handleGenerateItinerary(null)}
                disabled={loading}
              >
                <RefreshCw size={15} className={loading ? "spin-icon" : ""} /> Regenerate Plan
              </button>
            </div>
            {savedSuccess && (
              <span className="save-badge-success">
                <CheckCircle2 size={15} /> Saved as #{savedItineraryId}! View it in <a href="#my-trips">My Trips</a> below.
              </span>
            )}
          </div>

          {/* Budget Breakdown & Cost Analysis */}
          <div className="budget-breakdown-card">
            <div className="breakdown-header">
              <div>
                <h3>Estimated Trip Expenses</h3>
                <p>Transparent projected cost breakdown covering all major travel components</p>
              </div>
              <div className="budget-status-pill">
                <strong>{itineraryResult.within_budget ? "Surplus:" : "Shortfall:"}</strong>{" "}
                <span className={itineraryResult.within_budget ? "surplus-val" : "deficit-val"}>
                  {money(Math.abs(itineraryResult.remaining_budget))}
                </span>
              </div>
            </div>

            {/* Visual Progress Bar */}
            <div className="budget-progress-track">
              <div
                className="budget-bar accom-bar"
                style={{ width: `${Math.min(100, (itineraryResult.estimated_accommodation / itineraryResult.total_estimated_cost) * 100)}%` }}
                title={`Lodging: ${money(itineraryResult.estimated_accommodation)}`}
              />
              <div
                className="budget-bar transport-bar"
                style={{ width: `${Math.min(100, (itineraryResult.estimated_transport / itineraryResult.total_estimated_cost) * 100)}%` }}
                title={`Transport: ${money(itineraryResult.estimated_transport)}`}
              />
              <div
                className="budget-bar food-bar"
                style={{ width: `${Math.min(100, (itineraryResult.estimated_food / itineraryResult.total_estimated_cost) * 100)}%` }}
                title={`Food: ${money(itineraryResult.estimated_food)}`}
              />
              <div
                className="budget-bar sight-bar"
                style={{ width: `${Math.min(100, (itineraryResult.estimated_sightseeing / itineraryResult.total_estimated_cost) * 100)}%` }}
                title={`Sightseeing: ${money(itineraryResult.estimated_sightseeing)}`}
              />
            </div>

            {/* 4-Part Expense Grid */}
            <div className="expense-grid">
              <div className="expense-card">
                <div className="expense-icon accom-icon"><Building2 size={18} /></div>
                <div className="expense-info">
                  <span className="expense-category">Accommodation</span>
                  <strong>{money(itineraryResult.estimated_accommodation)}</strong>
                  <span className="expense-sub">
                    {itineraryResult.accommodation_details.rooms} room(s) × {itineraryResult.accommodation_details.nights} night(s)
                  </span>
                </div>
              </div>

              <div className="expense-card">
                <div className="expense-icon transport-icon"><Bus size={18} /></div>
                <div className="expense-info">
                  <span className="expense-category">Transport & Travel</span>
                  <strong>{money(itineraryResult.estimated_transport)}</strong>
                  <span className="expense-sub">
                    {itineraryResult.origin ? `From ${itineraryResult.origin} · ` : ""}Transit & Mobility
                  </span>
                </div>
              </div>

              <div className="expense-card">
                <div className="expense-icon food-icon"><Utensils size={18} /></div>
                <div className="expense-info">
                  <span className="expense-category">Food & Dining</span>
                  <strong>{money(itineraryResult.estimated_food)}</strong>
                  <span className="expense-sub">
                    ~{money(itineraryResult.food_details.daily_per_person)}/day per traveler
                  </span>
                </div>
              </div>

              <div className="expense-card">
                <div className="expense-icon sight-icon"><Ticket size={18} /></div>
                <div className="expense-info">
                  <span className="expense-category">Sightseeing & Entry</span>
                  <strong>{money(itineraryResult.estimated_sightseeing)}</strong>
                  <span className="expense-sub">
                    Attraction entry fees ({itineraryResult.travelers} people)
                  </span>
                </div>
              </div>
            </div>

            {/* Summary Totals */}
            <div className="budget-summary-strip">
              <div className="summary-col">
                <span className="summary-label">Total Estimated Cost</span>
                <span className="summary-val">{money(itineraryResult.total_estimated_cost)}</span>
              </div>
              <div className="summary-col">
                <span className="summary-label">Estimated Cost / Person</span>
                <span className="summary-val highlight">{money(itineraryResult.cost_per_person)}</span>
              </div>
              <div className="summary-col">
                <span className="summary-label">Your Budget / Person</span>
                <span className="summary-val">{money(itineraryResult.budget_per_person)}</span>
              </div>
              <div className="summary-col">
                <span className="summary-label">Remaining Balance</span>
                <span className={`summary-val ${itineraryResult.within_budget ? "positive" : "negative"}`}>
                  {itineraryResult.within_budget ? `+${money(itineraryResult.remaining_budget)}` : `-${money(Math.abs(itineraryResult.remaining_budget))}`}
                </span>
              </div>
            </div>
          </div>

          {/* Insufficient Budget Alert & Smart Alternatives */}
          {!itineraryResult.within_budget && (
            <div className="budget-alert-card">
              <div className="alert-head">
                <AlertTriangle size={20} className="alert-icon" />
                <div>
                  <h4>Budget Shortfall Analysis</h4>
                  <p>{itineraryResult.budget_explanation}</p>
                </div>
              </div>

              {itineraryResult.alternatives && itineraryResult.alternatives.length > 0 && (
                <div className="alternatives-wrapper">
                  <h5>Recommended Cost-Saving Alternatives:</h5>
                  <div className="alternatives-grid">
                    {itineraryResult.alternatives.map((alt, idx) => (
                      <div className="alternative-box" key={idx}>
                        <div className="alt-title-row">
                          <strong>{alt.title}</strong>
                          {alt.savings_estimate > 0 && (
                            <span className="alt-saving-badge">Save ~{money(alt.savings_estimate)}</span>
                          )}
                        </div>
                        <p>{alt.description}</p>
                        {alt.destination_id && (
                          <button
                            type="button"
                            className="btn-switch-dest"
                            onClick={() => handleGenerateItinerary(null, alt.destination_id)}
                          >
                            Plan this destination instead <ArrowRight size={13} />
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Recommended Destinations Grid (If generated without destination or as alternatives) */}
          {itineraryResult.recommended_destinations && itineraryResult.recommended_destinations.length > 0 && (
            <div className="recommended-destinations-block">
              <div className="rec-head">
                <h3>Recommended Destinations For Your Budget</h3>
                <p>Click any destination to explore a full day-by-day itinerary tailored to it</p>
              </div>
              <div className="rec-destinations-grid">
                {itineraryResult.recommended_destinations.map(d => (
                  <div
                    key={d.destination_id}
                    className={`rec-dest-card ${d.destination_id === itineraryResult.destination.id ? "current-active" : ""}`}
                    onClick={() => handleGenerateItinerary(null, d.destination_id)}
                  >
                    <img
                      src={d.image_url}
                      alt={d.name}
                      loading="lazy"
                      onError={(e) => {
                        e.target.onerror = null;
                        e.target.src = "https://images.unsplash.com/photo-1488646953014-85cb44e25828?auto=format&fit=crop&w=800&q=80";
                      }}
                    />
                    <div className="rec-card-body">
                      <div className="rec-card-tags">
                        <span className="rec-state">{d.name}, {d.state}</span>
                        <span className={`rec-badge ${d.within_budget ? "within" : "over"}`}>
                          {d.within_budget ? "Within Budget" : "Over Budget"}
                        </span>
                      </div>
                      <div className="rec-cost-row">
                        <span>Est. Cost:</span>
                        <strong>{money(d.estimated_cost_per_person)} / person</strong>
                      </div>
                      <p className="rec-reason">{d.match_reason}</p>
                      <button type="button" className="rec-select-btn">
                        {d.destination_id === itineraryResult.destination.id ? "Currently Viewing" : "Generate Itinerary →"}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Travel & Transport Options Section */}
          <div className="travel-transport-section" style={{
            background: "#ffffff",
            border: "1px solid #dbe5de",
            borderRadius: "16px",
            padding: "1.75rem",
            margin: "2rem 0",
            boxShadow: "0 4px 16px rgba(0,0,0,0.03)"
          }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "1rem", marginBottom: "1.25rem" }}>
              <div>
                <span className="eyebrow" style={{ color: "#1b4d37", display: "inline-flex", alignItems: "center", gap: "0.35rem" }}>
                  <Compass size={14} /> TRAVEL & TRANSPORT OPTIONS
                </span>
                <h3 style={{ margin: "0.25rem 0 0.4rem", fontSize: "1.45rem", color: "#182c22" }}>
                  Travel & Transport Options to {itineraryResult.destination.name}
                </h3>
                <p style={{ margin: 0, fontSize: "0.92rem", color: "#546e61" }}>
                  {itineraryResult.origin ? (
                    <span>Direct and connecting demo schedules from <strong>{itineraryResult.origin}</strong></span>
                  ) : (
                    <span style={{ color: "#b45309" }}>Starting city not entered — enter your departure city below for transport options</span>
                  )}
                  {` · Group of ${itineraryResult.travelers} ${itineraryResult.travelers === 1 ? "traveller" : "travellers"} · Transit budget allocated: ${money(itineraryResult.estimated_transport)}`}
                </p>
              </div>

              {onSearchTransport && (
                <button
                  type="button"
                  className="button secondary"
                  style={{ fontSize: "0.85rem", padding: "0.45rem 0.95rem" }}
                  onClick={() => onSearchTransport({
                    origin: itineraryResult.origin || origin || "Hyderabad",
                    destination: itineraryResult.destination.name,
                  })}
                >
                  <Compass size={14} /> Compare All Routes on Search Page →
                </button>
              )}
            </div>

            {/* Prompt if Starting Location was not provided */}
            {!itineraryResult.origin && (
              <div style={{
                background: "#fefce8",
                border: "1px solid #fef08a",
                borderRadius: "12px",
                padding: "1.2rem",
                marginBottom: "1.5rem"
              }}>
                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", color: "#854d0e", fontWeight: 700, fontSize: "0.98rem" }}>
                  <AlertCircle size={18} /> Starting Location Required for Transport
                </div>
                <p style={{ margin: "0.4rem 0 0.85rem", color: "#713f12", fontSize: "0.9rem" }}>
                  Please enter your starting city to search the bus and train databases, compare journey durations and fares, and calculate transit expenses into your total trip budget.
                </p>
                <div style={{ display: "flex", gap: "0.6rem", flexWrap: "wrap", alignItems: "center" }}>
                  <input
                    type="text"
                    placeholder="Enter starting city (e.g. Hyderabad, Bengaluru, Delhi, Mumbai, Chennai)"
                    value={origin}
                    onChange={e => setOrigin(e.target.value)}
                    style={{
                      flex: 1, minWidth: "240px", padding: "0.55rem 0.85rem", borderRadius: "8px",
                      border: "1px solid #cbd5e1", fontSize: "0.9rem"
                    }}
                    list="itin-prompt-origins"
                  />
                  <datalist id="itin-prompt-origins">
                    <option value="Hyderabad" />
                    <option value="Bengaluru" />
                    <option value="Delhi" />
                    <option value="Mumbai" />
                    <option value="Chennai" />
                    <option value="Kochi" />
                    <option value="Varanasi" />
                  </datalist>
                  <button
                    type="button"
                    className="button primary"
                    style={{ padding: "0.55rem 1.1rem", fontSize: "0.9rem" }}
                    onClick={e => handleGenerateItinerary(e)}
                  >
                    Find Transport & Recalculate
                  </button>
                </div>
              </div>
            )}

            {/* Comparison Summary Banner */}
            {itineraryResult.recommended_transport?.comparison_summary && (
              <div style={{
                background: "#f0fdf4",
                border: "1px solid #bbf7d0",
                borderRadius: "12px",
                padding: "1rem 1.25rem",
                marginBottom: "1.5rem",
                fontSize: "0.92rem",
                color: "#166534",
                lineHeight: 1.55
              }}>
                <strong>💡 AI Transport Analysis & Recommendation:</strong>{" "}
                {itineraryResult.recommended_transport.comparison_summary}
              </div>
            )}

            {/* Top Recommended Bus & Train Showcase Cards */}
            {itineraryResult.recommended_transport && (itineraryResult.recommended_transport.recommended_bus || itineraryResult.recommended_transport.recommended_train) && (
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "1.25rem", marginBottom: "1.75rem" }}>
                {/* Recommended Bus Card */}
                {itineraryResult.recommended_transport.recommended_bus ? (
                  <div style={{
                    border: "1px solid #93c5fd",
                    borderRadius: "14px",
                    background: "#f8fafd",
                    padding: "1.3rem",
                    display: "flex",
                    flexDirection: "column",
                    justifyContent: "space-between",
                    gap: "0.85rem",
                    position: "relative"
                  }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <span style={{
                        display: "inline-flex", alignItems: "center", gap: "0.3rem",
                        background: "#1d4ed8", color: "#ffffff", padding: "3px 10px",
                        borderRadius: "20px", fontSize: "0.75rem", fontWeight: 700
                      }}>
                        <Bus size={13} /> RECOMMENDED BUS
                      </span>
                      <span style={{ fontSize: "0.74rem", color: "#2563eb", fontWeight: 600 }}>
                        Sample Demo Service
                      </span>
                    </div>

                    <div>
                      <h4 style={{ margin: "0.3rem 0 0.2rem", fontSize: "1.15rem", color: "#1e3a8a" }}>
                        {itineraryResult.recommended_transport.recommended_bus.operator}
                      </h4>
                      {itineraryResult.recommended_transport.recommended_bus.service_name && (
                        <div style={{ fontSize: "0.86rem", color: "#3b82f6", fontWeight: 600 }}>
                          {itineraryResult.recommended_transport.recommended_bus.service_name}
                        </div>
                      )}
                      <div style={{ fontSize: "0.82rem", color: "#475569", marginTop: "0.3rem" }}>
                        Bus Type: {itineraryResult.recommended_transport.recommended_bus.service_type || "AC Sleeper"}
                      </div>
                    </div>

                    <div style={{ background: "#ffffff", border: "1px solid #e2e8f0", borderRadius: "10px", padding: "0.75rem" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.88rem", fontWeight: 700, color: "#1e293b" }}>
                        <span>Departure: {itineraryResult.recommended_transport.recommended_bus.departure_time}</span>
                        <span>Arrival: {itineraryResult.recommended_transport.recommended_bus.arrival_time}</span>
                      </div>
                      <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.78rem", color: "#64748b", marginTop: "4px" }}>
                        <span>Boarding: {itineraryResult.recommended_transport.recommended_bus.boarding_point || itineraryResult.recommended_transport.recommended_bus.origin}</span>
                        <span>Dropping: {itineraryResult.recommended_transport.recommended_bus.dropping_point || itineraryResult.recommended_transport.recommended_bus.destination}</span>
                      </div>
                      <div style={{ fontSize: "0.8rem", color: "#0f766e", marginTop: "6px", fontWeight: 600 }}>
                        ⏱️ Journey Duration: {itineraryResult.recommended_transport.recommended_bus.duration || "Direct"} · 💺 {itineraryResult.recommended_transport.recommended_bus.booking_status}
                      </div>
                    </div>

                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderTop: "1px solid #e2e8f0", paddingTop: "0.75rem" }}>
                      <div>
                        <div style={{ fontSize: "1.25rem", fontWeight: 800, color: "#1e3a8a" }}>
                          {money(itineraryResult.recommended_transport.recommended_bus.ticket_price)} <span style={{ fontSize: "0.75rem", fontWeight: 500, color: "#64748b" }}>/ person</span>
                        </div>
                        <div style={{ fontSize: "0.78rem", color: "#2563eb", fontWeight: 600 }}>
                          Total: {money(itineraryResult.recommended_transport.recommended_bus.ticket_price * itineraryResult.travelers)} for {itineraryResult.travelers} travellers
                        </div>
                      </div>
                      <div style={{ display: "flex", gap: "0.4rem" }}>
                        <button
                          type="button"
                          className="button secondary"
                          style={{ padding: "0.4rem 0.75rem", fontSize: "0.8rem" }}
                          onClick={() => setSelectedTransportModal(itineraryResult.recommended_transport.recommended_bus)}
                        >
                          Details
                        </button>
                        {itineraryResult.recommended_transport.recommended_bus.booking_url && (
                          <a
                            href={itineraryResult.recommended_transport.recommended_bus.booking_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="button primary"
                            style={{ padding: "0.4rem 0.85rem", fontSize: "0.8rem" }}
                          >
                            Book Bus <ExternalLink size={12} />
                          </a>
                        )}
                      </div>
                    </div>
                  </div>
                ) : (
                  <div style={{ border: "1px dashed #cbd5e1", borderRadius: "14px", padding: "1.5rem", textAlign: "center", color: "#64748b" }}>
                    No matching demo bus option available for this corridor.
                  </div>
                )}

                {/* Recommended Train Card */}
                {itineraryResult.recommended_transport.recommended_train ? (
                  <div style={{
                    border: "1px solid #f472b6",
                    borderRadius: "14px",
                    background: "#fdf8fb",
                    padding: "1.3rem",
                    display: "flex",
                    flexDirection: "column",
                    justifyContent: "space-between",
                    gap: "0.85rem",
                    position: "relative"
                  }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <span style={{
                        display: "inline-flex", alignItems: "center", gap: "0.3rem",
                        background: "#be185d", color: "#ffffff", padding: "3px 10px",
                        borderRadius: "20px", fontSize: "0.75rem", fontWeight: 700
                      }}>
                        <Train size={13} /> RECOMMENDED TRAIN
                      </span>
                      <span style={{ fontSize: "0.74rem", color: "#db2777", fontWeight: 600 }}>
                        Sample Demo Service
                      </span>
                    </div>

                    <div>
                      <h4 style={{ margin: "0.3rem 0 0.2rem", fontSize: "1.15rem", color: "#831843" }}>
                        {itineraryResult.recommended_transport.recommended_train.service_name || itineraryResult.recommended_transport.recommended_train.operator}
                      </h4>
                      <div style={{ fontSize: "0.86rem", color: "#9d174d", fontWeight: 600 }}>
                        {itineraryResult.recommended_transport.recommended_train.operator} · {itineraryResult.recommended_transport.recommended_train.service_type || "Express"}
                      </div>
                      {itineraryResult.recommended_transport.recommended_train.available_classes && (
                        <div style={{ fontSize: "0.82rem", color: "#475569", marginTop: "0.3rem" }}>
                          Classes Available: <strong>{itineraryResult.recommended_transport.recommended_train.available_classes}</strong>
                        </div>
                      )}
                    </div>

                    <div style={{ background: "#ffffff", border: "1px solid #fce7f3", borderRadius: "10px", padding: "0.75rem" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.88rem", fontWeight: 700, color: "#1e293b" }}>
                        <span>Departure: {itineraryResult.recommended_transport.recommended_train.departure_time}</span>
                        <span>Arrival: {itineraryResult.recommended_transport.recommended_train.arrival_time}</span>
                      </div>
                      <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.78rem", color: "#64748b", marginTop: "4px" }}>
                        <span>Station: {itineraryResult.recommended_transport.recommended_train.origin_station || itineraryResult.recommended_transport.recommended_train.origin}</span>
                        <span>Destination: {itineraryResult.recommended_transport.recommended_train.destination_station || itineraryResult.recommended_transport.recommended_train.destination}</span>
                      </div>
                      <div style={{ fontSize: "0.8rem", color: "#9d174d", marginTop: "6px", fontWeight: 600 }}>
                        ⏱️ Journey Duration: {itineraryResult.recommended_transport.recommended_train.duration || "Direct"} · 💺 {itineraryResult.recommended_transport.recommended_train.booking_status}
                      </div>
                    </div>

                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderTop: "1px solid #fce7f3", paddingTop: "0.75rem" }}>
                      <div>
                        <div style={{ fontSize: "1.25rem", fontWeight: 800, color: "#831843" }}>
                          {money(itineraryResult.recommended_transport.recommended_train.ticket_price)} <span style={{ fontSize: "0.75rem", fontWeight: 500, color: "#64748b" }}>/ person</span>
                        </div>
                        <div style={{ fontSize: "0.78rem", color: "#be185d", fontWeight: 600 }}>
                          Total: {money(itineraryResult.recommended_transport.recommended_train.ticket_price * itineraryResult.travelers)} for {itineraryResult.travelers} travellers
                        </div>
                      </div>
                      <div style={{ display: "flex", gap: "0.4rem" }}>
                        <button
                          type="button"
                          className="button secondary"
                          style={{ padding: "0.4rem 0.75rem", fontSize: "0.8rem" }}
                          onClick={() => setSelectedTransportModal(itineraryResult.recommended_transport.recommended_train)}
                        >
                          Details
                        </button>
                        {itineraryResult.recommended_transport.recommended_train.booking_url && (
                          <a
                            href={itineraryResult.recommended_transport.recommended_train.booking_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="button primary"
                            style={{ padding: "0.4rem 0.85rem", fontSize: "0.8rem", background: "#be185d", borderColor: "#be185d" }}
                          >
                            Book IRCTC <ExternalLink size={12} />
                          </a>
                        )}
                      </div>
                    </div>
                  </div>
                ) : (
                  <div style={{ border: "1px dashed #cbd5e1", borderRadius: "14px", padding: "1.5rem", textAlign: "center", color: "#64748b" }}>
                    No matching demo train option available for this corridor.
                  </div>
                )}
              </div>
            )}

            {/* Sub-Tabs: Explore All Buses & Trains */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "0.5rem", marginBottom: "1rem" }}>
              <div style={{ display: "flex", gap: "0.5rem" }}>
                <button
                  type="button"
                  className={`cat-pill ${activeItinTransportCategory === "all" ? "active" : ""}`}
                  style={{ padding: "0.35rem 0.85rem", fontSize: "0.82rem" }}
                  onClick={() => setActiveItinTransportCategory("all")}
                >
                  All 10 Options ({itineraryResult.recommended_transport?.all_options?.length || 0})
                </button>
                <button
                  type="button"
                  className={`cat-pill ${activeItinTransportCategory === "bus" ? "active" : ""}`}
                  style={{ padding: "0.35rem 0.85rem", fontSize: "0.82rem" }}
                  onClick={() => setActiveItinTransportCategory("bus")}
                >
                  <Bus size={13} /> Recommended Buses ({itineraryResult.recommended_transport?.buses?.length || 0})
                </button>
                <button
                  type="button"
                  className={`cat-pill ${activeItinTransportCategory === "train" ? "active" : ""}`}
                  style={{ padding: "0.35rem 0.85rem", fontSize: "0.82rem" }}
                  onClick={() => setActiveItinTransportCategory("train")}
                >
                  <Train size={13} /> Recommended Trains ({itineraryResult.recommended_transport?.trains?.length || 0})
                </button>
              </div>

              <span style={{ fontSize: "0.78rem", color: "#64748b" }}>
                * Fictional demo schedules & estimated fares for planning
              </span>
            </div>

            {/* List of Recommended Buses and Trains */}
            {(() => {
              const buses = itineraryResult.recommended_transport?.buses || [];
              const trains = itineraryResult.recommended_transport?.trains || [];

              if (buses.length === 0 && trains.length === 0) {
                return (
                  <div style={{ padding: "1.5rem", background: "#f8faf9", borderRadius: "10px", textAlign: "center", color: "#617c6e" }}>
                    {itineraryResult.origin
                      ? `No matching demo transport routes cataloged between ${itineraryResult.origin} and ${itineraryResult.destination.name}.`
                      : "Please enter your starting location above to view all matching buses and trains."}
                  </div>
                );
              }

              const renderTransportCard = (t) => (
                <div key={t.id} style={{
                  background: "#ffffff",
                  border: t.mode === "bus" ? "1px solid #bfdbfe" : "1px solid #fbcfe8",
                  borderRadius: "12px",
                  padding: "1.1rem",
                  display: "flex",
                  flexDirection: "column",
                  justifyContent: "space-between",
                  gap: "0.65rem",
                  boxShadow: "0 2px 6px rgba(0,0,0,0.02)"
                }}>
                  <div>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.35rem" }}>
                      <span style={{
                        padding: "2px 7px", borderRadius: "4px", fontSize: "10px", fontWeight: 700, textTransform: "uppercase",
                        background: t.mode === "bus" ? "#eef6ff" : "#fdf2f8",
                        color: t.mode === "bus" ? "#1d4ed8" : "#be185d"
                      }}>
                        {t.mode === "bus" ? "🚌 Demo Bus" : "🚆 Demo Train"}
                      </span>
                      <span style={{ fontSize: "11px", color: "#059669", fontWeight: 600 }}>
                        {t.booking_status || "Available"}
                      </span>
                    </div>
                    <h4 style={{ margin: "0.2rem 0", fontSize: "0.98rem", color: "#182c21" }}>
                      {t.mode === "train" ? (t.service_name || t.operator) : t.operator}
                    </h4>
                    {t.mode === "bus" && t.service_name && <div style={{ fontSize: "0.8rem", color: "#526d5f", fontWeight: 500 }}>{t.service_name}</div>}
                    <div style={{ fontSize: "0.78rem", color: "#456153", marginTop: "0.4rem" }}>
                      <strong>{t.departure_time}</strong> ({t.origin_station || t.origin}) ➔ <strong>{t.arrival_time}</strong> ({t.destination_station || t.destination})
                    </div>
                    <div style={{ fontSize: "0.75rem", color: "#6b8275", marginTop: "0.2rem" }}>
                      ⏱️ Duration: {t.duration || "Direct"} · 💺 {t.available_seats || 30} demo seats
                    </div>

                    {/* Connecting Railhead Notice for Hill Stations */}
                    {t.mode === "train" && (t.destination === "Ooty" || t.destination === "Manali" || t.destination_station?.includes("MTP") || t.destination_station?.includes("Chandigarh") || t.destination_station?.includes("Kalka")) && (
                      <div style={{
                        fontSize: "0.74rem",
                        color: "#92400e",
                        background: "#fef3c7",
                        padding: "3px 6px",
                        borderRadius: "5px",
                        marginTop: "4px",
                        border: "1px solid #fde68a"
                      }}>
                        ⚠️ Connecting station: Rail terminates at nearby railhead with road / toy-train transfer to {t.destination}.
                      </div>
                    )}
                  </div>

                  <div style={{ borderTop: "1px dashed #e1e9e3", paddingTop: "0.65rem", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <div>
                      <div style={{ fontSize: "1.15rem", fontWeight: 800, color: t.mode === "bus" ? "#1e40af" : "#9d174d" }}>
                        {money(t.ticket_price)}
                      </div>
                      <span style={{ fontSize: "0.72rem", color: "#617c6e" }}>
                        Total {money(t.ticket_price * itineraryResult.travelers)} ({itineraryResult.travelers} {itineraryResult.travelers === 1 ? "traveller" : "travellers"})
                      </span>
                    </div>
                    <div style={{ display: "flex", gap: "0.35rem" }}>
                      <button
                        type="button"
                        className="button secondary"
                        style={{ padding: "0.3rem 0.6rem", fontSize: "0.76rem" }}
                        onClick={() => setSelectedTransportModal(t)}
                      >
                        Details
                      </button>
                      {t.booking_url && (
                        <a
                          href={t.booking_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="button primary"
                          style={{
                            padding: "0.3rem 0.7rem",
                            fontSize: "0.76rem",
                            background: t.mode === "train" ? "#be185d" : undefined,
                            borderColor: t.mode === "train" ? "#be185d" : undefined
                          }}
                        >
                          Book <ExternalLink size={10} />
                        </a>
                      )}
                    </div>
                  </div>
                </div>
              );

              return (
                <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
                  {/* Buses Section */}
                  {(activeItinTransportCategory === "all" || activeItinTransportCategory === "bus") && buses.length > 0 && (
                    <div>
                      <div style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "0.5rem",
                        marginBottom: "0.85rem",
                        paddingBottom: "0.35rem",
                        borderBottom: "2px solid #bfdbfe"
                      }}>
                        <Bus size={18} color="#1d4ed8" />
                        <h4 style={{ margin: 0, fontSize: "1.05rem", color: "#1e3a8a", fontWeight: 700 }}>
                          Recommended Buses – {buses.length} Options
                        </h4>
                        <span style={{ fontSize: "0.75rem", color: "#2563eb", background: "#eff6ff", padding: "2px 8px", borderRadius: "12px", fontWeight: 600 }}>
                          Morning to Night schedules
                        </span>
                      </div>
                      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "1rem" }}>
                        {buses.map(renderTransportCard)}
                      </div>
                    </div>
                  )}

                  {/* Trains Section */}
                  {(activeItinTransportCategory === "all" || activeItinTransportCategory === "train") && trains.length > 0 && (
                    <div>
                      <div style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "0.5rem",
                        marginBottom: "0.85rem",
                        paddingBottom: "0.35rem",
                        borderBottom: "2px solid #fbcfe8"
                      }}>
                        <Train size={18} color="#be185d" />
                        <h4 style={{ margin: 0, fontSize: "1.05rem", color: "#831843", fontWeight: 700 }}>
                          Recommended Trains – {trains.length} Options
                        </h4>
                        <span style={{ fontSize: "0.75rem", color: "#db2777", background: "#fdf2f8", padding: "2px 8px", borderRadius: "12px", fontWeight: 600 }}>
                          Vande Bharat, Superfast, Jan Shatabdi & Overnight
                        </span>
                      </div>
                      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "1rem" }}>
                        {trains.map(renderTransportCard)}
                      </div>
                    </div>
                  )}
                </div>
              );
            })()}
          </div>

          {/* Day-by-Day Schedule Timeline */}
          <div className="daily-schedule-section">
            <div className="schedule-header">
              <div>
                <h3>Day-by-Day Itinerary Schedule</h3>
                <p>Carefully distributed attractions, activities, and timings across your {itineraryResult.days}-day stay</p>
              </div>
            </div>

            <div className="days-container">
              {itineraryResult.daily_schedule.map(dayPlan => (
                <div className="day-card" key={dayPlan.day}>
                  <div className="day-card-header">
                    <div className="day-number-badge">Day {dayPlan.day}</div>
                    <h4>{dayPlan.title}</h4>
                    <span className="day-entry-sum">
                      Sightseeing: {dayPlan.day_sightseeing_cost_per_person > 0 ? `${money(dayPlan.day_sightseeing_cost_per_person)} / person` : "Free Entry"}
                    </span>
                  </div>

                  <div className="slots-grid">
                    {dayPlan.schedule.map((item, itemIdx) => (
                      <div className="slot-item" key={itemIdx}>
                        <div className="slot-img-wrap">
                          <img
                            src={item.image_url}
                            alt={item.name}
                            loading="lazy"
                            onError={(e) => {
                              e.target.onerror = null;
                              e.target.src = "https://images.unsplash.com/photo-1488646953014-85cb44e25828?auto=format&fit=crop&w=800&q=80";
                            }}
                          />
                          <span className="slot-time-badge"><Clock size={12} /> {item.time_slot}</span>
                        </div>
                        <div className="slot-content">
                          <div className="slot-top-row">
                            <span className="slot-category">{item.category}</span>
                            <span className="slot-duration"><Clock size={11} /> {item.duration_text}</span>
                          </div>
                          <h5>{item.name}</h5>
                          <p className="slot-desc">{item.description}</p>
                          <div className="slot-meta-row">
                            <span className="slot-fee">
                              <Ticket size={12} /> {item.entry_fee > 0 ? `${money(item.entry_fee)} entry` : "Free admission"}
                            </span>
                            <span className="slot-hours">
                              <Calendar size={12} /> {item.opening_hours}
                            </span>
                          </div>
                          {item.suggested_activity && (
                            <div className="slot-tip-box">
                              <strong>Activity & Tip:</strong> {item.suggested_activity}
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* HOTEL RECOMMENDATIONS VIEW (PRESERVED) */}
      {activeTab === "hotels" && hotelResult && (
        <div className="recommendation-results" ref={resultsRef} aria-live="polite">
          <div className="recommendation-result-heading">
            <div>
              <h3>
                {hotelResult.matches.length
                  ? "Recommended stays"
                  : hotelResult.alternatives.length
                  ? "Closest available stays"
                  : "No stays to show"}
              </h3>
              <p>{hotelResult.message} Estimates cover lodging only; confirm rates and availability with the property.</p>
            </div>
            {hotelResult.matches.length > 0 && (
              <span className="recommendation-count">{hotelResult.matches.length} matches</span>
            )}
          </div>
          {hotelOptions.length > 0 && (
            <div className="recommendation-grid">
              {hotelOptions.map((option, index) => (
                <article className="recommendation-card" key={`${option.hotel_id}-${option.room_type_id ?? "hotel"}-${index}`}>
                  <span className={`recommendation-badge ${option.within_budget ? "" : "over-budget"}`}>
                    {option.is_demo ? "Sample demo price · not live" : option.within_budget ? "Within budget" : `${money(option.over_budget_per_person)} over budget / person`}
                  </span>
                  <h4>{option.hotel}</h4>
                  <p className="recommendation-place">{option.destination}{option.region ? ` · ${option.region}` : ""}</p>
                  <p className="recommendation-room">{option.room_type} · {option.travelers} people · {option.nights} night(s)</p>
                  <div className="recommendation-price">
                    <strong>{money(option.estimated_per_person)}<small> / person</small></strong>
                    <span>{money(option.estimated_total)} lodging total</span>
                  </div>
                  <a className="recommendation-link" href={`#destination-${option.destination_id}`}>
                    Explore {option.destination} stays <ArrowRight size={14} />
                  </a>
                </article>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TRANSPORT ONLY RESULT VIEW */}
      {activeTab === "transport" && transportResult && (
        <div className="transport-results-container" ref={resultsRef} aria-live="polite">
          {/* Route Hero Banner */}
          <div className="transport-route-banner">
            <div className="t-banner-top">
              <div className="t-corridor-title">
                <Compass size={24} />
                <span>{transportResult.origin} ➔ {transportResult.destination}</span>
              </div>
              <div className="t-daily-guarantee-badge">
                <ShieldCheck size={14} /> Daily Guaranteed Service · 365 Days a Year
              </div>
            </div>

            <div className="t-banner-meta-row">
              <div className="t-banner-meta-item">
                <Calendar size={15} />
                <strong>Travel Date:</strong>
                <span>{formatJourneyDateTime(transportResult.date, "00:00", "00:00").depDateText}</span>
              </div>
              <div className="t-banner-meta-item">
                <Users size={15} />
                <strong>Passengers:</strong>
                <span>{transportResult.travelers} {transportResult.travelers === 1 ? "Traveller" : "Travellers"}</span>
              </div>
              <div className="t-banner-meta-item">
                <Ticket size={15} />
                <strong>Total Options:</strong>
                <span>{sortedServices.length} Daily Connections (5 Buses + 5 Trains)</span>
              </div>
            </div>

            <p className="t-daily-notice-text">
              ✨ <strong>Daily Availability:</strong> All 5 demo buses and 5 demo trains operate every single day. Timings, fares, and service names are identical on any date you choose.
            </p>
          </div>

          {/* Filter & Sort Controls Toolbar */}
          <div className="transport-toolbar">
            <div className="t-filter-pills">
              <button
                type="button"
                className={`t-pill-btn ${transportCategory === "all" ? "active" : ""}`}
                onClick={() => setTransportCategory("all")}
              >
                All Transport <span className="t-pill-count">{sortedServices.length}</span>
              </button>
              <button
                type="button"
                className={`t-pill-btn ${transportCategory === "bus" ? "active" : ""}`}
                onClick={() => setTransportCategory("bus")}
              >
                <Bus size={14} /> Buses <span className="t-pill-count">{transportBuses.length}</span>
              </button>
              <button
                type="button"
                className={`t-pill-btn ${transportCategory === "train" ? "active" : ""}`}
                onClick={() => setTransportCategory("train")}
              >
                <Train size={14} /> Trains <span className="t-pill-count">{transportTrains.length}</span>
              </button>
            </div>

            <div className="t-sort-group">
              <span className="t-sort-label">Sort by:</span>
              <select
                className="t-sort-select"
                value={transportSortBy}
                onChange={e => setTransportSortBy(e.target.value)}
              >
                <option value="cheapest">Lowest Fare First</option>
                <option value="expensive">Highest Fare First</option>
                <option value="departure_asc">Earliest Departure</option>
                <option value="duration_asc">Shortest Journey Duration</option>
              </select>
            </div>
          </div>

          {/* Empty State */}
          {sortedServices.length === 0 && (
            <div className="transport-empty-state">
              <Bus size={42} />
              <h4>No demo services found for this corridor</h4>
              <p>Please select another pair of starting city and destination to explore available buses and trains.</p>
            </div>
          )}

          {/* SECTION 1: AVAILABLE DEMO BUSES */}
          {(transportCategory === "all" || transportCategory === "bus") && transportBuses.length > 0 && (
            <div className="transport-section-block">
              <div className="t-section-header">
                <div>
                  <h3><Bus size={20} color="#047857" /> Available Demo Buses – {transportBuses.length} Options</h3>
                  <p>Daily departure slots: early morning, late morning, afternoon, evening, and overnight sleeper coaches.</p>
                </div>
                <span style={{ fontSize: "0.8rem", color: "#047857", fontWeight: 700 }}>
                  Showing {transportBuses.length} daily bus services
                </span>
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: "0.85rem" }}>
                {transportBuses.map((bus, idx) => {
                  const { depDateText, arrDateText, isNextDay, cleanArrTime } = formatJourneyDateTime(
                    transportResult.date,
                    bus.departure_time,
                    bus.arrival_time
                  );
                  return (
                    <div className="t-card-item" key={bus.id || bus.service_id || idx}>
                      <div className="t-card-col-info">
                        <div className="t-card-topline">
                          <span className="t-mode-tag bus">BUS</span>
                          <span className="t-id-tag">{bus.service_id || `BUS-${bus.id}`}</span>
                          <span className="t-daily-tag">🟢 Daily</span>
                        </div>
                        <h4 className="t-card-operator">{bus.operator}</h4>
                        <p className="t-card-service-name">{bus.service_name}</p>
                        <span style={{ fontSize: "0.78rem", color: "#475569", fontWeight: 600 }}>
                          {bus.service_type || "AC Sleeper (2+1)"}
                        </span>
                        <span className="t-card-seats-info">
                          💺 {bus.available_seats || 32} seats available · {bus.booking_status || "Available"}
                        </span>
                      </div>

                      <div className="t-card-col-timing">
                        <div className="t-timing-row">
                          <div className="t-time-point">
                            <span className="t-time-val">{bus.departure_time}</span>
                            <span className="t-time-date">{depDateText}</span>
                            <span className="t-station-name" title={bus.origin_station || bus.origin}>
                              {bus.origin_station || bus.origin}
                            </span>
                          </div>

                          <div className="t-timing-path">
                            <span className="t-duration-txt">{bus.duration || "Direct"}</span>
                            <div className="t-path-line" />
                            <span className="t-distance-txt">{bus.distance_km || "Direct Highway"}</span>
                          </div>

                          <div className="t-time-point" style={{ alignItems: "flex-end", textAlign: "right" }}>
                            <span className="t-time-val">
                              {cleanArrTime}
                              {isNextDay && <span className="t-next-day-pill">+1 Next Day</span>}
                            </span>
                            <span className="t-time-date">{arrDateText}</span>
                            <span className="t-station-name" title={bus.destination_station || bus.destination}>
                              {bus.destination_station || bus.destination}
                            </span>
                          </div>
                        </div>
                      </div>

                      <div className="t-card-col-fare">
                        <div className="t-price-headline">
                          <span className="t-fare-per-person">
                            {money(bus.ticket_price)} <span className="t-per-person-unit">/ person</span>
                          </span>
                          <span className="t-total-fare-calc">
                            Total: {money(bus.ticket_price * transportResult.travelers)} for {transportResult.travelers} {transportResult.travelers === 1 ? "traveller" : "travellers"}
                          </span>
                          <span className="t-date-reminder">
                            Travel Date: {depDateText}
                          </span>
                        </div>

                        <div className="t-card-buttons">
                          <button
                            type="button"
                            className="btn-t-details"
                            onClick={() => setSelectedTransportModal(bus)}
                          >
                            Details
                          </button>
                          {bus.booking_url && (
                            <a
                              href={bus.booking_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="btn-t-book"
                            >
                              Official Website <ExternalLink size={13} />
                            </a>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* SECTION 2: AVAILABLE DEMO TRAINS */}
          {(transportCategory === "all" || transportCategory === "train") && transportTrains.length > 0 && (
            <div className="transport-section-block">
              <div className="t-section-header">
                <div>
                  <h3><Train size={20} color="#be185d" /> Available Demo Trains – {transportTrains.length} Options</h3>
                  <p>Daily railway departures: morning superfast, midday intercity, afternoon jan shatabdi, evening vande bharat, and overnight express.</p>
                </div>
                <span style={{ fontSize: "0.8rem", color: "#be185d", fontWeight: 700 }}>
                  Showing {transportTrains.length} daily train services
                </span>
              </div>

              {/* Connecting railhead advisory for hill stations Ooty & Manali */}
              {transportResult.destination.toLowerCase().includes("ooty") && (
                <div className="railhead-alert-box">
                  <Info size={18} />
                  <div>
                    <strong>Connecting Railhead Advisory for Ooty:</strong> Ooty is a high-altitude Nilgiri hill station. Trains operate to connecting gateway stations Mettupalayam (MTP) / Coimbatore Junction (CBE) with connecting mountain toy train or Ghat road transfers (demo schedules).
                  </div>
                </div>
              )}

              {transportResult.destination.toLowerCase().includes("manali") && (
                <div className="railhead-alert-box">
                  <Info size={18} />
                  <div>
                    <strong>Connecting Railhead Advisory for Manali:</strong> Manali is a Himalayan hill station. Trains operate to connecting gateway stations Chandigarh Junction (CDG) / Kalka (KLK) with connecting luxury highway transfers (demo schedules).
                  </div>
                </div>
              )}

              <div style={{ display: "flex", flexDirection: "column", gap: "0.85rem" }}>
                {transportTrains.map((train, idx) => {
                  const { depDateText, arrDateText, isNextDay, cleanArrTime } = formatJourneyDateTime(
                    transportResult.date,
                    train.departure_time,
                    train.arrival_time
                  );
                  return (
                    <div className="t-card-item" key={train.id || train.service_id || idx}>
                      <div className="t-card-col-info">
                        <div className="t-card-topline">
                          <span className="t-mode-tag train">TRAIN</span>
                          <span className="t-id-tag">{train.service_id || `TRN-${train.id}`}</span>
                          <span className="t-daily-tag" style={{ color: "#be185d" }}>🟢 Daily</span>
                        </div>
                        <h4 className="t-card-operator">{train.operator}</h4>
                        <p className="t-card-service-name">{train.service_name}</p>
                        <div className="t-classes-badges">
                          <span>Classes: <strong>{train.available_classes || "3AC / 2AC / SL"}</strong></span>
                        </div>
                        <span className="t-card-seats-info" style={{ color: "#be185d" }}>
                          💺 {train.available_seats || 48} seats available · {train.booking_status || "Available"}
                        </span>
                      </div>

                      <div className="t-card-col-timing">
                        <div className="t-timing-row">
                          <div className="t-time-point">
                            <span className="t-time-val">{train.departure_time}</span>
                            <span className="t-time-date">{depDateText}</span>
                            <span className="t-station-name" title={train.origin_station || train.origin}>
                              {train.origin_station || train.origin}
                            </span>
                          </div>

                          <div className="t-timing-path">
                            <span className="t-duration-txt">{train.duration || "Direct"}</span>
                            <div className="t-path-line" />
                            <span className="t-distance-txt">{train.distance_km || "Direct Rail"}</span>
                          </div>

                          <div className="t-time-point" style={{ alignItems: "flex-end", textAlign: "right" }}>
                            <span className="t-time-val">
                              {cleanArrTime}
                              {isNextDay && <span className="t-next-day-pill">+1 Next Day</span>}
                            </span>
                            <span className="t-time-date">{arrDateText}</span>
                            <span className="t-station-name" title={train.destination_station || train.destination}>
                              {train.destination_station || train.destination}
                            </span>
                          </div>
                        </div>
                      </div>

                      <div className="t-card-col-fare">
                        <div className="t-price-headline">
                          <span className="t-fare-per-person">
                            {money(train.ticket_price)} <span className="t-per-person-unit">/ person</span>
                          </span>
                          <span className="t-total-fare-calc" style={{ color: "#be185d" }}>
                            Total: {money(train.ticket_price * transportResult.travelers)} for {transportResult.travelers} {transportResult.travelers === 1 ? "traveller" : "travellers"}
                          </span>
                          <span className="t-date-reminder">
                            Travel Date: {depDateText}
                          </span>
                        </div>

                        <div className="t-card-buttons">
                          <button
                            type="button"
                            className="btn-t-details"
                            onClick={() => setSelectedTransportModal(train)}
                          >
                            Details
                          </button>
                          {train.booking_url && (
                            <a
                              href={train.booking_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="btn-t-book"
                              style={{ background: "#be185d" }}
                            >
                              Official Website <ExternalLink size={13} />
                            </a>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* SECTION 3: ROAMLY AI RECOMMENDATIONS & ANALYSIS */}
          {aiRecommendations && (
            <div className="ai-transport-recs-container">
              <div className="ai-recs-header">
                <div className="ai-recs-badge">
                  <Sparkles size={14} /> ROAMLY AI INTELLIGENCE
                </div>
                <h3>Roamly AI Transport Recommendations &amp; Analysis</h3>
                <p>
                  Algorithmic comparison and best-value picks for your group of {transportResult.travelers} {transportResult.travelers === 1 ? "traveller" : "travellers"} traveling from {transportResult.origin} to {transportResult.destination} on {formatJourneyDateTime(transportResult.date, "00:00", "00:00").depDateText}.
                </p>
              </div>

              <div className="ai-recs-grid">
                {/* 1. Cheapest Bus */}
                {aiRecommendations.cheapestBus && (
                  <div className="ai-rec-card cheapest-bus">
                    <div>
                      <span className="ai-rec-badge-tag"><Bus size={12} /> Cheapest Bus</span>
                      <h4 className="ai-rec-title">{aiRecommendations.cheapestBus.operator}</h4>
                      <p className="ai-rec-sub">{aiRecommendations.cheapestBus.service_name}</p>
                      <div className="ai-rec-timing">
                        ⏱️ {aiRecommendations.cheapestBus.departure_time} ➔ {aiRecommendations.cheapestBus.arrival_time} ({aiRecommendations.cheapestBus.duration})
                      </div>
                      <div className="ai-rec-pricing">
                        <div className="ai-rec-price-val">{money(aiRecommendations.cheapestBus.ticket_price)} <small style={{ fontSize: "0.74rem", color: "#64748b" }}>/ person</small></div>
                        <div className="ai-rec-group-total">Total: {money(aiRecommendations.cheapestBus.ticket_price * transportResult.travelers)} for {transportResult.travelers} pax</div>
                      </div>
                    </div>
                    <div className="ai-rec-explanation">
                      💡 <strong>Why AI Recommends:</strong> Lowest bus fare on this corridor, offering guaranteed daily departures with comfortable sleeper seating.
                    </div>
                    <div className="ai-rec-actions">
                      <button type="button" className="btn-t-details" style={{ flex: 1, padding: "0.35rem 0.6rem", fontSize: "0.78rem" }} onClick={() => setSelectedTransportModal(aiRecommendations.cheapestBus)}>Details</button>
                      {aiRecommendations.cheapestBus.booking_url && (
                        <a href={aiRecommendations.cheapestBus.booking_url} target="_blank" rel="noopener noreferrer" className="btn-t-book" style={{ flex: 1, padding: "0.35rem 0.6rem", fontSize: "0.78rem", justifyContent: "center" }}>Book <ExternalLink size={11} /></a>
                      )}
                    </div>
                  </div>
                )}

                {/* 2. Cheapest Train */}
                {aiRecommendations.cheapestTrain && (
                  <div className="ai-rec-card cheapest-train">
                    <div>
                      <span className="ai-rec-badge-tag"><Train size={12} /> Cheapest Train</span>
                      <h4 className="ai-rec-title">{aiRecommendations.cheapestTrain.operator}</h4>
                      <p className="ai-rec-sub">{aiRecommendations.cheapestTrain.service_name}</p>
                      <div className="ai-rec-timing">
                        ⏱️ {aiRecommendations.cheapestTrain.departure_time} ➔ {aiRecommendations.cheapestTrain.arrival_time} ({aiRecommendations.cheapestTrain.duration})
                      </div>
                      <div className="ai-rec-pricing">
                        <div className="ai-rec-price-val">{money(aiRecommendations.cheapestTrain.ticket_price)} <small style={{ fontSize: "0.74rem", color: "#64748b" }}>/ person</small></div>
                        <div className="ai-rec-group-total">Total: {money(aiRecommendations.cheapestTrain.ticket_price * transportResult.travelers)} for {transportResult.travelers} pax</div>
                      </div>
                    </div>
                    <div className="ai-rec-explanation">
                      💡 <strong>Why AI Recommends:</strong> Most economical railway service with verified Sleeper/AC berth options and scenic rail journey.
                    </div>
                    <div className="ai-rec-actions">
                      <button type="button" className="btn-t-details" style={{ flex: 1, padding: "0.35rem 0.6rem", fontSize: "0.78rem" }} onClick={() => setSelectedTransportModal(aiRecommendations.cheapestTrain)}>Details</button>
                      {aiRecommendations.cheapestTrain.booking_url && (
                        <a href={aiRecommendations.cheapestTrain.booking_url} target="_blank" rel="noopener noreferrer" className="btn-t-book" style={{ flex: 1, padding: "0.35rem 0.6rem", fontSize: "0.78rem", justifyContent: "center", background: "#be185d" }}>Book IRCTC <ExternalLink size={11} /></a>
                      )}
                    </div>
                  </div>
                )}

                {/* 3. Fastest Available Option */}
                {aiRecommendations.fastest && (
                  <div className="ai-rec-card fastest">
                    <div>
                      <span className="ai-rec-badge-tag"><Zap size={12} /> Fastest Option</span>
                      <h4 className="ai-rec-title">{aiRecommendations.fastest.operator}</h4>
                      <p className="ai-rec-sub">{aiRecommendations.fastest.service_name}</p>
                      <div className="ai-rec-timing">
                        ⚡ Duration: <strong>{aiRecommendations.fastest.duration}</strong> ({aiRecommendations.fastest.departure_time} dep)
                      </div>
                      <div className="ai-rec-pricing">
                        <div className="ai-rec-price-val">{money(aiRecommendations.fastest.ticket_price)} <small style={{ fontSize: "0.74rem", color: "#64748b" }}>/ person</small></div>
                        <div className="ai-rec-group-total">Total: {money(aiRecommendations.fastest.ticket_price * transportResult.travelers)} for {transportResult.travelers} pax</div>
                      </div>
                    </div>
                    <div className="ai-rec-explanation">
                      💡 <strong>Why AI Recommends:</strong> Shortest travel time on this route ({aiRecommendations.fastest.duration}), minimizing travel fatigue for your journey.
                    </div>
                    <div className="ai-rec-actions">
                      <button type="button" className="btn-t-details" style={{ flex: 1, padding: "0.35rem 0.6rem", fontSize: "0.78rem" }} onClick={() => setSelectedTransportModal(aiRecommendations.fastest)}>Details</button>
                      {aiRecommendations.fastest.booking_url && (
                        <a href={aiRecommendations.fastest.booking_url} target="_blank" rel="noopener noreferrer" className="btn-t-book" style={{ flex: 1, padding: "0.35rem 0.6rem", fontSize: "0.78rem", justifyContent: "center" }}>Book <ExternalLink size={11} /></a>
                      )}
                    </div>
                  </div>
                )}

                {/* 4. Best Budget-Friendly Option */}
                {aiRecommendations.bestValue && (
                  <div className="ai-rec-card best-value">
                    <div>
                      <span className="ai-rec-badge-tag"><Check size={12} /> Best Group Value</span>
                      <h4 className="ai-rec-title">{aiRecommendations.bestValue.operator}</h4>
                      <p className="ai-rec-sub">{aiRecommendations.bestValue.service_name}</p>
                      <div className="ai-rec-timing">
                        ⏱️ {aiRecommendations.bestValue.departure_time} ➔ {aiRecommendations.bestValue.arrival_time} ({aiRecommendations.bestValue.duration})
                      </div>
                      <div className="ai-rec-pricing">
                        <div className="ai-rec-price-val">{money(aiRecommendations.bestValue.ticket_price)} <small style={{ fontSize: "0.74rem", color: "#64748b" }}>/ person</small></div>
                        <div className="ai-rec-group-total" style={{ color: "#1d4ed8" }}>Total: {money(aiRecommendations.bestValue.ticket_price * transportResult.travelers)} for {transportResult.travelers} pax</div>
                      </div>
                    </div>
                    <div className="ai-rec-explanation">
                      💡 <strong>Why AI Recommends:</strong> Maximum overall cost savings for your party of {transportResult.travelers} while retaining confirmed daily departure.
                    </div>
                    <div className="ai-rec-actions">
                      <button type="button" className="btn-t-details" style={{ flex: 1, padding: "0.35rem 0.6rem", fontSize: "0.78rem" }} onClick={() => setSelectedTransportModal(aiRecommendations.bestValue)}>Details</button>
                      {aiRecommendations.bestValue.booking_url && (
                        <a href={aiRecommendations.bestValue.booking_url} target="_blank" rel="noopener noreferrer" className="btn-t-book" style={{ flex: 1, padding: "0.35rem 0.6rem", fontSize: "0.78rem", justifyContent: "center" }}>Book <ExternalLink size={11} /></a>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}
      {selectedTransportModal && (
        <div className="transport-modal-overlay" onClick={() => setSelectedTransportModal(null)}>
          <div className="transport-modal-card" onClick={e => e.stopPropagation()}>
            <button
              type="button"
              className="t-modal-close"
              onClick={() => setSelectedTransportModal(null)}
            >
              <X size={18} />
            </button>

            <div className="t-modal-header">
              <span className={`t-category-badge badge-${selectedTransportModal.mode === "bus" ? "bus" : "train"}`}>
                {selectedTransportModal.mode.toUpperCase()}
              </span>
              <h3>{selectedTransportModal.operator} {selectedTransportModal.service_name ? `· ${selectedTransportModal.service_name}` : ""}</h3>
              <p>{selectedTransportModal.origin} to {selectedTransportModal.destination}</p>
            </div>

            <div className="t-modal-grid">
              <div className="t-modal-item">
                <span className="t-modal-label">Departure</span>
                <span className="t-modal-val">{selectedTransportModal.departure_time}</span>
                <small style={{ color: "#617c6e" }}>{selectedTransportModal.origin_station || selectedTransportModal.origin}</small>
              </div>

              <div className="t-modal-item">
                <span className="t-modal-label">Arrival</span>
                <span className="t-modal-val">{selectedTransportModal.arrival_time}</span>
                <small style={{ color: "#617c6e" }}>{selectedTransportModal.destination_station || selectedTransportModal.destination}</small>
              </div>

              <div className="t-modal-item">
                <span className="t-modal-label">Travel Duration</span>
                <span className="t-modal-val">{selectedTransportModal.duration || "Direct route"}</span>
              </div>

              <div className="t-modal-item">
                <span className="t-modal-label">Estimated Distance</span>
                <span className="t-modal-val">{selectedTransportModal.distance_km || "Regional route"}</span>
              </div>

              <div className="t-modal-item">
                <span className="t-modal-label">Vehicle / Type</span>
                <span className="t-modal-val">{selectedTransportModal.service_type || "Standard"}</span>
              </div>

              <div className="t-modal-item">
                <span className="t-modal-label">Fare</span>
                <span className="t-modal-val" style={{ color: "#164e37" }}>
                  {money(selectedTransportModal.ticket_price)} ({selectedTransportModal.pricing_unit === "per_vehicle" ? "Per Vehicle" : "Per Passenger"})
                </span>
              </div>
            </div>

            {selectedTransportModal.available_classes && (
              <div style={{ marginBottom: "1rem", fontSize: "0.88rem", color: "#2d4a3b" }}>
                <strong>Available Classes:</strong> {selectedTransportModal.available_classes}
              </div>
            )}

            {selectedTransportModal.contact_number && (
              <div style={{ marginBottom: "1rem", fontSize: "0.85rem", color: "#324b3e" }}>
                <strong>Helpline / Contact:</strong> {selectedTransportModal.contact_number}
              </div>
            )}

            <div className="t-modal-portal-note">
              <strong>Official Booking Portal Guidance:</strong>
              <span> Book verified tickets directly on the official transport portal ({selectedTransportModal.mode === "train" ? "IRCTC" : selectedTransportModal.mode === "bus" ? "RedBus / RTC" : "Chauffeur Portal"}) with official confirmation and PNR.</span>
            </div>

            <div className="t-modal-actions">
              <button
                type="button"
                className="btn-t-details"
                onClick={() => setSelectedTransportModal(null)}
              >
                Close
              </button>
              {selectedTransportModal.booking_url && (
                <a
                  href={selectedTransportModal.booking_url}
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
