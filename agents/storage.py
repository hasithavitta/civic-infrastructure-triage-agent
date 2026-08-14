from dataclasses import asdict
from google.cloud import firestore
from agents.schema import Report

# Initialize the Firestore client
# Application Default Credentials (ADC) are used automatically.
db = firestore.Client()

def save_report(report: Report) -> None:
    """
    Saves a report to the 'reports' Firestore collection.
    Uses report.report_id as the document ID.
    """
    if not report.report_id:
        print("[storage] Warning: cannot save report without a report_id.")
        return
    try:
        doc_ref = db.collection("reports").document(report.report_id)
        doc_ref.set(asdict(report))
    except Exception as e:
        print(f"[storage] Warning: Failed to save report to Firestore: {e}. Degrading gracefully.")

def get_all_reports() -> list[Report]:
    """
    Retrieves all reports from the 'reports' Firestore collection.
    Reconstructs each document as a Report dataclass instance.
    """
    try:
        docs = db.collection("reports").stream()
        reports = []
        for doc in docs:
            data = doc.to_dict()
            # Construct Report object from document dictionary
            reports.append(Report(**data))
        return reports
    except Exception as e:
        print(f"[storage] Warning: Failed to retrieve reports from Firestore: {e}. Returning empty list.")
        return []
