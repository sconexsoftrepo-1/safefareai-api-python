"""Generate 20 sample PRS seat CSV files (one every 10 seconds) for the BMS vs Sensor comparison.

* 20 files named  PRS_<iot kit>_<dd-mm-yyyy>_<HH-MM-SS>.csv , 10 seconds apart, 60 seats (A1..A60) each.
* EXACTLY 5 files have the GPS of one BMS stop each (the bus is AT stops 1..5); the other 15 are on the road,
  far (> 1 km) from every stop, so they must NOT match.
* Each CSV has the columns  timestamp, sensor_sub_id, sensor_data, lat, long  (lat/long are read by the PRS ingestion
  and stored in dbo.prs_sensor_readings).
* Seat changes are random (seeded -> repeatable) but planned from the BMS rows: at every stop the seats that become
  occupied = bms_in and the seats that become empty = bms_out, so the sensor In / Out / Total EXACTLY equal the BMS
  In / Out / Total and every stop is a MATCH. (Use --mismatch-stops 4 to make ONLY that stop differ: one extra
  passenger is on board at the stop, who gets off again on the road right after it, so the other stops stay MATCH.)

The 5 stop positions are read from dbo.bms_stop_details (so they always equal the real BMS rows), or from the
built-in sample list with --offline.

Examples
    python tools/generate_bms_sample_csvs.py                       # write 20 files to sample_data/prs_bms/
    python tools/generate_bms_sample_csvs.py --upload              # ... and put them in the S3 folder from .env
    python tools/generate_bms_sample_csvs.py --live --upload       # real time: one file every 10 s (200 s in total)
    python tools/generate_bms_sample_csvs.py --live --upload --mismatch-stops 4     # only stop 4 will be MISMATCH
    python tools/generate_bms_sample_csvs.py --live --upload --mismatch-stops 4 --carry-extra   # stop 4 AND stop 5 MISMATCH
"""
from __future__ import annotations

import argparse
import csv
import random
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SEATS = [f"A{i}" for i in range(1, 61)]

# fallback when --offline (same as dbo.bms_stop_details sample rows)
# (sequence, name, lat, long, bms_in, bms_out, bms_total)
SAMPLE_STOPS = [
    (1, "Anakapalli", 17.6863300, 83.0023400, 12, 0, 12),
    (2, "Tuni", 17.3685600, 82.5432300, 6, 1, 17),
    (3, "Rajahmundry", 17.0012000, 81.7897000, 9, 3, 23),
    (4, "Vijayawada", 16.5088038, 80.6156014, 7, 5, 25),
    (5, "Ongole", 15.5112042, 80.0418439, 0, 25, 0),
]

# file number (1..20) at which the bus is AT stop N; the file right after it is on the road again (= departure)
STOP_FILE = {1: 3, 2: 7, 3: 11, 4: 15, 5: 19}

def build_plan(stops, mismatch_stops: Set[int], carry_extra: bool = False) -> Dict[int, Tuple[int, int]]:
    """(In, Out) planned for each stop = the BMS In / Out of that stop (exact match). A stop listed in
    --mismatch-stops gets ONE extra In (so its In and Total are one higher than BMS); that extra passenger leaves
    again on the road right after the stop (see build_seat_states), so later stops are not affected.
    With carry_extra the extra passenger stays on the bus until the LAST stop and gets off there, so the last stop's
    Out is one higher than BMS too (e.g. Ongole Out 26 instead of 25) and the last stop is a MISMATCH as well."""
    plan: Dict[int, Tuple[int, int]] = {}
    last_seq = stops[-1][0]
    carried = len([m for m in mismatch_stops if m != last_seq]) if carry_extra else 0
    occupied = 0
    for seq, name, lat, lon, bms_in, bms_out, bms_total in stops:
        if bms_out > occupied:
            sys.exit(f"Stop {seq} {name}: BMS Out {bms_out} is more than the {occupied} passengers on board, "
                     f"so the BMS rows are not consistent (previous total + In - Out must equal the next total).")
        occupied = occupied + bms_in - bms_out
        if occupied != bms_total:
            print(f"WARNING stop {seq} {name}: previous total + In - Out = {occupied} but bms_total is {bms_total}; "
                  f"this stop cannot be an exact match.")
        plan[seq] = (bms_in + (1 if seq in mismatch_stops else 0), bms_out + (carried if seq == last_seq else 0))
    return plan


