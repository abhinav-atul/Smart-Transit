"""
GTFS (General Transit Feed Specification) Ingestion Pipeline
============================================================
Parses standard GTFS zip files from transit authorities and loads them
into the Smart-Transit database, replacing or augmenting existing routes.

GTFS is the international standard for public transit data. Every major
city (Delhi Metro, London TfL, NYC MTA, etc.) publishes GTFS feeds.

Usage:
    # Download a GTFS zip and run:
    python scripts/gtfs_ingest.py --file /path/to/gtfs.zip

    # Or point to a directory of already-extracted GTFS txt files:
    python scripts/gtfs_ingest.py --dir /path/to/gtfs_folder/

    # Dry run (parse only, no DB writes):
    python scripts/gtfs_ingest.py --file /path/to/gtfs.zip --dry-run

Run from project root: python scripts/gtfs_ingest.py --help
"""

import argparse
import asyncio
import csv
import io
import logging
import os
import sys
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Optional

import asyncpg
from dotenv import load_dotenv

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("gtfs_ingest")

# ── Config ────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

DB_DSN = os.getenv(
    "DATABASE_URL", "postgresql://user:secretpass123@localhost:5433/transit_db"
)

# GTFS files we need (others like calendar.txt are optional for our use case)
REQUIRED_FILES = {"routes.txt", "stops.txt", "stop_times.txt", "trips.txt"}
OPTIONAL_FILES = {"shapes.txt", "agency.txt"}


# ── GTFS Reader ───────────────────────────────────────────────────────────────

def _read_csv(content: bytes) -> list[dict]:
    """Parse CSV bytes into a list of dicts, stripping BOM."""
    text = content.decode("utf-8-sig")
    return list(csv.DictReader(io.StringIO(text)))


def load_gtfs_from_zip(zip_path: Path) -> dict[str, list[dict]]:
    """Extract and parse all relevant GTFS files from a zip archive."""
    logger.info("Loading GTFS from zip: %s", zip_path)
    gtfs = {}
    with zipfile.ZipFile(zip_path, "r") as zf:
        names = set(zf.namelist())
        available = REQUIRED_FILES | OPTIONAL_FILES
        for fname in available:
            if fname in names:
                gtfs[fname] = _read_csv(zf.read(fname))
                logger.info("  Loaded %-20s (%d records)", fname, len(gtfs[fname]))
            elif fname in REQUIRED_FILES:
                logger.error("Required file missing from zip: %s", fname)
                sys.exit(1)
    return gtfs


def load_gtfs_from_dir(dir_path: Path) -> dict[str, list[dict]]:
    """Parse GTFS txt files from an already-extracted directory."""
    logger.info("Loading GTFS from directory: %s", dir_path)
    gtfs = {}
    available = REQUIRED_FILES | OPTIONAL_FILES
    for fname in available:
        fpath = dir_path / fname
        if fpath.exists():
            gtfs[fname] = _read_csv(fpath.read_bytes())
            logger.info("  Loaded %-20s (%d records)", fname, len(gtfs[fname]))
        elif fname in REQUIRED_FILES:
            logger.error("Required file missing: %s", fpath)
            sys.exit(1)
    return gtfs


# ── GTFS Transformer ──────────────────────────────────────────────────────────

