import os
from dataclasses import asdict, fields
from dotenv import load_dotenv
from supabase import create_client, Client
from agents.schema import Report

# Load environment variables (useful for local runs & standalone test scripts)
load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ImportError(
        "Supabase client initialization failed: "
        "SUPABASE_URL and SUPABASE_KEY environment variables must be set."
    )

# Initialize the Supabase client
db: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def save_report(report: Report) -> None:
    """
    Saves a report to the 'reports' Supabase table.
    Uses report.report_id as the primary key.
    """
    if not report.report_id:
        print("[storage] Warning: cannot save report without a report_id.")
        return
    try:
        data = asdict(report)
        db.table("reports").upsert(data).execute()
    except Exception as e:
        print(f"[storage] Warning: Failed to save report to Supabase: {e}. Degrading gracefully.")

def get_all_reports() -> list[Report]:
    """
    Retrieves all reports from the 'reports' Supabase table.
    Reconstructs each row as a Report dataclass instance.
    """
    try:
        response = db.table("reports").select("*").execute()
        reports = []
        report_fields = {f.name for f in fields(Report)}
        for row in response.data:
            filtered_row = {k: v for k, v in row.items() if k in report_fields}
            reports.append(Report(**filtered_row))
        return reports
    except Exception as e:
        print(f"[storage] Warning: Failed to retrieve reports from Supabase: {e}. Returning empty list.")
        return []

def get_nearby_reports(lat: float, lon: float, radius_meters: float) -> list[Report]:
    """
    Retrieves reports within radius_meters from the specified coordinates
    using the Supabase RPC function 'get_reports_near'.
    Reconstructs each row as a Report dataclass instance.
    """
    try:
        response = db.rpc(
            'get_reports_near',
            {'lat': lat, 'lon': lon, 'radius_meters': radius_meters}
        ).execute()
        reports = []
        report_fields = {f.name for f in fields(Report)}
        for row in response.data:
            filtered_row = {k: v for k, v in row.items() if k in report_fields}
            reports.append(Report(**filtered_row))
        return reports
    except Exception as e:
        print(f"[storage] Warning: Failed to retrieve nearby reports from Supabase: {e}. Returning empty list.")
        return []


