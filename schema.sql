-- Create the reports table matching the Report dataclass fields
CREATE TABLE IF NOT EXISTS reports (
    report_id TEXT PRIMARY KEY,
    raw_text TEXT,
    image_filename TEXT,
    issue_type TEXT,
    description TEXT,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    address TEXT,
    is_duplicate BOOLEAN NOT NULL DEFAULT FALSE,
    duplicate_of_report_id TEXT,
    severity_score INTEGER,
    severity_reasoning TEXT,
    department TEXT,
    work_order_text TEXT,
    status TEXT NOT NULL DEFAULT 'open'
);