def transform_gtfs(gtfs: dict[str, list[dict]]) -> list[dict]:
    """
    Convert raw GTFS tables into our internal route format:
    [
      {
        "route_id": "RT-101",
        "route_name": "Route 101 - City Center",
        "stops": [
          {"stop_id": "S1", "stop_name": "Central Station", "lat": 31.5, "lng": 74.3, "sequence": 0},
          ...
        ]
      },
      ...
    ]
    """
    logger.info("Transforming GTFS data...")

    # Build stop lookup: stop_id -> {name, lat, lng}
    stops_lookup: dict[str, dict] = {}
    for s in gtfs["stops.txt"]:
        stops_lookup[s["stop_id"]] = {
            "stop_name": s.get("stop_name", "Unknown Stop"),
            "lat": float(s["stop_lat"]),
            "lng": float(s["stop_lon"]),
        }

    # Build trips lookup: trip_id -> route_id
    trips_lookup: dict[str, str] = {}
    for t in gtfs["trips.txt"]:
        trips_lookup[t["trip_id"]] = t["route_id"]

    # Build route name lookup: route_id -> display name
    route_names: dict[str, str] = {}
    for r in gtfs["routes.txt"]:
        short = r.get("route_short_name", "").strip()
        long = r.get("route_long_name", "").strip()
        name = f"{short} - {long}" if short and long else (long or short or r["route_id"])
        route_names[r["route_id"]] = name

    # Build stop_times: route_id -> trip_id -> [(sequence, stop_id)]
    # We pick ONE representative trip per route (the first trip_id found)
    route_to_trip: dict[str, str] = {}
    trip_stops: dict[str, list[tuple[int, str]]] = defaultdict(list)

    for st in gtfs["stop_times.txt"]:
        trip_id = st["trip_id"]
        route_id = trips_lookup.get(trip_id)
        if not route_id:
            continue

        # Only keep first trip per route to avoid duplicates
        if route_id not in route_to_trip:
            route_to_trip[route_id] = trip_id

        if trip_id == route_to_trip.get(route_id):
            try:
                seq = int(st["stop_sequence"])
            except ValueError:
                seq = 0
            trip_stops[trip_id].append((seq, st["stop_id"]))

    # Build final route list
    routes = []
    for route_id, trip_id in route_to_trip.items():
        sorted_stops = sorted(trip_stops[trip_id], key=lambda x: x[0])
        stops = []
        for seq, stop_id in sorted_stops:
            stop_info = stops_lookup.get(stop_id)
            if stop_info:
                stops.append({
                    "stop_id": stop_id,
                    "stop_name": stop_info["stop_name"],
                    "lat": stop_info["lat"],
                    "lng": stop_info["lng"],
                    "sequence": seq,
                })

        if len(stops) < 2:
            logger.warning("Skipping route %s — fewer than 2 valid stops", route_id)
            continue

        routes.append({
            "route_id": route_id,
            "route_name": route_names.get(route_id, route_id),
            "stops": stops,
        })

    logger.info("Transformed %d routes (from %d GTFS routes)", len(routes), len(gtfs["routes.txt"]))
    return routes


# ── Database Writer ───────────────────────────────────────────────────────────

async def write_to_database(routes: list[dict], dry_run: bool = False) -> None:
    """Upsert all routes and stops into the database."""
    if dry_run:
        logger.info("[DRY RUN] Would write %d routes to database:", len(routes))
        for r in routes:
            logger.info("  Route %-20s | %s | %d stops", r["route_id"], r["route_name"], len(r["stops"]))
        return

    logger.info("Connecting to database...")
    try:
        conn = await asyncpg.connect(DB_DSN)
    except Exception as e:
        logger.error("Connection failed: %s", e)
        logger.error("Ensure Docker is running: docker compose up -d")
        sys.exit(1)

    logger.info("Writing %d routes to database...", len(routes))
    written = 0
    skipped = 0

    try:
        async with conn.transaction():
            for route in routes:
                route_id = route["route_id"]
                route_name = route["route_name"]

                # Upsert route
                await conn.execute("""
                    INSERT INTO routes (route_id, route_name)
                    VALUES ($1, $2)
                    ON CONFLICT (route_id) DO UPDATE
                    SET route_name = EXCLUDED.route_name
                """, route_id, route_name)

                # Replace stops for this route (clean slate per route)
                await conn.execute("DELETE FROM stops WHERE route_id = $1", route_id)

                for stop in route["stops"]:
                    await conn.execute("""
                        INSERT INTO stops (route_id, stop_name, latitude, longitude, stop_sequence)
                        VALUES ($1, $2, $3, $4, $5)
                    """, route_id, stop["stop_name"], stop["lat"], stop["lng"], stop["sequence"])

                logger.info("  ✓ %-20s | %s (%d stops)", route_id, route_name, len(route["stops"]))
                written += 1

        logger.info("")
        logger.info("═══════════════════════════════════════════")
        logger.info(" GTFS Ingestion Complete")
        logger.info("  Routes written : %d", written)
        logger.info("  Routes skipped : %d", skipped)
        logger.info("═══════════════════════════════════════════")

    except Exception as e:
        logger.error("Database write failed: %s", e)
        raise
    finally:
        await conn.close()


