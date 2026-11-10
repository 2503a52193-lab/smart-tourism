import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  BedDouble,
  Building2,
  Bus,
  CheckCircle2,
  Clock,
  Compass,
  Download,
  ExternalLink,
  LogOut,
  MapPin,
  MapPinned,
  Phone,
  RefreshCw,
  Search,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Train,
  Users,
  XCircle,
} from "lucide-react";
import { api, json } from "../api";
import "./Admin.css";
import "./CatalogAdmin.css";

function AdminShell({ children }) {
  const navigate = useNavigate();
  function logout() {
    localStorage.removeItem("tourism_token");
    localStorage.removeItem("tourism_user");
    navigate("/admin/login");
  }

  return (
    <div className="admin-layout">
      <aside className="sidebar">
        <Link to="/admin" className="admin-brand"><Compass /> roamly<span>.</span></Link>
        <span className="side-label">MANAGEMENT</span>
        <nav className="side-nav">
          <a href="#customers"><Users /> Registered users</a>
          <a href="#bookings"><BedDouble /> Hotel bookings</a>
          <a href="#destinations"><MapPinned /> Destinations</a>
          <a href="#hotels"><Building2 /> Hotels & rooms</a>
          <a href="#places"><MapPin /> Places</a>
          <a href="#transport"><Bus /> Transport options</a>
        </nav>
        <div className="sidebar-bottom">
          <div className="admin-profile">
            <span className="avatar admin-avatar">A</span>
            <div><strong>Administrator</strong><small>Travel catalog</small></div>
          </div>
          <button onClick={logout} className="side-logout"><LogOut size={17} /> Sign out</button>
        </div>
      </aside>
      <main className="admin-main">
        <header className="admin-topline">
          <span>Travel catalog management</span>
          <span className="admin-live"><i /> Live database</span>
        </header>
        <div className="admin-content">
          <div className="page-title">
            <div>
              <span className="eyebrow">ROAMLY ADMIN</span>
              <h1>Destinations, Hotels & Bookings</h1>
              <p>Manage verified destinations, properties, room inventories, and customer reservations.</p>
            </div>
          </div>
          {children}
        </div>
      </main>
    </div>
  );
}

const field = (form, name) => String(form.get(name) || "").trim();

