"""Streaming quality report for event log files."""


class QualityReport:
    """Accumulate log quality counts and track unfinished sessions.

    Session IDs are treated as globally unique across all log files. A
    repeated SESSION_START for an already-open ID is idempotent, and a
    SESSION_END without a matching start is ignored. The set of open IDs is
    retained between files, so a session can span file boundaries.

    Memory use depends on the number of currently open sessions, not on the
    number of events processed.
    """

    def __init__(self):
        self.files = 0
        self.lines_read = 0
        self.valid = 0
        self.corrupt = 0
        self._open_sessions = set()
        self._finished = False

    @property
    def incomplete_sessions(self):
        """Number of session IDs without a matching SESSION_END."""
        return len(self._open_sessions)

    def add_file(self):
        """Record that a log file was opened."""
        self.files += 1

    def add_line(self):
        """Record that one line was read, whether valid or corrupt."""
        self.lines_read += 1

    def add_valid(self, event):
        """Record a valid event and update the open-session set."""
        self.valid += 1
        event_type = event.get("event_type")
        session_id = event.get("session_id")
        if event_type == "SESSION_START":
            self._open_sessions.add(session_id)
        elif event_type == "SESSION_END":
            self._open_sessions.discard(session_id)

    def add_corrupt(self):
        """Record one corrupt line."""
        self.corrupt += 1

    def finish(self):
        """Mark that the complete log traversal has finished."""
        self._finished = True

    def format(self):
        """Return the quality report using the laboratory's exact layout."""
        if self.lines_read:
            valid_percent = self.valid / self.lines_read * 100
            corrupt_percent = self.corrupt / self.lines_read * 100
        else:
            valid_percent = 0.0
            corrupt_percent = 0.0

        return (
            "Archivos procesados: {files}\n"
            "Lineas leidas: {lines}\n"
            "Eventos validos: {valid} ({valid_percent:.2f}%)\n"
            "Lineas corruptas: {corrupt} ({corrupt_percent:.2f}%)\n"
            "Sesiones incompletas: {incomplete} (SESSION_START sin SESSION_END)"
        ).format(
            files=format(self.files, ","),
            lines=format(self.lines_read, ","),
            valid=format(self.valid, ","),
            valid_percent=valid_percent,
            corrupt=format(self.corrupt, ","),
            corrupt_percent=corrupt_percent,
            incomplete=format(self.incomplete_sessions, ","),
        )

    def print_report(self):
        """Print the formatted quality report."""
        print(self.format())