def load_stops(offline: bool) -> List[Tuple[int, str, float, float, int, int, int]]:
    if offline:
        return SAMPLE_STOPS
    from app.database.sensor_connection import get_db_connection
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT stop_sequence, stop_name, lat, [long], bms_in, bms_out, bms_total
            FROM dbo.bms_stop_details
            WHERE vehicle_number = ? AND device_id = ? ORDER BY stop_sequence
        """, ARGS.vehicle, ARGS.device_id)
        rows = [(r[0], r[1], float(r[2]), float(r[3]), r[4], r[5], r[6]) for r in cur.fetchall()]
    finally:
        conn.close()
    if len(rows) != 5:
        sys.exit(f"Expected 5 BMS stops for {ARGS.vehicle}/{ARGS.device_id}, found {len(rows)} (use --offline for the built-in list)")
    return rows


def road_position(stops, file_no: int) -> Tuple[float, float]:
    """A point on the road, far (> 1 km) from every stop. Files 1-2 are before stop 1, file 20 is after stop 5,
    the rest lie 25 % / 50 % / 75 % of the way between the stop before and the stop after."""
    if file_no in (1, 2):
        return stops[0][2] - 0.040 + 0.010 * (file_no - 1), stops[0][3] - 0.040 + 0.010 * (file_no - 1)
    if file_no == 20:
        return stops[4][2] - 0.040, stops[4][3] - 0.040
    previous_stop_no = max(s for s, f in STOP_FILE.items() if f < file_no)       # 1..4
    steps_after = file_no - STOP_FILE[previous_stop_no]                           # 1, 2 or 3
    fraction = steps_after / 4.0
    a, b = stops[previous_stop_no - 1], stops[previous_stop_no]
    return a[2] + (b[2] - a[2]) * fraction, a[3] + (b[3] - a[3]) * fraction


def build_seat_states(rng: random.Random, plan: Dict[int, Tuple[int, int]], mismatch_stops: Set[int] = frozenset(),
                      carry_extra: bool = False) -> Dict[int, Set[str]]:
    """Occupied seats of every file 1..20, with random seats but the planned In / Out at the 5 stop files."""
    states: Dict[int, Set[str]] = {}
    occupied: Set[str] = set()
    stop_of_file = {f: s for s, f in STOP_FILE.items()}
    extra_to_remove: Optional[str] = None                    # the one extra passenger of a mismatch stop
    for file_no in range(1, 21):
        if extra_to_remove is not None:                       # first file after the stop = the bus is on the road again
            occupied = occupied - {extra_to_remove}
            extra_to_remove = None
        if file_no in stop_of_file:
            seat_in, seat_out = plan[stop_of_file[file_no]]
            leaving = set(rng.sample(sorted(occupied), seat_out)) if seat_out else set()
            free = [s for s in SEATS if s not in occupied]
            boarding = set(rng.sample(free, seat_in))
            occupied = (occupied - leaving) | boarding
            if stop_of_file[file_no] in mismatch_stops and not carry_extra:
                extra_to_remove = sorted(boarding)[0]
        states[file_no] = set(occupied)               # between stops the seats do not change
    return states


def write_csv(path: Path, ts: datetime, occupied: Set[str], lat: float, lon: float) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["timestamp", "sensor_sub_id", "sensor_data", "lat", "long"])
        for seat in SEATS:
            reading = "occupied" if seat in occupied else "not_occupied"
            w.writerow([ts.strftime("%Y-%m-%d %H:%M:%S"), 5, f"unique_number:{seat},reading:{reading}", f"{lat:.7f}", f"{lon:.7f}"])


def file_name(kit: str, ts: datetime) -> str:
    return f"PRS_{kit}_{ts.strftime('%d-%m-%Y_%H-%M-%S')}.csv"


def upload(path: Path) -> None:
    from app.services.s3_service import s3_service
    key = f"{s3_service.folder.rstrip('/')}/{path.name}" if s3_service.folder else path.name
    s3_service.s3_client.upload_file(str(path), s3_service.bucket_name, key)
    print(f"  uploaded s3://{s3_service.bucket_name}/{key}")


def main() -> None:
    stops = load_stops(ARGS.offline)
    rng = random.Random(ARGS.seed)
    mismatch = {int(x) for x in ARGS.mismatch_stops.split(',') if x.strip()} if ARGS.mismatch_stops else set()
    plan = build_plan(stops, mismatch, ARGS.carry_extra)
    states = build_seat_states(rng, plan, mismatch, ARGS.carry_extra)
    tz = ZoneInfo(ARGS.timezone)
    now = datetime.now(tz).replace(tzinfo=None, microsecond=0)
    start = datetime.strptime(ARGS.start, "%Y-%m-%d %H:%M:%S") if ARGS.start else now - timedelta(seconds=10 * 19)

    out = Path(ARGS.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    stop_of_file = {f: s for s, f in STOP_FILE.items()}

    for file_no in range(1, 21):
        ts = datetime.now(tz).replace(tzinfo=None, microsecond=0) if ARGS.live else start + timedelta(seconds=10 * (file_no - 1))
        if file_no in stop_of_file:
            seq = stop_of_file[file_no]
            lat, lon = stops[seq - 1][2] + ARGS.stop_offset_m / 111_195.0, stops[seq - 1][3]
            where = f"AT STOP {seq} {stops[seq - 1][1]}"
        else:
            lat, lon = road_position(stops, file_no)
            where = "on the road"
        path = out / file_name(ARGS.iot_kit, ts)
        write_csv(path, ts, states[file_no], lat, lon)
        print(f"{file_no:2d}. {path.name}  occupied={len(states[file_no]):2d}  lat={lat:.5f} long={lon:.5f}  {where}")
        if ARGS.upload:
            upload(path)
        if ARGS.live and file_no < 20:
            time.sleep(10)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out-dir", default=str(ROOT / "sample_data" / "prs_bms"))
    p.add_argument("--iot-kit", default="IOT-KIT-001", help="kit name in the file name (must map to the vehicle)")
    p.add_argument("--vehicle", default="AP31Z0044")
    p.add_argument("--device-id", type=int, default=1215)
    p.add_argument("--start", help='timestamp of file 1, "YYYY-MM-DD HH:MM:SS" (default: file 20 = now)')
    p.add_argument("--timezone", default="Asia/Kolkata")
    p.add_argument("--stop-offset-m", type=float, default=15.0, help="how far (m, north) from the BMS point the bus stands")
    p.add_argument("--seed", type=int, default=2026)
    p.add_argument("--mismatch-stops", default="", help="comma separated stop numbers that should differ from BMS, e.g. 2,4 (default: none, all MATCH)")
    p.add_argument("--carry-extra", action="store_true",
                   help="with --mismatch-stops: the extra passenger stays on board until the last stop (so the last stop is a MISMATCH too)")
    p.add_argument("--offline", action="store_true", help="do not read dbo.bms_stop_details; use the built-in sample stops")
    p.add_argument("--upload", action="store_true", help="also upload each file to the S3 folder from .env")
    p.add_argument("--live", action="store_true", help="real time: one file every 10 s, timestamp = now")
    ARGS = p.parse_args()
    main()