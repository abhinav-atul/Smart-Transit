"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Plus, Trash2, MapPin, Upload, CheckCircle, Loader2, Database } from "lucide-react";

type Route = { route_id: string; route_name: string };
type GtfsStatus = { gtfs_routes: number; gtfs_stops: number };

export default function RoutesPage() {
  const [routes, setRoutes] = useState<Route[]>([]);
  const [loading, setLoading] = useState(true);
  const [gtfsStatus, setGtfsStatus] = useState<GtfsStatus | null>(null);
  const [gtfsLoading, setGtfsLoading] = useState(false);
  const [gtfsSuccess, setGtfsSuccess] = useState(false);

  // Create Route Form State
  const [showForm, setShowForm] = useState(false);
  const [routeId, setRouteId] = useState("");
  const [routeName, setRouteName] = useState("");
  const [stops, setStops] = useState([{ stop_name: "", latitude: "", longitude: "" }]);

  useEffect(() => {
    fetchRoutes();
    fetchGtfsStatus();
  }, []);

  const fetchRoutes = async () => {
    try {
      const res = await api.get("/admin/routes");
      setRoutes(res.data);
    } catch (err) {
      console.error("Failed to fetch routes", err);
    } finally {
      setLoading(false);
    }
  };

  const fetchGtfsStatus = async () => {
    try {
      const res = await api.get("/admin/gtfs/status");
      setGtfsStatus(res.data);
    } catch (err) {
      console.error("Failed to fetch GTFS status", err);
    }
  };

  const handleGtfsDemo = async () => {
    setGtfsLoading(true);
    setGtfsSuccess(false);
    try {
      await api.post("/admin/gtfs/demo");
      setGtfsSuccess(true);
      await fetchRoutes();
      await fetchGtfsStatus();
      setTimeout(() => setGtfsSuccess(false), 4000);
    } catch (err) {
      console.error("GTFS ingestion failed", err);
      alert("GTFS ingestion failed. Check that the backend is running.");
    } finally {
      setGtfsLoading(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Are you sure you want to delete this route?")) return;
    try {
      await api.delete(`/admin/routes/${id}`);
      fetchRoutes();
    } catch (err) {
      console.error("Failed to delete route", err);
      alert("Error deleting route.");
    }
  };

  const handleAddStop = () => {
    setStops([...stops, { stop_name: "", latitude: "", longitude: "" }]);
  };

  const handleStopChange = (index: number, field: string, value: string) => {
    const newStops = [...stops];
    newStops[index] = { ...newStops[index], [field]: value };
    setStops(newStops);
  };

  const handleCreateRoute = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const payload = {
        route_id: routeId,
        route_name: routeName,
        stops: stops.map((s) => ({
          stop_name: s.stop_name,
          latitude: parseFloat(s.latitude),
          longitude: parseFloat(s.longitude),
        })),
      };
      await api.post("/admin/routes", payload);
      setShowForm(false);
      setRouteId("");
      setRouteName("");
      setStops([{ stop_name: "", latitude: "", longitude: "" }]);
      fetchRoutes();
    } catch (err) {
      console.error("Failed to create route", err);
      alert("Error creating route. Please check the inputs.");
    }
  };

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <Loader2 className="w-8 h-8 animate-spin text-primary" />
    </div>
  );

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold tracking-tight">Route Management</h1>
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex items-center px-4 py-2 bg-primary text-white rounded-lg hover:bg-blue-600 transition-colors"
        >
          <Plus className="w-4 h-4 mr-2" />
          {showForm ? "Cancel" : "New Route"}
        </button>
      </div>

      {/* GTFS Pipeline Panel */}
      <div className="glass-panel p-6 rounded-xl">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-violet-500/20">
              <Database className="w-5 h-5 text-violet-400" />
            </div>
            <div>
              <h2 className="font-bold text-lg">GTFS Data Pipeline</h2>
              <p className="text-sm text-gray-400 mt-0.5">
                Import routes from the international GTFS transit standard used by every major city.
              </p>
            </div>
          </div>
          {gtfsStatus && (
            <div className="text-right text-sm text-gray-400">
              <p><span className="text-white font-bold">{gtfsStatus.gtfs_routes}</span> GTFS routes</p>
              <p><span className="text-white font-bold">{gtfsStatus.gtfs_stops}</span> GTFS stops</p>
            </div>
          )}
        </div>

        <div className="mt-4 pt-4 border-t border-border flex items-center gap-4">
          <button
            onClick={handleGtfsDemo}
            disabled={gtfsLoading}
            className="flex items-center px-4 py-2 bg-violet-600 hover:bg-violet-700 disabled:opacity-50 text-white rounded-lg transition-colors text-sm font-medium"
          >
            {gtfsLoading ? (
              <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Ingesting...</>
            ) : gtfsSuccess ? (
              <><CheckCircle className="w-4 h-4 mr-2 text-green-300" /> Ingested!</>
            ) : (
              <><Upload className="w-4 h-4 mr-2" /> Run Demo Feed</>
            )}
          </button>
          <p className="text-xs text-gray-500">
            Loads a sample Lahore transit network (3 routes, 13 stops) to demonstrate real-world GTFS compatibility.
            In production, point the CLI at any city's official GTFS zip file.
          </p>
        </div>
      </div>

      {/* Create Route Form */}
      {showForm && (
        <div className="glass-panel p-6 rounded-xl">
          <h2 className="text-xl font-bold mb-4">Create / Update Route</h2>
          <form onSubmit={handleCreateRoute} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-gray-400 mb-1">Route ID (e.g. RT-101)</label>
                <input
                  required
                  value={routeId}
                  onChange={(e) => setRouteId(e.target.value)}
                  className="w-full bg-input border border-border rounded-md px-3 py-2 text-white"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">Route Name</label>
                <input
                  required
                  value={routeName}
                  onChange={(e) => setRouteName(e.target.value)}
                  className="w-full bg-input border border-border rounded-md px-3 py-2 text-white"
                />
              </div>
            </div>

            <div className="pt-4 border-t border-border">
              <div className="flex justify-between items-center mb-2">
                <h3 className="font-semibold text-lg">Stops Sequence</h3>
                <button type="button" onClick={handleAddStop} className="text-sm text-primary hover:underline">
                  + Add Stop
                </button>
              </div>
              {stops.map((stop, i) => (
                <div key={i} className="flex space-x-2 mb-2 items-center">
                  <div className="w-8 h-8 rounded-full bg-border flex items-center justify-center text-xs font-bold flex-shrink-0">
                    {i + 1}
                  </div>
                  <input
                    placeholder="Stop Name"
                    required
                    value={stop.stop_name}
                    onChange={(e) => handleStopChange(i, "stop_name", e.target.value)}
                    className="flex-1 bg-input border border-border rounded-md px-3 py-2 text-sm text-white"
                  />
                  <input
                    placeholder="Latitude"
                    type="number"
                    step="any"
                    required
                    value={stop.latitude}
                    onChange={(e) => handleStopChange(i, "latitude", e.target.value)}
                    className="w-32 bg-input border border-border rounded-md px-3 py-2 text-sm text-white"
                  />
                  <input
                    placeholder="Longitude"
                    type="number"
                    step="any"
                    required
                    value={stop.longitude}
                    onChange={(e) => handleStopChange(i, "longitude", e.target.value)}
                    className="w-32 bg-input border border-border rounded-md px-3 py-2 text-sm text-white"
                  />
                </div>
              ))}
            </div>

            <div className="flex justify-end pt-4">
              <button type="submit" className="px-6 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors">
                Save Route
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Routes Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
        {routes.map((route) => (
          <div key={route.route_id} className="glass-panel p-6 rounded-xl flex flex-col justify-between">
            <div>
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h3 className="text-xl font-bold text-white">{route.route_name}</h3>
                  <span className={`text-xs font-mono px-2 py-1 rounded mt-1 inline-block ${
                    route.route_id.startsWith("GTFS-")
                      ? "bg-violet-500/20 text-violet-300"
                      : "bg-border text-gray-300"
                  }`}>
                    {route.route_id.startsWith("GTFS-") ? "🌐 " : ""}{route.route_id}
                  </span>
                </div>
                <div className="bg-primary/20 p-2 rounded-full">
                  <MapPin className="w-5 h-5 text-primary" />
                </div>
              </div>
            </div>

            <div className="mt-6 pt-4 border-t border-border flex justify-end">
              <button
                onClick={() => handleDelete(route.route_id)}
                className="text-red-400 hover:text-red-300 flex items-center text-sm transition-colors"
              >
                <Trash2 className="w-4 h-4 mr-1" /> Delete
              </button>
            </div>
          </div>
        ))}
      </div>

      {routes.length === 0 && !showForm && (
        <div className="text-center py-12 text-gray-500 glass-panel rounded-xl">
          No routes configured. Create one manually or run the GTFS demo feed above.
        </div>
      )}
    </div>
  );
}
