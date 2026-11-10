import { useState } from "react";
import {
  MapPin, ExternalLink, Navigation, Car, Compass, X, AlertCircle, LocateFixed, Check
} from "lucide-react";
import "./HotelLocationModal.css";

export function getHotelMapQuery(hotel) {
  if (!hotel) return "";
  if (hotel.latitude && hotel.longitude) {
    return `${hotel.latitude},${hotel.longitude}`;
  }
  const parts = [hotel.name];
  if (hotel.address) parts.push(hotel.address);
  else if (hotel.destination) parts.push(hotel.destination);
  return parts.join(", ");
}

export function getGoogleMapsUrl(hotel) {
  if (!hotel) return "#";
  if (hotel.google_maps_url && typeof hotel.google_maps_url === "string" && hotel.google_maps_url.startsWith("http")) {
    return hotel.google_maps_url;
  }
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(getHotelMapQuery(hotel))}`;
}

export function getDirectionsUrl(hotel, origin = "") {
  if (!hotel) return "#";
  const destQuery = getHotelMapQuery(hotel);
  if (origin && origin.trim()) {
    return `https://www.google.com/maps/dir/?api=1&origin=${encodeURIComponent(origin.trim())}&destination=${encodeURIComponent(destQuery)}`;
  }
  return `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(destQuery)}`;
}

export function getTaxiSearchUrl(hotel) {
  if (!hotel) return "#";
  const loc = hotel.address || (hotel.name + ", " + (hotel.destination || ""));
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent("taxi stand near " + loc)}`;
}

export function getAutoSearchUrl(hotel) {
  if (!hotel) return "#";
  const loc = hotel.address || (hotel.name + ", " + (hotel.destination || ""));
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent("auto rickshaw stand near " + loc)}`;
}