# ── Summary Reporter ──────────────────────────────────────────────────────────

def print_summary(routes: list[dict]) -> None:
    """Print a human-readable preview of what will be ingested."""
    total_stops = sum(len(r["stops"]) for r in routes)
    print("\n" + "═" * 60)
    print(f"  GTFS FEED SUMMARY")
    print("═" * 60)
    print(f"  Routes found : {len(routes)}")
    print(f"  Total stops  : {total_stops}")
    print("─" * 60)
    for r in routes[:10]:  # Preview first 10
        print(f"  {r['route_id']:<15} {r['route_name']:<35} ({len(r['stops'])} stops)")
    if len(routes) > 10:
        print(f"  ... and {len(routes) - 10} more routes")
    print("═" * 60 + "\n")


# ── CLI Entry Point ───────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Smart-Transit GTFS Ingestion Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/gtfs_ingest.py --file ~/Downloads/city_gtfs.zip
  python scripts/gtfs_ingest.py --dir ~/Downloads/gtfs_extracted/
  python scripts/gtfs_ingest.py --file gtfs.zip --dry-run
  python scripts/gtfs_ingest.py --demo          # Generate sample GTFS and ingest
        """,
    )
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--file", type=Path, help="Path to GTFS .zip file")
    source.add_argument("--dir", type=Path, help="Path to extracted GTFS directory")
    source.add_argument("--demo", action="store_true", help="Generate and ingest a demo GTFS feed")
    parser.add_argument("--dry-run", action="store_true", help="Parse only, do not write to database")
    args = parser.parse_args()

    if args.demo:
        logger.info("Generating demo GTFS feed...")
        gtfs = generate_demo_gtfs()
    elif args.file:
        if not args.file.exists():
            logger.error("File not found: %s", args.file)
            sys.exit(1)
        gtfs = load_gtfs_from_zip(args.file)
    elif args.dir:
        if not args.dir.is_dir():
            logger.error("Directory not found: %s", args.dir)
            sys.exit(1)
        gtfs = load_gtfs_from_dir(args.dir)
    else:
        parser.print_help()
        sys.exit(0)

    routes = transform_gtfs(gtfs)
    print_summary(routes)
    asyncio.run(write_to_database(routes, dry_run=args.dry_run))


# ── Demo GTFS Generator ───────────────────────────────────────────────────────

def generate_demo_gtfs() -> dict[str, list[dict]]:
    """
    Generate a realistic GTFS demo feed for Lahore, Pakistan.
    Mirrors the structure of a real GTFS feed to validate the pipeline.
    """
    logger.info("Generating demo GTFS data (Lahore transit network)...")

    agencies = [{"agency_id": "LTC", "agency_name": "Lahore Transport Company", "agency_url": "https://ltc.gov.pk", "agency_timezone": "Asia/Karachi"}]

    routes_raw = [
        {"route_id": "GTFS-RT1", "agency_id": "LTC", "route_short_name": "G1", "route_long_name": "Mall Road Express", "route_type": "3"},
        {"route_id": "GTFS-RT2", "agency_id": "LTC", "route_short_name": "G2", "route_long_name": "Gulberg Circular", "route_type": "3"},
        {"route_id": "GTFS-RT3", "agency_id": "LTC", "route_short_name": "G3", "route_long_name": "Airport Link", "route_type": "3"},
    ]

    stops_raw = [
        # Route G1 stops
        {"stop_id": "S101", "stop_name": "Lahore Railway Station", "stop_lat": "31.5204", "stop_lon": "74.3587"},
        {"stop_id": "S102", "stop_name": "Anarkali Bazaar", "stop_lat": "31.5785", "stop_lon": "74.3186"},
        {"stop_id": "S103", "stop_name": "GPO Chowk", "stop_lat": "31.5600", "stop_lon": "74.3100"},
        {"stop_id": "S104", "stop_name": "Mall Road Library", "stop_lat": "31.5650", "stop_lon": "74.3150"},
        {"stop_id": "S105", "stop_name": "High Court", "stop_lat": "31.5700", "stop_lon": "74.3200"},
        # Route G2 stops
        {"stop_id": "S201", "stop_name": "Gulberg Main Market", "stop_lat": "31.5100", "stop_lon": "74.3350"},
        {"stop_id": "S202", "stop_name": "Liberty Market", "stop_lat": "31.5150", "stop_lon": "74.3400"},
        {"stop_id": "S203", "stop_name": "MM Alam Road", "stop_lat": "31.5050", "stop_lon": "74.3420"},
        {"stop_id": "S204", "stop_name": "Ferozepur Road", "stop_lat": "31.5000", "stop_lon": "74.3300"},
        # Route G3 stops
        {"stop_id": "S301", "stop_name": "Allama Iqbal Airport", "stop_lat": "31.5216", "stop_lon": "74.4036"},
        {"stop_id": "S302", "stop_name": "Thokar Niaz Baig", "stop_lat": "31.4700", "stop_lon": "74.3600"},
        {"stop_id": "S303", "stop_name": "DHA Phase 6", "stop_lat": "31.4800", "stop_lon": "74.3700"},
        {"stop_id": "S304", "stop_name": "Cavalry Ground", "stop_lat": "31.5000", "stop_lon": "74.3800"},
    ]

    trips_raw = [
        {"route_id": "GTFS-RT1", "service_id": "WD", "trip_id": "T1001"},
        {"route_id": "GTFS-RT2", "service_id": "WD", "trip_id": "T2001"},
        {"route_id": "GTFS-RT3", "service_id": "WD", "trip_id": "T3001"},
    ]

    stop_times_raw = [
        # T1001 — Mall Road Express
        {"trip_id": "T1001", "stop_id": "S101", "arrival_time": "07:00:00", "departure_time": "07:00:00", "stop_sequence": "1"},
        {"trip_id": "T1001", "stop_id": "S102", "arrival_time": "07:08:00", "departure_time": "07:09:00", "stop_sequence": "2"},
        {"trip_id": "T1001", "stop_id": "S103", "arrival_time": "07:16:00", "departure_time": "07:17:00", "stop_sequence": "3"},
        {"trip_id": "T1001", "stop_id": "S104", "arrival_time": "07:24:00", "departure_time": "07:25:00", "stop_sequence": "4"},
        {"trip_id": "T1001", "stop_id": "S105", "arrival_time": "07:32:00", "departure_time": "07:32:00", "stop_sequence": "5"},
        # T2001 — Gulberg Circular
        {"trip_id": "T2001", "stop_id": "S201", "arrival_time": "08:00:00", "departure_time": "08:00:00", "stop_sequence": "1"},
        {"trip_id": "T2001", "stop_id": "S202", "arrival_time": "08:10:00", "departure_time": "08:11:00", "stop_sequence": "2"},
        {"trip_id": "T2001", "stop_id": "S203", "arrival_time": "08:20:00", "departure_time": "08:21:00", "stop_sequence": "3"},
        {"trip_id": "T2001", "stop_id": "S204", "arrival_time": "08:30:00", "departure_time": "08:30:00", "stop_sequence": "4"},
        # T3001 — Airport Link
        {"trip_id": "T3001", "stop_id": "S301", "arrival_time": "06:30:00", "departure_time": "06:30:00", "stop_sequence": "1"},
        {"trip_id": "T3001", "stop_id": "S302", "arrival_time": "06:50:00", "departure_time": "06:51:00", "stop_sequence": "2"},
        {"trip_id": "T3001", "stop_id": "S303", "arrival_time": "07:05:00", "departure_time": "07:06:00", "stop_sequence": "3"},
        {"trip_id": "T3001", "stop_id": "S304", "arrival_time": "07:20:00", "departure_time": "07:20:00", "stop_sequence": "4"},
    ]

    return {
        "agency.txt": agencies,
        "routes.txt": routes_raw,
        "stops.txt": stops_raw,
        "trips.txt": trips_raw,
        "stop_times.txt": stop_times_raw,
    }


if __name__ == "__main__":
    main()
