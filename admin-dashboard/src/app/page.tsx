"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { Bus, Activity, Clock, Navigation } from "lucide-react";

export default function Dashboard() {
  const [summary, setSummary] = useState<any>(null);
  const [hourlyData, setHourlyData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [summaryRes, hourlyRes] = await Promise.all([
          api.get("/analytics/fleet/summary"),
          api.get("/analytics/fleet/hourly"),
        ]);
        setSummary(summaryRes.data);
        setHourlyData(
          hourlyRes.data.map((d: any) => ({
            time: new Date(d.hour).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
            buses: d.active_buses,
            speed: d.avg_speed,
          }))
        );
      } catch (err) {
        console.error("Failed to fetch analytics", err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  if (loading) {
    return <div className="flex h-full items-center justify-center">Loading dashboard...</div>;
  }

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold tracking-tight">Fleet Overview</h1>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Active Buses (24h)"
          value={summary?.unique_buses || 0}
          icon={Bus}
          description="Unique vehicles reporting"
        />
        <StatCard
          title="Total Telemetry"
          value={summary?.total_pings?.toLocaleString() || 0}
          icon={Activity}
          description="GPS pings processed"
        />
        <StatCard
          title="Avg Speed"
          value={`${summary?.avg_speed_kmh || 0} km/h`}
          icon={Navigation}
          description="Fleet average"
        />
        <StatCard
          title="Latest Ping"
          value={summary?.latest_ping ? new Date(summary.latest_ping).toLocaleTimeString() : "-"}
          icon={Clock}
          description="Last updated"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="glass-panel p-6 rounded-xl">
          <h2 className="text-lg font-semibold mb-4">Active Buses (Hourly)</h2>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={hourlyData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="time" stroke="#94a3b8" />
                <YAxis stroke="#94a3b8" />
                <Tooltip
                  contentStyle={{ backgroundColor: "#0f172a", borderColor: "#1e293b", color: "#f8fafc" }}
                />
                <Line type="monotone" dataKey="buses" stroke="#3b82f6" strokeWidth={3} dot={{ r: 4 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="glass-panel p-6 rounded-xl">
          <h2 className="text-lg font-semibold mb-4">Average Speed (Hourly)</h2>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={hourlyData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="time" stroke="#94a3b8" />
                <YAxis stroke="#94a3b8" />
                <Tooltip
                  contentStyle={{ backgroundColor: "#0f172a", borderColor: "#1e293b", color: "#f8fafc" }}
                />
                <Line type="monotone" dataKey="speed" stroke="#10b981" strokeWidth={3} dot={{ r: 4 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}

function StatCard({ title, value, icon: Icon, description }: { title: string; value: string | number; icon: any; description: string }) {
  return (
    <div className="glass-panel p-6 rounded-xl flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-gray-400">{title}</h3>
        <Icon className="w-5 h-5 text-gray-500" />
      </div>
      <div className="text-3xl font-bold text-white mb-1">{value}</div>
      <p className="text-xs text-gray-500">{description}</p>
    </div>
  );
}