export default function Admin() {
  const [customers, setCustomers] = useState([]);
  const [destinations, setDestinations] = useState([]);
  const [hotels, setHotels] = useState([]);
  const [places, setPlaces] = useState([]);
  const [transports, setTransports] = useState([]);
  const [bookings, setBookings] = useState([]);
  const [includeArchivedHotels, setIncludeArchivedHotels] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [editingDestinationId, setEditingDestinationId] = useState(null);
  const [editingHotelId, setEditingHotelId] = useState(null);
  const [editingRoomId, setEditingRoomId] = useState(null);
  const [editingTransportId, setEditingTransportId] = useState(null);
  const [addTransportCategory, setAddTransportCategory] = useState("bus");
  const [transportSearch, setTransportSearch] = useState("");
  const [transportCategoryFilter, setTransportCategoryFilter] = useState("all");
  const [transportStatusFilter, setTransportStatusFilter] = useState("all");

  // Bookings filtering and searching
  const [bookingSearch, setBookingSearch] = useState("");
  const [bookingStatusFilter, setBookingStatusFilter] = useState("all");
  const [seedingLoading, setSeedingLoading] = useState(false);

  async function loadCustomers() {
    setCustomers(await json("/admin/customers"));
  }

  async function loadBookings() {
    setBookings(await json("/admin/bookings"));
  }

  async function loadCatalog(includeArchived = includeArchivedHotels) {
    const [destinationRows, hotelRows, placeRows, transportRows] = await Promise.all([
      json("/admin/destinations"),
      json(`/admin/hotels${includeArchived ? "?include_archived=true" : ""}`),
      json("/admin/attractions"),
      json("/admin/transport/services").catch(() => []),
    ]);
    setDestinations(destinationRows);
    setHotels(hotelRows);
    setPlaces(placeRows);
    setTransports(transportRows);
  }

  useEffect(() => {
    loadCatalog().catch(requestError => setError(requestError.message));
    loadCustomers().catch(requestError => setError(requestError.message));
    loadBookings().catch(requestError => setError(requestError.message));
  }, []);

  async function exportBookings() {
    try {
      const response = await api("/admin/bookings/export");
      const fileUrl = URL.createObjectURL(await response.blob());
      const link = document.createElement("a");
      link.href = fileUrl;
      link.download = "hotel-bookings.xlsx";
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(fileUrl);
      setError("");
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  async function seedDemoData() {
    try {
      setSeedingLoading(true);
      setError("");
      setNotice("Seeding demonstration hotels and room types for all destinations...");
      const res = await json("/admin/catalog/seed-demo-data", { method: "POST" });
      await loadCatalog();
      await loadBookings();
      setNotice(res.message || "Demonstration hotels and rooms populated successfully.");
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setSeedingLoading(false);
    }
  }

  async function updateBookingStatus(bookingId, newStatus) {
    try {
      await json(`/admin/bookings/${bookingId}`, {
        method: "PATCH",
        body: JSON.stringify({ status: newStatus }),
      });
      await loadBookings();
      setError("");
      if (newStatus === "confirmed") {
        setNotice(`Booking #${bookingId} successfully confirmed! Customer reservation is now verified and active.`);
      } else if (newStatus === "cancelled") {
        setNotice(`Booking #${bookingId} has been cancelled.`);
      } else {
        setNotice(`Booking #${bookingId} status reopened as pending.`);
      }
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  async function submitAction(event, action, successMessage) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    try {
      await action(form);
      await loadCatalog();
      formElement.reset();
      setError("");
      setNotice(successMessage);
      return true;
    } catch (requestError) {
      setError(requestError.message);
      return false;
    }
  }

  async function addDestination(form) {
    await json("/admin/destinations", {
      method: "POST",
      body: JSON.stringify({
        name: field(form, "name"),
        region: field(form, "region"),
        image_url: field(form, "image_url"),
        description: field(form, "description"),
      }),
    });
  }

  async function saveDestination(event, destination) {
    const saved = await submitAction(event, async form => {
      await json(`/admin/destinations/${destination.id}`, {
        method: "PUT",
        body: JSON.stringify({
          name: field(form, "name"),
          region: field(form, "region"),
          image_url: field(form, "image_url"),
          description: field(form, "description"),
        }),
      });
    }, "Destination updated.");
    if (saved) setEditingDestinationId(null);
  }

  async function archive(path, label) {
    try {
      await json(path, { method: "DELETE" });
      await loadCatalog();
      setError("");
      setNotice(`${label} archived.`);
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  async function setDestinationActive(destination, active) {
    try {
      await json(`/admin/destinations/${destination.id}`, {
        method: "PUT",
        body: JSON.stringify({ active }),
      });
      await loadCatalog();
      setError("");
      setNotice(active ? "Destination restored." : "Destination archived.");
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  function hotelPayload(form) {
    const isDemo = form.get("is_demo") === "true";
    const priceBasis = field(form, "price_basis") || (isDemo ? "estimate" : "unverified");
    return {
      name: field(form, "name"),
      destination_id: Number(form.get("destination_id")),
      nightly_rate: Number(form.get("nightly_rate")),
      price_basis: priceBasis,
      rating: Number(form.get("rating") || 4.5),
      address: field(form, "address"),
      google_maps_url: field(form, "google_maps_url") || "",
      latitude: field(form, "latitude") ? Number(form.get("latitude")) : null,
      longitude: field(form, "longitude") ? Number(form.get("longitude")) : null,
      description: field(form, "description"),
      image_url: field(form, "image_url"),
      source_url: field(form, "source_url"),
      facilities: field(form, "facilities").split(",").map(item => item.trim()).filter(Boolean),
      check_in_policy: field(form, "check_in_policy") || "14:00",
      check_out_policy: field(form, "check_out_policy") || "11:00",
      is_demo: isDemo,
    };
  }

  async function addHotel(form) {
    await json("/admin/hotels", {
      method: "POST",
      body: JSON.stringify(hotelPayload(form)),
    });
  }

  async function saveHotel(event, hotel) {
    const saved = await submitAction(event, async form => {
      await json(`/admin/hotels/${hotel.id}`, {
        method: "PUT",
        body: JSON.stringify(hotelPayload(form)),
      });
    }, "Hotel details updated.");
    if (saved) setEditingHotelId(null);
  }

  async function addRoom(event, hotel) {
    const formElement = event.currentTarget;
    const saved = await submitAction(event, async form => {
      const rate = field(form, "nightly_rate");
      const totalRooms = field(form, "total_rooms");
      const availableRooms = field(form, "available_rooms");
      await json(`/admin/hotels/${hotel.id}/rooms`, {
        method: "POST",
        body: JSON.stringify({
          name: field(form, "name"),
          nightly_rate: rate ? Number(rate) : 0,
          price_basis: rate ? field(form, "price_basis") : "unavailable",
          capacity: Number(form.get("capacity") || 2),
          total_rooms: totalRooms ? Number(totalRooms) : null,
          available_rooms: availableRooms ? Number(availableRooms) : (totalRooms ? Number(totalRooms) : null),
        }),
      });
    }, "Room type added.");
    if (saved) formElement.reset();
  }

  async function saveRoom(event, room) {
    const saved = await submitAction(event, async form => {
      const rate = field(form, "nightly_rate");
      const totalRooms = field(form, "total_rooms");
      const availableRooms = field(form, "available_rooms");
      await json(`/admin/rooms/${room.id}`, {
        method: "PUT",
        body: JSON.stringify({
          name: field(form, "name"),
          nightly_rate: rate ? Number(rate) : 0,
          price_basis: rate ? field(form, "price_basis") : "unavailable",
          capacity: Number(form.get("capacity")),
          total_rooms: totalRooms ? Number(totalRooms) : null,
          available_rooms: availableRooms ? Number(availableRooms) : null,
        }),
      });
    }, "Room details updated.");
    if (saved) setEditingRoomId(null);
  }

  async function restoreRoom(room) {
    try {
      await json(`/admin/rooms/${room.id}`, {
        method: "PUT",
        body: JSON.stringify({ active: true }),
      });
      await loadCatalog();
      setError("");
      setNotice("Room type restored.");
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  async function setHotelActive(hotel, active) {
    try {
      await json(`/admin/hotels/${hotel.id}`, {
        method: "PUT",
        body: JSON.stringify({ active }),
      });
      await loadCatalog();
      setError("");
      setNotice(active ? "Hotel restored." : "Hotel archived.");
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  async function addPlace(form) {
    await json("/admin/attractions", {
      method: "POST",
      body: JSON.stringify({
        destination_id: Number(form.get("destination_id")),
        name: field(form, "name"),
        category: field(form, "category") || "Sightseeing",
        description: field(form, "description"),
        interests: field(form, "interests").split(",").map(item => item.trim()).filter(Boolean),
        estimated_cost: Number(form.get("estimated_cost") || 0),
        duration_hours: Number(form.get("duration_hours") || 2),
        cost_basis: field(form, "cost_basis") || "unverified",
        source_url: field(form, "source_url"),
      }),
    });
  }

  async function deletePlace(place) {
    try {
      await json(`/admin/attractions/${place.id}`, { method: "DELETE" });
      await loadCatalog();
      setError("");
      setNotice("Place removed.");
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  function transportPayload(form) {
    const rawClassFares = field(form, "class_fares");
    let classFaresObj = {};
    if (rawClassFares) {
      try { classFaresObj = JSON.parse(rawClassFares); }
      catch { classFaresObj = {}; }
    }
    const destVal = form.get("destination_id");
    return {
      mode: field(form, "mode"),
      operator: field(form, "operator"),
      service_name: field(form, "service_name"),
      service_type: field(form, "service_type"),
      origin: field(form, "origin"),
      origin_station: field(form, "origin_station"),
      destination: field(form, "destination"),
      destination_station: field(form, "destination_station"),
      boarding_point: field(form, "boarding_point") || null,
      dropping_point: field(form, "dropping_point") || null,
      booking_status: field(form, "booking_status") || "available",
      departure_time: field(form, "departure_time"),
      arrival_time: field(form, "arrival_time"),
      duration: field(form, "duration"),
      distance_km: field(form, "distance_km"),
      ticket_price: Number(form.get("ticket_price") || 0),
      pricing_unit: field(form, "pricing_unit") || "per_person",
      available_classes: field(form, "available_classes"),
      class_fares: classFaresObj,
      available_seats: form.get("available_seats") ? Number(form.get("available_seats")) : null,
      contact_number: field(form, "contact_number"),
      booking_url: field(form, "booking_url"),
      source_url: field(form, "booking_url"),
      price_basis: field(form, "price_basis") || "verified",
      availability_verified: form.get("availability_verified") === "on" || form.get("availability_verified") === "true",
      destination_id: destVal ? Number(destVal) : null,
      is_daily: true,
    };
  }

  async function addTransport(event) {
    await submitAction(event, async form => {
      await json("/admin/transport/services", {
        method: "POST",
        body: JSON.stringify(transportPayload(form)),
      });
    }, "Transport service added successfully.");
  }

  async function saveTransport(event, transport) {
    const saved = await submitAction(event, async form => {
      await json(`/admin/transport/services/${transport.id}`, {
        method: "PUT",
        body: JSON.stringify(transportPayload(form)),
      });
    }, "Transport service details updated.");
    if (saved) setEditingTransportId(null);
  }

  async function archiveTransport(transport) {
    try {
      await json(`/admin/transport/services/${transport.id}`, { method: "DELETE" });
      await loadCatalog();
      setError("");
      setNotice(`Transport service #${transport.id} (${transport.operator}) archived.`);
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  async function restoreTransport(transport) {
    try {
      await json(`/admin/transport/services/${transport.id}/restore`, { method: "POST" });
      await loadCatalog();
      setError("");
      setNotice(`Transport service #${transport.id} (${transport.operator}) restored to active.`);
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  async function seedTransportCatalog() {
    try {
      setError("");
      setNotice("Seeding verified-style and estimated transport catalog...");
      const res = await json("/admin/transport/seed", { method: "POST" });
      await loadCatalog();
      setNotice(res.message || "Transport catalog seeded successfully.");
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  // Booking statistics
  const totalBookingsCount = bookings.length;
  const pendingBookingsCount = bookings.filter(b => b.status === "pending").length;
  const confirmedBookingsCount = bookings.filter(b => b.status === "confirmed").length;
  const cancelledBookingsCount = bookings.filter(b => b.status === "cancelled").length;
  const totalRevenue = bookings
    .filter(b => b.status !== "cancelled")
    .reduce((sum, b) => sum + (Number(b.amount) || 0), 0);

  // Filtered bookings
  const filteredBookings = bookings.filter(b => {
    if (bookingStatusFilter !== "all" && b.status !== bookingStatusFilter) return false;
    if (bookingSearch.trim()) {
      const q = bookingSearch.toLowerCase();
      const ref = (b.booking_reference || `BK-${String(b.id).padStart(6, "0")}`).toLowerCase();
      const customer = (b.customer_name || "").toLowerCase();
      const email = (b.customer_email || "").toLowerCase();
      const dest = (b.destination || "").toLowerCase();
      const hotel = (b.hotel || "").toLowerCase();
      return ref.includes(q) || customer.includes(q) || email.includes(q) || dest.includes(q) || hotel.includes(q);
    }
    return true;
  });

  return (
    <AdminShell>
      {error && <div className="alert">{error}<button onClick={() => setError("")}>Dismiss</button></div>}
      {notice && <div className="success">{notice}<button onClick={() => setNotice("")}>Dismiss</button></div>}

      <section id="customers" className="panel customers-panel">
        <div className="panel-heading">
          <div>
            <h2>Registered users <span className="count-pill">{customers.length}</span></h2>
            <p>Customer accounts created through registration.</p>
          </div>
          <button type="button" onClick={() => loadCustomers().catch(requestError => setError(requestError.message))}>Refresh list</button>
        </div>
        {customers.length === 0 ? (
          <p className="muted">No customer accounts registered yet.</p>
        ) : (
          <div className="customer-admin-list">
            {customers.map(customer => (
              <div key={customer.id}>
                <span className="avatar">{customer.name.slice(0, 1).toUpperCase()}</span>
                <strong>{customer.name}</strong>
                <span>{customer.email}</span>
                <small>Joined {new Date(customer.created_at).toLocaleDateString()}</small>
                <span>{customer.bookings} {customer.bookings === 1 ? "booking" : "bookings"}</span>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Bookings Section */}
      <section id="bookings" className="panel booking-admin-panel">
        <div className="panel-heading">
          <div>
            <h2>Hotel bookings <span className="count-pill">{bookings.length}</span></h2>
            <p>Customer reservations with real-time room inventory tracking and status control.</p>
          </div>
          <div className="catalog-actions">
            <button type="button" onClick={seedDemoData} disabled={seedingLoading} className="seed-demo-btn">
              <Sparkles size={14} /> {seedingLoading ? "Seeding..." : "Seed Demo Hotels & Rooms"}
            </button>
            <button type="button" onClick={() => loadBookings().catch(requestError => setError(requestError.message))}>
              <RefreshCw size={14} /> Refresh
            </button>
            <button type="button" onClick={exportBookings}>
              <Download size={14} /> Export Excel
            </button>
          </div>
        </div>

        {/* Metric stats cards */}
        <div className="admin-stats-row">
          <div className="admin-stat-card">
            <span className="stat-label">Total Bookings</span>
            <strong className="stat-val">{totalBookingsCount}</strong>
          </div>
          <div className="admin-stat-card">
            <span className="stat-label">Pending</span>
            <strong className="stat-val stat-pending">{pendingBookingsCount}</strong>
          </div>
          <div className="admin-stat-card">
            <span className="stat-label">Confirmed</span>
            <strong className="stat-val stat-confirmed">{confirmedBookingsCount}</strong>
          </div>
          <div className="admin-stat-card">
            <span className="stat-label">Cancelled</span>
            <strong className="stat-val stat-cancelled">{cancelledBookingsCount}</strong>
          </div>
          <div className="admin-stat-card">
            <span className="stat-label">Active Booking Value</span>
            <strong className="stat-val stat-revenue">₹{totalRevenue.toLocaleString("en-IN")}</strong>
          </div>
        </div>

        {/* Search & Filter Toolbar */}
        <div className="admin-filter-bar">
          <div className="filter-search-box">
            <Search size={14} />
            <input
              type="text"
              placeholder="Search reference (e.g. BK-000001), user, destination, hotel..."
              value={bookingSearch}
              onChange={e => setBookingSearch(e.target.value)}
            />
            {bookingSearch && (
              <button type="button" className="clear-search-btn" onClick={() => setBookingSearch("")}>×</button>
            )}
          </div>
          <div className="filter-status-group">
            <label>Status:</label>
            <select value={bookingStatusFilter} onChange={e => setBookingStatusFilter(e.target.value)}>
              <option value="all">All Statuses ({totalBookingsCount})</option>
              <option value="pending">Pending ({pendingBookingsCount})</option>
              <option value="confirmed">Confirmed ({confirmedBookingsCount})</option>
              <option value="cancelled">Cancelled ({cancelledBookingsCount})</option>
            </select>
          </div>
        </div>

        {filteredBookings.length === 0 ? (
          <p className="muted" style={{ padding: "1.5rem", textAlign: "center" }}>
            {bookings.length === 0 ? "No hotel bookings have been saved yet." : "No bookings match your current filter."}
          </p>
        ) : (
          <div className="booking-table-wrap">
            <table className="booking-admin-table">
              <thead>
                <tr>
                  <th>Reference</th>
                  <th>Customer</th>
                  <th>Hotel & Address</th>
                  <th>Dates & Rooms</th>
                  <th>Guests</th>
                  <th>Total</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredBookings.map(booking => {
                  const ref = booking.booking_reference || `BK-${String(booking.id).padStart(6, "0")}`;
                  return (
                    <tr key={booking.id}>
                      <td>
                        <strong className="booking-ref-pill">{ref}</strong>
                        <small>ID #{booking.id}</small>
                      </td>
                      <td>
                        <strong>{booking.customer_name}</strong>
                        <small>{booking.customer_email}</small>
                      </td>
                      <td>
                        <strong>{booking.hotel}</strong>
                        <small style={{ color: "#0d9488" }}>{booking.destination}</small>
                        {booking.hotel_address && <small style={{ maxWidth: 220, overflow: "hidden", textOverflow: "ellipsis" }}>{booking.hotel_address}</small>}
                      </td>
                      <td>
                        <span>{booking.check_in} → {booking.check_out}</span>
                        <small>{booking.room_type || "Standard Room"} · {booking.rooms} {booking.rooms === 1 ? "room" : "rooms"}</small>
                      </td>
                      <td>{booking.guests} {booking.guests === 1 ? "guest" : "guests"}</td>
                      <td><strong>₹{Number(booking.amount).toLocaleString("en-IN")}</strong></td>
                      <td>
                        <span className={`status-tag status-${booking.status}`}>
                          {booking.status === "confirmed" && <CheckCircle2 size={12} />}
                          {booking.status === "pending" && <Clock size={12} />}
                          {booking.status === "cancelled" && <XCircle size={12} />}
                          {booking.status.toUpperCase()}
                        </span>
                        {booking.is_demo && <small className="demo-tag">DEMO</small>}
                      </td>
                      <td>
                        <div className="action-buttons-cell">
                          {booking.status === "pending" && (
                            <>
                              <button
                                type="button"
                                className="btn-action confirm-btn"
                                onClick={() => updateBookingStatus(booking.id, "confirmed")}
                              >
                                Confirm
                              </button>
                              <button
                                type="button"
                                className="btn-action cancel-btn"
                                onClick={() => updateBookingStatus(booking.id, "cancelled")}
                              >
                                Cancel
                              </button>
                            </>
                          )}
                          {booking.status === "confirmed" && (
                            <button
                              type="button"
                              className="btn-action cancel-btn"
                              onClick={() => updateBookingStatus(booking.id, "cancelled")}
                            >
                              Cancel
                            </button>
                          )}
                          {booking.status === "cancelled" && (
                            <>
                              <button
                                type="button"
                                className="btn-action confirm-btn"
                                onClick={() => updateBookingStatus(booking.id, "confirmed")}
                              >
                                Confirm
                              </button>
                              <button
                                type="button"
                                className="btn-action restore-btn"
                                onClick={() => updateBookingStatus(booking.id, "pending")}
                              >
                                Reopen
                              </button>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Destinations Section */}
      <section id="destinations" className="panel catalog-manager">
        <div className="panel-heading">
          <div><h2>Destinations <span className="count-pill">{destinations.length}</span></h2><p>Add, update, archive, or restore destination details.</p></div>
        </div>
        <div className="manage-columns">
          <form className="manage-form" onSubmit={event => submitAction(event, addDestination, "Destination added.")}>
            <h3>Add destination</h3>
            <input name="name" required placeholder="Destination name" />
            <input name="region" placeholder="Region or state" />
            <input name="image_url" type="url" placeholder="Image URL (optional)" />
            <textarea name="description" placeholder="Description" rows="3" />
            <button className="button primary">Add destination</button>
          </form>
          <div className="manage-list">
            {destinations.length === 0 ? (
              <p className="muted" style={{ padding: "1rem" }}>No destinations added yet.</p>
            ) : (
              destinations.map(destination => (
                <div key={destination.id} className="catalog-item">
                  {editingDestinationId === destination.id ? (
                    <form className="catalog-edit-form" onSubmit={event => saveDestination(event, destination)}>
                      <input name="name" required defaultValue={destination.name} aria-label="Destination name" />
                      <input name="region" defaultValue={destination.region} placeholder="Region" aria-label="Region" />
                      <input name="image_url" type="url" defaultValue={destination.image_url} placeholder="Image URL" aria-label="Image URL" />
                      <textarea name="description" rows="3" defaultValue={destination.description} aria-label="Description" />
                      <div className="catalog-actions">
                        <button className="button primary">Save destination</button>
                        <button type="button" onClick={() => setEditingDestinationId(null)}>Cancel</button>
                      </div>
                    </form>
                  ) : (
                    <>
                      <span>
                        <strong>{destination.name}</strong>
                        <small>{destination.region || "Region not set"} · {destination.active ? "Active" : "Archived"}</small>
                      </span>
                      <div className="catalog-actions">
                        <button type="button" onClick={() => setEditingDestinationId(destination.id)}>Edit</button>
                        {destination.active ? (
                          <button type="button" onClick={() => archive(`/admin/destinations/${destination.id}`, "Destination")}>Delete</button>
                        ) : (
                          <button type="button" onClick={() => setDestinationActive(destination, true)}>Restore</button>
                        )}
                      </div>
                    </>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      </section>

      {/* Places / Attractions Section */}
      <section id="places" className="panel catalog-manager">
        <div className="panel-heading">
          <div><h2>Places <span className="count-pill">{places.length}</span></h2><p>Add destination places and attractions to the catalog.</p></div>
        </div>
        <form className="manage-form place-create-form" onSubmit={event => submitAction(event, addPlace, "Place added.")}>
          <h3>Add place</h3>
          <div className="manage-columns">
            <input name="name" required placeholder="Place name" />
            <select name="destination_id" required defaultValue="">
              <option value="" disabled>Choose destination</option>
              {destinations.filter(item => item.active).map(item => (
                <option key={item.id} value={item.id}>{item.name}</option>
              ))}
            </select>
            <input name="category" placeholder="Category (e.g. Museum)" />
            <input name="interests" placeholder="Interests, separated by commas" />
            <textarea name="description" rows="3" placeholder="Description" />
            <input name="estimated_cost" type="number" min="0" step=".01" defaultValue="0" placeholder="Visitor cost estimate" />
            <input name="duration_hours" type="number" min=".25" max="24" step=".25" defaultValue="2" placeholder="Visit duration (hours)" />
            <select name="cost_basis" defaultValue="unverified">
              <option value="unverified">Unverified cost</option>
              <option value="estimate">Estimated cost</option>
              <option value="verified">Verified cost</option>
              <option value="free">Free entry</option>
            </select>
            <input name="source_url" type="url" placeholder="Visitor information source (HTTPS)" />
          </div>
          <button className="button primary">Add place</button>
        </form>
        <div className="manage-list">
          {places.length === 0 ? (
            <p className="muted" style={{ padding: "1rem" }}>No places added yet.</p>
          ) : (
            places.map(place => (
              <div key={place.id} className="catalog-item">
                <span>
                  <strong>{place.name}</strong>
                  <small>{place.destination} · {place.category}</small>
                </span>
                <span>{place.cost_basis === "unverified" ? "Cost unverified" : `₹${place.estimated_cost.toLocaleString("en-IN")}`}</span>
                <div className="catalog-actions">
                  <button type="button" onClick={() => deletePlace(place)}>Delete</button>
                </div>
              </div>
            ))
          )}
        </div>
      </section>

      {/* Hotels & Rooms Section */}
      <section id="hotels" className="panel catalog-manager">
        <div className="panel-heading">
          <div>
            <h2>Hotels & rooms <span className="count-pill">{hotels.length}</span></h2>
            <p>Manage properties, detailed addresses, policies, room types, rates, and inventory.</p>
          </div>
          <div className="catalog-actions">
            <button type="button" onClick={seedDemoData} disabled={seedingLoading} className="seed-demo-btn">
              <Sparkles size={14} /> Refresh Demo Hotels
            </button>
            <button type="button" onClick={async () => {
              const next = !includeArchivedHotels;
              setIncludeArchivedHotels(next);
              try {
                await loadCatalog(next);
                setError("");
              } catch (requestError) {
                setError(requestError.message);
              }
            }}>
              {includeArchivedHotels ? "Hide archived" : "Show archived"}
            </button>
          </div>
        </div>

        {/* Add Hotel Form */}
        <form className="manage-form hotel-create-form" onSubmit={event => submitAction(event, addHotel, "Hotel added successfully.")}>
          <h3>Add new hotel property</h3>
          <div className="hotel-form-grid">
            <label>
              Hotel or Property Name *
              <input name="name" required placeholder="e.g. Grand Heritage Palace" />
            </label>
            <label>
              Destination *
              <select name="destination_id" required defaultValue="">
                <option value="" disabled>Choose destination for this hotel</option>
                {destinations.filter(item => item.active).map(item => (
                  <option key={item.id} value={item.id}>{item.name}</option>
                ))}
              </select>
            </label>
            <label>
              Property Address *
              <input name="address" required placeholder="Full address (e.g. Beach Road, Calangute, Goa)" />
            </label>
            <label>
              Google Maps Link (Optional)
              <input name="google_maps_url" type="url" placeholder="https://maps.google.com/?q=..." />
            </label>
            <label>
              Latitude (Optional)
              <input name="latitude" type="number" step="any" placeholder="e.g. 15.5432" />
            </label>
            <label>
              Longitude (Optional)
              <input name="longitude" type="number" step="any" placeholder="e.g. 73.7554" />
            </label>
            <label>
              Image URL
              <input name="image_url" type="url" placeholder="https://images.unsplash.com/..." />
            </label>
            <label>
              Nightly Rate (INR) *
              <input name="nightly_rate" type="number" min="1" step="1" required placeholder="Starting rate per night" />
            </label>
            <label>
              Hotel Rating (0–5)
              <input name="rating" type="number" min="0" max="5" step=".1" defaultValue="4.5" required />
            </label>
            <label>
              Property Type / Classification
              <select name="is_demo" defaultValue="false">
                <option value="false">Verified Real Property</option>
                <option value="true">Sample Demonstration Property</option>
              </select>
            </label>
            <label>
              Rate Verification Basis
              <select name="price_basis" defaultValue="estimate">
                <option value="estimate">Demonstration / Estimate</option>
                <option value="verified">Verified Official Rate</option>
                <option value="unverified">Unverified</option>
              </select>
            </label>
            <label>
              Official Website / Source URL
              <input name="source_url" type="url" placeholder="Official property website (HTTPS)" />
            </label>
            <label>
              Facilities & Amenities (comma-separated)
              <input name="facilities" placeholder="WiFi, Swimming Pool, Spa, Free Breakfast, Parking" />
            </label>
            <label>
              Check-in Policy
              <input name="check_in_policy" defaultValue="14:00" placeholder="e.g. 14:00" />
            </label>
            <label>
              Check-out Policy
              <input name="check_out_policy" defaultValue="11:00" placeholder="e.g. 11:00" />
            </label>
          </div>
          <label style={{ marginTop: "6px" }}>
            Property Description
            <textarea name="description" rows="2" placeholder="Brief overview of amenities, view, and location..." />
          </label>
          <button className="button primary" style={{ marginTop: "10px" }}>Add hotel property</button>
        </form>

        {/* Hotels List */}
        <div className="hotel-catalog-list">
          {hotels.length === 0 ? (
            <p className="muted" style={{ padding: "1.5rem", textAlign: "center" }}>
              No hotels added yet. Use the form above or click "Refresh Demo Hotels" to seed sample properties.
            </p>
          ) : (
            hotels.map(hotel => (
              <article className="hotel-catalog-card" key={hotel.id}>
                <div className="hotel-catalog-heading">
                  <div>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
                      <h3>{hotel.name}</h3>
                      {hotel.is_demo ? (
                        <span className="demo-tag"><Sparkles size={11} /> Sample Demonstration Property</span>
                      ) : (
                        <span className="verified-tag"><ShieldCheck size={11} /> Verified Property</span>
                      )}
                    </div>
                    <p>
                      <strong>{hotel.destination}</strong> ·{" "}
                      {hotel.active ? (
                        hotel.price_basis === "unavailable" ? "Rate not listed" : `₹${hotel.nightly_rate.toLocaleString("en-IN")}/night`
                      ) : (
                        <span style={{ color: "#ef4444" }}>Archived</span>
                      )}
                      {hotel.rating && ` · Rating: ★ ${hotel.rating}`}
                    </p>
                    <p style={{ color: "#526159", fontSize: "11px", marginTop: "3px" }}>
                      <MapPin size={12} style={{ display: "inline", verticalAlign: "middle", marginRight: "4px" }} />
                      {hotel.address || <span style={{ color: "#d97706" }}>Property address not provided</span>}
                    </p>
                    {hotel.google_maps_url && (
                      <p style={{ fontSize: "11px", marginTop: "2px" }}>
                        <a href={hotel.google_maps_url} target="_blank" rel="noreferrer" style={{ color: "#0d6342", display: "inline-flex", alignItems: "center", gap: "4px" }}>
                          <ExternalLink size={11} /> Open in Google Maps
                          {hotel.latitude && hotel.longitude && <span style={{ color: "#617c6e" }}>({hotel.latitude}, {hotel.longitude})</span>}
                        </a>
                      </p>
                    )}
                    {hotel.check_in_policy && (
                      <p style={{ color: "#78877f", fontSize: "10px", marginTop: "2px" }}>
                        Check-in: {hotel.check_in_policy} | Check-out: {hotel.check_out_policy}
                      </p>
                    )}
                  </div>
                  <div className="catalog-actions">
                    {hotel.active && (
                      <button
                        type="button"
                        onClick={() => setEditingHotelId(editingHotelId === hotel.id ? null : hotel.id)}
                      >
                        {editingHotelId === hotel.id ? "Cancel edit" : "Edit hotel"}
                      </button>
                    )}
                    {hotel.active ? (
                      <button type="button" onClick={() => archive(`/admin/hotels/${hotel.id}`, "Hotel")}>Archive</button>
                    ) : (
                      <button type="button" onClick={() => setHotelActive(hotel, true)}>Restore</button>
                    )}
                  </div>
                </div>

                {/* Edit Hotel Form */}
                {editingHotelId === hotel.id && (
                  <form className="manage-form hotel-edit-form" onSubmit={event => saveHotel(event, hotel)}>
                    <div className="hotel-form-grid">
                      <label>
                        Hotel Name
                        <input name="name" required defaultValue={hotel.name} placeholder="Hotel name" />
                      </label>
                      <label>
                        Destination
                        <select name="destination_id" required defaultValue={hotel.destination_id}>
                          {destinations.filter(item => item.active).map(item => (
                            <option key={item.id} value={item.id}>{item.name}</option>
                          ))}
                        </select>
                      </label>
                      <label>
                        Address
                        <input name="address" required defaultValue={hotel.address || ""} placeholder="Full property address" />
                      </label>
                      <label>
                        Google Maps Link
                        <input name="google_maps_url" type="url" defaultValue={hotel.google_maps_url || ""} placeholder="https://maps.google.com/..." />
                      </label>
                      <label>
                        Latitude
                        <input name="latitude" type="number" step="any" defaultValue={hotel.latitude ?? ""} placeholder="e.g. 15.5432" />
                      </label>
                      <label>
                        Longitude
                        <input name="longitude" type="number" step="any" defaultValue={hotel.longitude ?? ""} placeholder="e.g. 73.7554" />
                      </label>
                      <label>
                        Image URL
                        <input name="image_url" type="url" defaultValue={hotel.image_url || ""} placeholder="Image URL" />
                      </label>
                      <label>
                        Nightly Rate (INR)
                        <input name="nightly_rate" type="number" min="0.01" step=".01" required defaultValue={hotel.nightly_rate} />
                      </label>
                      <label>
                        Rating (0–5)
                        <input name="rating" type="number" min="0" max="5" step=".1" required defaultValue={hotel.rating ?? 4.5} />
                      </label>
                      <label>
                        Property Classification
                        <select name="is_demo" defaultValue={hotel.is_demo ? "true" : "false"}>
                          <option value="false">Verified Real Property</option>
                          <option value="true">Sample Demonstration Property</option>
                        </select>
                      </label>
                      <label>
                        Rate Basis
                        <select name="price_basis" defaultValue={hotel.price_basis || "estimate"}>
                          <option value="estimate">Estimate / Demo</option>
                          <option value="verified">Verified Official Rate</option>
                          <option value="unverified">Unverified</option>
                        </select>
                      </label>
                      <label>
                        Official Source URL
                        <input name="source_url" type="url" defaultValue={hotel.source_url || ""} placeholder="HTTPS website URL" />
                      </label>
                      <label>
                        Facilities (comma-separated)
                        <input name="facilities" defaultValue={(hotel.facilities || []).join(", ")} placeholder="WiFi, Pool, etc." />
                      </label>
                      <label>
                        Check-in Policy
                        <input name="check_in_policy" defaultValue={hotel.check_in_policy || "14:00"} />
                      </label>
                      <label>
                        Check-out Policy
                        <input name="check_out_policy" defaultValue={hotel.check_out_policy || "11:00"} />
                      </label>
                    </div>
                    <label style={{ marginTop: "6px" }}>
                      Description
                      <textarea name="description" rows="2" defaultValue={hotel.description || ""} />
                    </label>
                    <div className="catalog-actions" style={{ marginTop: "10px" }}>
                      <button className="button primary">Save hotel details</button>
                      <button type="button" onClick={() => setEditingHotelId(null)}>Cancel</button>
                    </div>
                  </form>
                )}

                {/* Rooms List */}
                <div className="hotel-room-list">
                  <h4>Room Types & Inventory ({hotel.rooms.length})</h4>
                  {hotel.rooms.map(room => (
                    <div className="room-catalog-item" key={room.id}>
                      {editingRoomId === room.id ? (
                        <form className="room-edit-form" onSubmit={event => saveRoom(event, room)}>
                          <input name="name" required defaultValue={room.name} placeholder="Room type" aria-label="Room name" />
                          <input name="nightly_rate" type="number" min="0" step="1" defaultValue={room.nightly_rate || ""} placeholder="Rate/night" aria-label="Rate" />
                          <select name="price_basis" defaultValue={room.price_basis} aria-label="Rate basis">
                            <option value="estimate">Estimate</option>
                            <option value="verified">Verified</option>
                            <option value="unverified">Unverified</option>
                            <option value="unavailable">Unavailable</option>
                          </select>
                          <input name="capacity" type="number" min="1" max="20" required defaultValue={room.capacity} placeholder="Max guests" aria-label="Capacity" />
                          <input name="total_rooms" type="number" min="1" max="10000" defaultValue={room.total_rooms ?? room.available_rooms ?? 5} placeholder="Total rooms" aria-label="Total rooms" />
                          <input name="available_rooms" type="number" min="0" max="10000" defaultValue={room.available_rooms ?? ""} placeholder="Available" aria-label="Available rooms" />
                          <button className="button primary">Save</button>
                          <button type="button" onClick={() => setEditingRoomId(null)}>Cancel</button>
                        </form>
                      ) : (
                        <>
                          <span>
                            <strong>{room.name}</strong>
                            <small>
                              {room.nightly_rate > 0 ? `₹${room.nightly_rate.toLocaleString("en-IN")}/night` : "Rate not listed"} ·{" "}
                              Capacity: {room.capacity} guests ·{" "}
                              Inventory: {room.available_rooms ?? 0} available of {room.total_rooms ?? room.available_rooms ?? "?"} total ·{" "}
                              {room.active ? "Active" : "Archived"}
                            </small>
                          </span>
                          <div className="catalog-actions">
                            <button type="button" onClick={() => setEditingRoomId(room.id)}>Edit room</button>
                            {room.active ? (
                              <button type="button" onClick={() => archive(`/admin/rooms/${room.id}`, "Room type")}>Archive</button>
                            ) : (
                              <button type="button" onClick={() => restoreRoom(room)}>Restore</button>
                            )}
                          </div>
                        </>
                      )}
                    </div>
                  ))}

                  {/* Add Room Form */}
                  <form className="room-add-form" onSubmit={event => addRoom(event, hotel)}>
                    <input name="name" required placeholder="New room type (e.g. Deluxe Room)" />
                    <input name="nightly_rate" type="number" min="1" step="1" required placeholder="Nightly rate (INR)" />
                    <select name="price_basis" defaultValue="estimate">
                      <option value="estimate">Estimate / Demo</option>
                      <option value="verified">Verified</option>
                      <option value="unverified">Unverified</option>
                    </select>
                    <input name="capacity" type="number" min="1" max="20" defaultValue="2" required placeholder="Max guests" />
                    <input name="total_rooms" type="number" min="1" max="10000" defaultValue="5" required placeholder="Total rooms" />
                    <input name="available_rooms" type="number" min="0" max="10000" defaultValue="5" placeholder="Available rooms" />
                    <button className="button primary">Add room</button>
                  </form>
                </div>
              </article>
            ))
          )}
        </div>
      </section>

      {/* --- TRANSPORT MANAGEMENT SECTION --- */}
      <section id="transport" className="catalog-panel">
        <div className="section-head-wrap" style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "1rem" }}>
          <div>
            <span className="eyebrow">TRANSPORT MANAGEMENT</span>
            <h2>Intercity Transport Options (Buses & Trains)</h2>
            <p>Manage verified Bus and Train routes, fares, duration, stations, and official booking portals.</p>
          </div>
          <button
            type="button"
            className="button secondary"
            onClick={seedTransportCatalog}
            title="Populate verified and realistic schedules across India for buses and trains"
          >
            <Sparkles size={14} /> Seed Bus & Train Demo Catalog
          </button>
        </div>

        {/* Transport Metrics Overview */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "1rem", margin: "1.25rem 0" }}>
          <div style={{ background: "#f8faf9", padding: "1rem", borderRadius: "10px", border: "1px solid #e1e9e3" }}>
            <span style={{ fontSize: "0.76rem", color: "#617c6e", textTransform: "uppercase", fontWeight: 700 }}>Total Active Services</span>
            <div style={{ fontSize: "1.6rem", fontWeight: 800, color: "#163325" }}>
              {transports.filter(t => t.active).length}
            </div>
          </div>
          <div style={{ background: "#eef6ff", padding: "1rem", borderRadius: "10px", border: "1px solid #bfdbfe" }}>
            <span style={{ fontSize: "0.76rem", color: "#1d4ed8", textTransform: "uppercase", fontWeight: 700 }}>Active Buses</span>
            <div style={{ fontSize: "1.6rem", fontWeight: 800, color: "#1e40af" }}>
              {transports.filter(t => t.active && t.mode === "bus").length}
            </div>
          </div>
          <div style={{ background: "#fdf2f8", padding: "1rem", borderRadius: "10px", border: "1px solid #fbcfe8" }}>
            <span style={{ fontSize: "0.76rem", color: "#be185d", textTransform: "uppercase", fontWeight: 700 }}>Active Trains</span>
            <div style={{ fontSize: "1.6rem", fontWeight: 800, color: "#9d174d" }}>
              {transports.filter(t => t.active && t.mode === "train").length}
            </div>
          </div>
        </div>

        {/* Add Transport Option Form */}
        <div style={{ background: "#fbfdfc", border: "1px solid #dde5df", borderRadius: "14px", padding: "1.5rem", marginBottom: "2rem" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem", flexWrap: "wrap", gap: "0.5rem" }}>
            <h3 style={{ margin: 0, fontSize: "1.15rem", color: "#1b3326" }}>Add New Transport Option</h3>
            <div style={{ display: "flex", gap: "0.4rem" }}>
              <button
                type="button"
                className={`button ${addTransportCategory === "bus" ? "primary" : "secondary"}`}
                style={{ padding: "0.35rem 0.75rem", fontSize: "0.82rem" }}
                onClick={() => setAddTransportCategory("bus")}
              >
                <Bus size={13} /> Bus
              </button>
              <button
                type="button"
                className={`button ${addTransportCategory === "train" ? "primary" : "secondary"}`}
                style={{ padding: "0.35rem 0.75rem", fontSize: "0.82rem" }}
                onClick={() => setAddTransportCategory("train")}
              >
                <Train size={13} /> Train
              </button>
            </div>
          </div>

          <form className="manage-form" onSubmit={addTransport}>
            <input type="hidden" name="mode" value={addTransportCategory} />
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "1rem" }}>
              <label>
                Operator / Provider Name
                <input
                  name="operator"
                  required
                  placeholder={addTransportCategory === "bus" ? "e.g. VRL Travels, KSRTC" : "e.g. Indian Railways / IRCTC"}
                />
              </label>

              <label>
                {addTransportCategory === "train" ? "Train Name & Number" : "Service Name / Bus Title"}
                <input
                  name="service_name"
                  placeholder={addTransportCategory === "train" ? "e.g. DEMO-12626 - Kerala Express" : "e.g. Airavat Club Class Multi-Axle"}
                />
              </label>

              <label>
                {addTransportCategory === "train" ? "Train Category" : "Bus Type"}
                <input
                  name="service_type"
                  placeholder={addTransportCategory === "train" ? "e.g. Superfast Express, Vande Bharat" : "e.g. AC Sleeper (2+1), Volvo 2+2"}
                />
              </label>

              <label>
                Starting City
                <input name="origin" required placeholder="e.g. Bengaluru, Delhi, Hyderabad" />
              </label>

              <label>
                Origin Station / Terminal
                <input name="origin_station" placeholder="e.g. Majestic Bus Station, NDLS" />
              </label>

              <label>
                Boarding Point
                <input name="boarding_point" placeholder="e.g. Majestic Platform 3, Anand Rao Circle" />
              </label>

              <label>
                Destination City
                <input name="destination" required placeholder="e.g. Goa, Manali, Agra, Mysuru" />
              </label>

              <label>
                Destination Station / Terminal
                <input name="destination_station" placeholder="e.g. Panaji Kadamba Stand, AGC" />
              </label>

              <label>
                Dropping Point
                <input name="dropping_point" placeholder="e.g. Panaji Bus Stand, Madgaon Jn" />
              </label>

              <label>
                Departure Time
                <input name="departure_time" required placeholder="e.g. 20:30, 06:00 AM, Flexible" />
              </label>

              <label>
                Arrival Time
                <input name="arrival_time" required placeholder="e.g. 07:00, 14:15, Est. 3h 30m" />
              </label>

              <label>
                Duration
                <input name="duration" placeholder="e.g. 10h 30m, 3h 15m" />
              </label>

              <label>
                Estimated Distance
                <input name="distance_km" placeholder="e.g. 560 km, 145 km" />
              </label>

              <label>
                Estimated Fare / Ticket Price (INR)
                <input name="ticket_price" type="number" min="0" step="1" required placeholder="e.g. 1250" />
              </label>

              <label>
                Pricing Unit
                <select name="pricing_unit" defaultValue="per_person">
                  <option value="per_person">Per Person / Seat</option>
                  <option value="per_vehicle">Per Vehicle</option>
                </select>
              </label>

              {addTransportCategory === "train" && (
                <label>
                  Available Classes
                  <input name="available_classes" placeholder="e.g. 1A, 2A, 3A, SL, CC, EC" />
                </label>
              )}

              {addTransportCategory === "train" && (
                <label>
                  Class Fares (JSON Optional)
                  <input name="class_fares" placeholder='e.g. {"SL": 450, "3A": 1200, "2A": 1800}' />
                </label>
              )}

              <label>
                Available Seats (Demo)
                <input name="available_seats" type="number" min="0" max="10000" placeholder="e.g. 32" />
              </label>

              <label>
                Booking Status
                <select name="booking_status" defaultValue="available">
                  <option value="available">Available</option>
                  <option value="filling_fast">Filling Fast</option>
                  <option value="waitlist">Waitlist</option>
                  <option value="rac">RAC</option>
                </select>
              </label>

              <label>
                Contact / Helpline Number
                <input name="contact_number" placeholder="e.g. +91 98765 01001 or 139" />
              </label>

              <label>
                Official Booking Link
                <input name="booking_url" type="url" placeholder="https://www.irctc.co.in, https://www.redbus.in" />
              </label>

              <label>
                Linked Destination (Optional)
                <select name="destination_id" defaultValue="">
                  <option value="">None / Regional</option>
                  {destinations.filter(d => d.active).map(d => (
                    <option key={d.id} value={d.id}>{d.name} ({d.state})</option>
                  ))}
                </select>
              </label>

              <label>
                Price Basis
                <select name="price_basis" defaultValue="verified">
                  <option value="verified">Verified Fare</option>
                  <option value="estimate">Estimate</option>
                  <option value="sample">Sample Catalog</option>
                </select>
              </label>

              <label style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginTop: "1.5rem" }}>
                <input type="checkbox" name="availability_verified" defaultChecked />
                Verified Schedule & Fare
              </label>
            </div>

            <div style={{ marginTop: "1.25rem" }}>
              <button className="button primary">Add Transport Option</button>
            </div>
          </form>
        </div>

        {/* Filter and Search Transport List */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "0.75rem", marginBottom: "1rem" }}>
          <div style={{ display: "flex", gap: "0.4rem", flexWrap: "wrap" }}>
            <button
              type="button"
              className={`button ${transportCategoryFilter === "all" ? "primary" : "secondary"}`}
              style={{ padding: "0.35rem 0.75rem", fontSize: "0.82rem" }}
              onClick={() => setTransportCategoryFilter("all")}
            >
              All ({transports.length})
            </button>
            <button
              type="button"
              className={`button ${transportCategoryFilter === "bus" ? "primary" : "secondary"}`}
              style={{ padding: "0.35rem 0.75rem", fontSize: "0.82rem" }}
              onClick={() => setTransportCategoryFilter("bus")}
            >
              <Bus size={13} /> Buses ({transports.filter(t => t.mode === "bus").length})
            </button>
            <button
              type="button"
              className={`button ${transportCategoryFilter === "train" ? "primary" : "secondary"}`}
              style={{ padding: "0.35rem 0.75rem", fontSize: "0.82rem" }}
              onClick={() => setTransportCategoryFilter("train")}
            >
              <Train size={13} /> Trains ({transports.filter(t => t.mode === "train").length})
            </button>
          </div>

          <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
            <select
              value={transportStatusFilter}
              onChange={e => setTransportStatusFilter(e.target.value)}
              style={{ padding: "0.4rem 0.6rem", borderRadius: "6px", border: "1px solid #c7d6cc", fontSize: "0.82rem" }}
            >
              <option value="all">All Statuses</option>
              <option value="active">Active Only</option>
              <option value="archived">Archived Only</option>
            </select>
            <input
              type="text"
              placeholder="Search routes or operators…"
              value={transportSearch}
              onChange={e => setTransportSearch(e.target.value)}
              style={{ padding: "0.4rem 0.75rem", borderRadius: "6px", border: "1px solid #c7d6cc", fontSize: "0.85rem", width: "220px" }}
            />
          </div>
        </div>

        {/* Transport List */}
        <div className="catalog-list">
          {transports
            .filter(t => {
              if (transportCategoryFilter !== "all" && t.mode !== transportCategoryFilter) return false;
              if (transportStatusFilter === "active" && !t.active) return false;
              if (transportStatusFilter === "archived" && t.active) return false;
              if (transportSearch.trim()) {
                const q = transportSearch.toLowerCase();
                const matchOp = (t.operator || "").toLowerCase().includes(q);
                const matchName = (t.service_name || "").toLowerCase().includes(q);
                const matchOrig = (t.origin || "").toLowerCase().includes(q);
                const matchDest = (t.destination || "").toLowerCase().includes(q);
                if (!matchOp && !matchName && !matchOrig && !matchDest) return false;
              }
              return true;
            })
            .map(t => (
              <article className="hotel-catalog-card" key={t.id} style={{ borderLeft: t.active ? "4px solid #1e4a38" : "4px solid #94a3b8" }}>
                <div className="hotel-catalog-heading">
                  <div>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
                      <span style={{
                        padding: "2px 8px", borderRadius: "4px", fontSize: "11px", fontWeight: 700, textTransform: "uppercase",
                        background: t.mode === "bus" ? "#eef6ff" : "#fdf2f8",
                        color: t.mode === "bus" ? "#1d4ed8" : "#be185d"
                      }}>
                        {t.mode}
                      </span>
                      <h3 style={{ margin: 0 }}>{t.operator} {t.service_name ? `· ${t.service_name}` : ""}</h3>
                      {t.availability_verified || t.price_basis === "verified" ? (
                        <span className="verified-tag"><ShieldCheck size={11} /> Verified Schedule</span>
                      ) : (
                        <span className="demo-tag"><Sparkles size={11} /> Estimated Schedule</span>
                      )}
                      {t.booking_status && (
                        <span style={{
                          padding: "2px 7px", borderRadius: "4px", fontSize: "11px", fontWeight: 600,
                          background: t.booking_status === "available" ? "#dcfce7" : "#fef3c7",
                          color: t.booking_status === "available" ? "#166534" : "#92400e"
                        }}>
                          {t.booking_status === "available" ? "Demo Available" : t.booking_status}
                        </span>
                      )}
                    </div>
                    <p style={{ marginTop: "4px" }}>
                      <strong>{t.origin} ({t.origin_station || "Any"}) ➔ {t.destination} ({t.destination_station || "Any"})</strong> ·{" "}
                      {t.departure_time} to {t.arrival_time} {t.duration ? `(${t.duration})` : ""} ·{" "}
                      <strong>₹{Number(t.ticket_price || 0).toLocaleString("en-IN")}</strong> {t.pricing_unit === "per_vehicle" ? "/ vehicle" : "/ person"}
                      {!t.active && <span style={{ color: "#ef4444", marginLeft: "6px" }}>· Archived</span>}
                    </p>
                    <div style={{ display: "flex", gap: "12px", fontSize: "11px", color: "#617c6e", marginTop: "3px", flexWrap: "wrap" }}>
                      {t.boarding_point && <span>Boarding: {t.boarding_point}</span>}
                      {t.dropping_point && <span>Dropping: {t.dropping_point}</span>}
                      {t.service_type && <span>Type: {t.service_type}</span>}
                      {t.distance_km && <span>Distance: {t.distance_km}</span>}
                      {t.available_classes && <span>Classes: {t.available_classes}</span>}
                      {t.available_seats != null && <span>Demo Seats: {t.available_seats}</span>}
                      {t.contact_number && <span><Phone size={10} style={{ display: "inline" }} /> {t.contact_number}</span>}
                      {t.booking_url && (
                        <a href={t.booking_url} target="_blank" rel="noopener noreferrer" style={{ color: "#0d6342", display: "inline-flex", alignItems: "center", gap: "3px" }}>
                          Official Link <ExternalLink size={10} />
                        </a>
                      )}
                    </div>
                  </div>

                  <div className="catalog-actions">
                    <button
                      type="button"
                      onClick={() => setEditingTransportId(editingTransportId === t.id ? null : t.id)}
                    >
                      {editingTransportId === t.id ? "Cancel edit" : "Edit transport"}
                    </button>
                    {t.active ? (
                      <button type="button" onClick={() => archiveTransport(t)}>Archive</button>
                    ) : (
                      <button type="button" onClick={() => restoreTransport(t)}>Restore</button>
                    )}
                  </div>
                </div>

                {/* Inline Edit Form */}
                {editingTransportId === t.id && (
                  <form className="manage-form hotel-edit-form" onSubmit={event => saveTransport(event, t)}>
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "0.85rem" }}>
                      <label>
                        Category
                        <select name="mode" defaultValue={t.mode}>
                          <option value="bus">Bus</option>
                          <option value="train">Train</option>
                        </select>
                      </label>
                      <label>
                        Operator Name
                        <input name="operator" required defaultValue={t.operator} />
                      </label>
                      <label>
                        Service Name
                        <input name="service_name" defaultValue={t.service_name || ""} />
                      </label>
                      <label>
                        Service Type
                        <input name="service_type" defaultValue={t.service_type || ""} />
                      </label>
                      <label>
                        Origin
                        <input name="origin" required defaultValue={t.origin} />
                      </label>
                      <label>
                        Origin Station
                        <input name="origin_station" defaultValue={t.origin_station || ""} />
                      </label>
                      <label>
                        Boarding Point
                        <input name="boarding_point" defaultValue={t.boarding_point || ""} />
                      </label>
                      <label>
                        Destination
                        <input name="destination" required defaultValue={t.destination} />
                      </label>
                      <label>
                        Destination Station
                        <input name="destination_station" defaultValue={t.destination_station || ""} />
                      </label>
                      <label>
                        Dropping Point
                        <input name="dropping_point" defaultValue={t.dropping_point || ""} />
                      </label>
                      <label>
                        Departure Time
                        <input name="departure_time" required defaultValue={t.departure_time} />
                      </label>
                      <label>
                        Arrival Time
                        <input name="arrival_time" required defaultValue={t.arrival_time} />
                      </label>
                      <label>
                        Duration
                        <input name="duration" defaultValue={t.duration || ""} />
                      </label>
                      <label>
                        Distance
                        <input name="distance_km" defaultValue={t.distance_km || ""} />
                      </label>
                      <label>
                        Ticket Price / Fare (INR)
                        <input name="ticket_price" type="number" min="0" step="1" required defaultValue={t.ticket_price} />
                      </label>
                      <label>
                        Pricing Unit
                        <select name="pricing_unit" defaultValue={t.pricing_unit || "per_person"}>
                          <option value="per_person">Per Person</option>
                          <option value="per_vehicle">Per Vehicle</option>
                        </select>
                      </label>
                      <label>
                        Booking Status
                        <select name="booking_status" defaultValue={t.booking_status || "available"}>
                          <option value="available">Available</option>
                          <option value="filling_fast">Filling Fast</option>
                          <option value="waitlist">Waitlist</option>
                          <option value="rac">RAC</option>
                        </select>
                      </label>
                      <label>
                        Classes (Train)
                        <input name="available_classes" defaultValue={t.available_classes || ""} />
                      </label>
                      <label>
                        Available Seats (Demo)
                        <input name="available_seats" type="number" min="0" defaultValue={t.available_seats != null ? t.available_seats : ""} />
                      </label>
                      <label>
                        Helpline / Phone
                        <input name="contact_number" defaultValue={t.contact_number || ""} />
                      </label>
                      <label>
                        Booking URL
                        <input name="booking_url" type="url" defaultValue={t.booking_url || t.source_url || ""} />
                      </label>
                      <label>
                        Price Basis
                        <select name="price_basis" defaultValue={t.price_basis || "verified"}>
                          <option value="verified">Verified</option>
                          <option value="estimate">Estimate</option>
                          <option value="sample">Sample</option>
                        </select>
                      </label>
                    </div>
                    <div style={{ marginTop: "1rem", display: "flex", gap: "0.5rem" }}>
                      <button className="button primary">Save changes</button>
                      <button type="button" onClick={() => setEditingTransportId(null)}>Cancel</button>
                    </div>
                  </form>
                )}
              </article>
            ))}
        </div>
      </section>
    </AdminShell>
  );
}

