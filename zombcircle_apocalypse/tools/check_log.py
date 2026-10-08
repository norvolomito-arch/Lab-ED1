"""Print session-start and data-quality counts for a log directory."""

import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from telemetry import QualityReport, iter_events


def main(log_dir=None):
    """Stream a log directory and print its session and quality counts."""
    if log_dir is None:
        log_dir = os.path.join(BASE_DIR, "logs")

    report = QualityReport()
    sessions_started = 0
    for event in iter_events(log_dir, report=report):
        if event["event_type"] == "SESSION_START":
            sessions_started += 1

    print("Sesiones iniciadas: %s" % format(sessions_started, ","))
    report.print_report()


if __name__ == "__main__":
    selected_log_dir = sys.argv[1] if len(sys.argv) > 1 else None
    main(selected_log_dir)