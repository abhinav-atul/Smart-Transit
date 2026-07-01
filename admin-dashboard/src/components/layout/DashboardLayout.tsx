"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import Cookies from "js-cookie";
import Link from "next/link";
import { LayoutDashboard, Map, LogOut, Bus } from "lucide-react";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    const token = Cookies.get("token");
    if (!token && !pathname.includes("/login")) {
      router.push("/login");
    }
  }, [router, pathname]);

  if (!mounted || pathname.includes("/login")) {
    return <>{children}</>;
  }

  const handleLogout = () => {
    Cookies.remove("token");
    router.push("/login");
  };

  const navItems = [
    { name: "Dashboard", href: "/", icon: LayoutDashboard },
    { name: "Routes", href: "/routes", icon: Map },
  ];

  return (
    <div className="flex h-screen bg-background">
      {/* Sidebar */}
      <aside className="w-64 border-r border-border bg-card flex flex-col">
        <div className="h-16 flex items-center px-6 border-b border-border">
          <Bus className="w-6 h-6 text-primary mr-3" />
          <span className="font-bold text-lg">Smart Transit</span>
        </div>
        <nav className="flex-1 p-4 space-y-1">
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            const Icon = item.icon;
            return (
              <Link
                key={item.name}
                href={item.href}
                className={`flex items-center px-4 py-3 rounded-lg transition-colors ${
                  isActive ? "bg-primary text-primary-foreground" : "text-gray-400 hover:bg-border hover:text-white"
                }`}
              >
                <Icon className="w-5 h-5 mr-3" />
                {item.name}
              </Link>
            );
          })}
        </nav>
        <div className="p-4 border-t border-border">
          <button
            onClick={handleLogout}
            className="flex items-center w-full px-4 py-3 text-gray-400 hover:bg-border hover:text-white rounded-lg transition-colors"
          >
            <LogOut className="w-5 h-5 mr-3" />
            Logout
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-auto p-8">
        {children}
      </main>
    </div>
  );
}