export default function HotelLocationModal({ hotel, onClose, initialOrigin = "" }) {
  const [origin, setOrigin] = useState(initialOrigin);
  const [locating, setLocating] = useState(false);
  const [locError, setLocError] = useState("");
  const [locSuccess, setLocSuccess] = useState(false);

  if (!hotel) return null;

  const mapQuery = getHotelMapQuery(hotel);
  const googleMapsUrl = getGoogleMapsUrl(hotel);
  const directionsUrl = getDirectionsUrl(hotel, origin);
  const taxiUrl = getTaxiSearchUrl(hotel);
  const autoUrl = getAutoSearchUrl(hotel);

  function handleUseCurrentLocation() {
    if (!navigator.geolocation) {
      setLocError("Browser geolocation is not supported on this device. Please enter your address or city manually.");
      return;
    }
    setLocating(true);
    setLocError("");
    setLocSuccess(false);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLocating(false);
        const coords = `${pos.coords.latitude.toFixed(5)},${pos.coords.longitude.toFixed(5)}`;
        setOrigin(coords);
        setLocSuccess(true);
      },
      (err) => {
        setLocating(false);
        if (err.code === 1) {
          setLocError("Location access was denied. You can still type your starting city, railway station, airport, or address manually below.");
        } else {
          setLocError("Could not retrieve GPS coordinates. Please type your starting location manually.");
        }
      },
      { timeout: 10000, enableHighAccuracy: true }
    );
  }

  return (
    <div className="hotel-map-backdrop" onClick={onClose} role="dialog" aria-modal="true">
      <div className="hotel-map-modal" onClick={e => e.stopPropagation()}>
        <header className="hotel-map-header">
          <div className="hotel-map-title-block">
            <span className="hotel-map-eyebrow"><MapPin size={13} /> HOTEL LOCATION & NAVIGATION</span>
            <h3>{hotel.name}</h3>
            <p className="hotel-map-address">
              📍 {hotel.address || `${hotel.destination || "Destination area"}, India`}
              {hotel.latitude && hotel.longitude && (
                <span className="hotel-coords-badge">
                  ({Number(hotel.latitude).toFixed(4)}, {Number(hotel.longitude).toFixed(4)})
                </span>
              )}
            </p>
          </div>
          <button type="button" className="hotel-map-close" onClick={onClose} aria-label="Close dialog">
            <X size={18} />
          </button>
        </header>

        <div className="hotel-map-body">
          {/* Embedded Interactive Map */}
          <div className="hotel-map-embed-container">
            <iframe
              title={`Google Map for ${hotel.name}`}
              className="hotel-map-iframe"
              loading="lazy"
              allowFullScreen
              referrerPolicy="no-referrer-when-downgrade"
              src={`https://maps.google.com/maps?q=${encodeURIComponent(mapQuery)}&t=&z=15&ie=UTF8&iwloc=&output=embed`}
            />
            <div className="hotel-map-overlay-actions">
              <a
                href={googleMapsUrl}
                target="_blank"
                rel="noreferrer"
                className="btn-map-action primary"
                title="Open hotel location in Google Maps app or browser"
              >
                <Compass size={14} /> View on Google Maps <ExternalLink size={12} />
              </a>
            </div>
          </div>

          {/* Local Transport & Directions Section */}
          <section className="hotel-directions-section">
            <div className="directions-section-header">
              <Navigation size={16} />
              <h4>Local Transport & Directions</h4>
            </div>

            {/* Starting Location Input & Geolocation */}
            <div className="origin-input-card">
              <label htmlFor="modal-origin-input">
                Starting Location:
                <span className="optional-tag">Optional (Defaults to your current location on Google Maps)</span>
              </label>
              <div className="origin-input-row">
                <input
                  id="modal-origin-input"
                  type="text"
                  placeholder="Enter starting point (e.g. Airport, Railway Station, City)"
                  value={origin}
                  onChange={e => {
                    setOrigin(e.target.value);
                    setLocSuccess(false);
                  }}
                />
                <button
                  type="button"
                  className={`btn-geo-detect ${locSuccess ? "geo-success" : ""}`}
                  onClick={handleUseCurrentLocation}
                  disabled={locating}
                  title="Detect and use current device location"
                >
                  {locating ? (
                    "Locating…"
                  ) : locSuccess ? (
                    <>
                      <Check size={14} /> Located
                    </>
                  ) : (
                    <>
                      <LocateFixed size={14} /> Use Current Location
                    </>
                  )}
                </button>
              </div>

              {locError && (
                <div className="origin-loc-error">
                  <AlertCircle size={13} /> {locError}
                </div>
              )}
            </div>

            {/* Navigation & Local Transport Action Grid */}
            <div className="hotel-transport-actions-grid">
              <a
                href={directionsUrl}
                target="_blank"
                rel="noreferrer"
                className="transport-action-card dir-card"
              >
                <div className="action-icon dir-icon"><Navigation size={18} /></div>
                <div className="action-text">
                  <strong>Get Directions</strong>
                  <span>Turn-by-turn route to {hotel.name}</span>
                </div>
                <ExternalLink size={14} className="action-arrow" />
              </a>

              <a
                href={googleMapsUrl}
                target="_blank"
                rel="noreferrer"
                className="transport-action-card map-card"
              >
                <div className="action-icon map-icon"><Compass size={18} /></div>
                <div className="action-text">
                  <strong>View on Google Maps</strong>
                  <span>See roads, nearby landmarks & satellite</span>
                </div>
                <ExternalLink size={14} className="action-arrow" />
              </a>

              <a
                href={taxiUrl}
                target="_blank"
                rel="noreferrer"
                className="transport-action-card taxi-card"
              >
                <div className="action-icon taxi-icon"><Car size={18} /></div>
                <div className="action-text">
                  <strong>Find Nearby Taxi Services</strong>
                  <span>Locate taxi stands and cab points on Google Maps</span>
                </div>
                <ExternalLink size={14} className="action-arrow" />
              </a>

              <a
                href={autoUrl}
                target="_blank"
                rel="noreferrer"
                className="transport-action-card auto-card"
              >
                <div className="action-icon auto-icon">🛺</div>
                <div className="action-text">
                  <strong>Find Nearby Auto Services</strong>
                  <span>Locate auto rickshaw stands on Google Maps</span>
                </div>
                <ExternalLink size={14} className="action-arrow" />
              </a>
            </div>

            <div className="transport-disclaimer-note">
              ℹ️ <em>Directions and transport searches open live Google Maps points near the hotel. Roamly assists with real-world navigation and directions without claiming unverified in-app ride bookings.</em>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}

