import { useState } from "react";
import { ArrowRight, Sparkles } from "lucide-react";
import { json } from "../api";
import "./HotelRecommendations.css";

const money = amount => `₹${Number(amount).toLocaleString("en-IN")}`;

export default function HotelRecommendations({ destinations, hotels }) {
  const [budget, setBudget] = useState("");
  const [travelers, setTravelers] = useState(2);
  const [nights, setNights] = useState(2);
  const [destinationId, setDestinationId] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function findHotels(event) {
    event.preventDefault();
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const recommendations = await json("/assistant/recommendations", {
        method: "POST",
        body: JSON.stringify({
          budget_per_person: Number(budget),
          travelers: Number(travelers),
          nights: Number(nights),
          destination_id: destinationId || null,
        }),
      });
      setResult(recommendations);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  }

  const options = result
    ? result.matches.length ? result.matches : result.alternatives
    : [];
  const unpricedHotels = result && options.length === 0
    ? hotels.filter(hotel => hotel.active && (!destinationId || hotel.destination_id === Number(destinationId))).slice(0, 6)
    : [];

  return <section className="section-block recommendation-section" aria-labelledby="recommendation-title">
    <div className="recommendation-heading">
      <div>
        <span className="eyebrow"><Sparkles size={13} /> AI-ASSISTED STAY FINDER</span>
        <h2 id="recommendation-title">Find a hotel that fits your trip</h2>
        <p>Tell us your budget and group size. Choose a destination if you have one in mind.</p>
      </div>
    </div>
    <form className="recommendation-form" onSubmit={findHotels}>
      <label>Budget per person (₹)
        <input type="number" min="1" max="10000000" step="1" required value={budget} onChange={event => setBudget(event.target.value)} placeholder="e.g. 10000" />
      </label>
      <label>People travelling
        <input type="number" min="1" max="20" required value={travelers} onChange={event => setTravelers(event.target.value)} />
      </label>
      <label>Nights
        <input type="number" min="1" max="30" required value={nights} onChange={event => setNights(event.target.value)} />
      </label>
      <label>Destination <span className="recommendation-optional">Optional</span>
        <select value={destinationId} onChange={event => setDestinationId(event.target.value)}>
          <option value="">Any destination</option>
          {destinations.map(destination => <option key={destination.id} value={destination.id}>{destination.name}</option>)}
        </select>
      </label>
      <button className="button primary recommendation-submit" disabled={loading}>
        {loading ? "Finding stays…" : "Find hotels"} <ArrowRight size={16} />
      </button>
    </form>

    {error && <div className="alert" role="alert">{error}</div>}
    {result && <div className="recommendation-results" aria-live="polite">
      <div className="recommendation-result-heading">
        <div>
          <h3>{result.matches.length ? "Recommended stays" : result.alternatives.length ? "Closest available stays" : unpricedHotels.length ? "Rates unavailable for budget comparison" : "No stays to show"}</h3>
          <p>{unpricedHotels.length && !options.length
            ? "We found property listings, but prices are not available to compare with your budget. Contact a property for current rates."
            : `${result.message} Estimates cover lodging only; confirm rates and availability with the property.`}</p>
        </div>
        {result.matches.length > 0 && <span className="recommendation-count">{result.matches.length} matches</span>}
      </div>
      {options.length > 0 && <div className="recommendation-grid">
        {options.map((option, index) => <article className="recommendation-card" key={`${option.hotel_id}-${option.room_type_id ?? "hotel"}-${index}`}>
          <span className={`recommendation-badge ${option.within_budget ? "" : "over-budget"}`}>
            {option.is_demo ? "Sample demo price · not live" : option.within_budget ? "Within budget" : `${money(option.over_budget_per_person)} over budget per person`}
          </span>
          <h4>{option.hotel}</h4>
          <p className="recommendation-place">{option.destination}{option.region ? ` · ${option.region}` : ""}</p>
          <p className="recommendation-room">{option.room_type} · {option.travelers} {option.travelers === 1 ? "person" : "people"} · {option.nights} {option.nights === 1 ? "night" : "nights"}</p>
          <div className="recommendation-price">
            <strong>{money(option.estimated_per_person)}<small> / person</small></strong>
            <span>{money(option.estimated_total)} lodging total</span>
          </div>
          {option.is_demo && <p className="recommendation-place">College-project estimate only; prices and inventory are not live or verified.</p>}
          <a className="recommendation-link" href={`#destination-${option.destination_id}`}>
            Explore {option.destination} <ArrowRight size={14} />
          </a>
        </article>)}
      </div>}
      {unpricedHotels.length > 0 && <div className="unpriced-recommendations">
        <h4>Properties to explore <span>Rates not listed</span></h4>
        <p>These properties may be worth exploring, but no usable prices are listed, so we can’t confirm they fit your budget. Contact the property for current rates.</p>
        <div className="recommendation-grid">
          {unpricedHotels.map(hotel => <article className="recommendation-card" key={hotel.id}>
            <span className="recommendation-badge rate-unavailable">Price unavailable</span>
            <h4>{hotel.name}</h4>
            <p className="recommendation-place">{hotel.destination}</p>
            {hotel.source_url && <a className="recommendation-link" href={hotel.source_url} target="_blank" rel="noreferrer">Property information <ArrowRight size={14} /></a>}
            <a className="recommendation-link" href={`#destination-${hotel.destination_id}`}>Explore {hotel.destination} listings <ArrowRight size={14} /></a>
          </article>)}
        </div>
      </div>}
    </div>}
  </section>;
}
