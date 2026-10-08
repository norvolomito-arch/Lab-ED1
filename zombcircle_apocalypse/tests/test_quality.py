"""Tests for streaming quality reporting."""

import contextlib
import io
import os
import tempfile
import tracemalloc
import unittest

from telemetry import QualityReport, iter_events


class FinishTrackingReport(QualityReport):
    """Track calls to finish without changing the report protocol."""

    def __init__(self):
        super().__init__()
        self.finish_calls = 0

    def finish(self):
        self.finish_calls += 1
        super().finish()


class QualityReportTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.log_dir = os.path.join(self.temp_dir.name, "logs")
        os.makedirs(self.log_dir)

    def tearDown(self):
        self.temp_dir.cleanup()

    def write_log(self, filename, contents):
        path = os.path.join(self.log_dir, filename)
        with open(path, "w", encoding="utf-8") as log_file:
            for line in contents:
                log_file.write(line)
        return path

    def test_counts_are_updated_by_iter_events(self):
        self.write_log("events_001.log", (
            "1.0|S0001|SESSION_START|player=ana\n",
            "not-a-time|S0001|CUSTOM|value=1\n",
            "1.1|S0001|CUSTOM|value=1\n",
        ))
        self.write_log("events_002.log", (
            "2.0|S0002|SESSION_START|player=bob\n",
            "2.1|S0002|SESSION_END|score=2\n",
            "   \n",
        ))
        report = QualityReport()
        event_count = 0

        for event in iter_events(self.log_dir, report=report):
            event_count += 1

        self.assertEqual(event_count, 4)
        self.assertEqual(report.files, 2)
        self.assertEqual(report.lines_read, 6)
        self.assertEqual(report.valid, 4)
        self.assertEqual(report.corrupt, 2)
        self.assertEqual(report.incomplete_sessions, 1)

    def test_session_ids_span_files_and_duplicate_events_are_idempotent(self):
        self.write_log("events_001.log", (
            "1.0|cross|SESSION_START|\n",
            "1.1|cross|SESSION_START|\n",
            "1.2|orphan|SESSION_END|\n",
        ))
        self.write_log("events_002.log", (
            "2.0|cross|SESSION_END|\n",
            "2.1|open|SESSION_START|\n",
        ))
        report = QualityReport()

        for _ in iter_events(self.log_dir, report=report):
            pass

        self.assertEqual(report.incomplete_sessions, 1)
        self.assertEqual(report.valid, 5)

    def test_format_matches_the_section_seven_example(self):
        report = QualityReport()
        for session_number in range(4):
            report.add_valid({"event_type": "SESSION_START",
                              "session_id": "S%04d" % session_number})
        report.files = 3
        report.lines_read = 42180
        report.valid = 41955
        report.corrupt = 225

        expected = (
            "Archivos procesados: 3\n"
            "Lineas leidas: 42,180\n"
            "Eventos validos: 41,955 (99.47%)\n"
            "Lineas corruptas: 225 (0.53%)\n"
            "Sesiones incompletas: 4 (SESSION_START sin SESSION_END)"
        )
        self.assertEqual(report.format(), expected)

    def test_empty_report_formats_zero_percentages(self):
        report = QualityReport()
        self.assertEqual(report.format(), (
            "Archivos procesados: 0\n"
            "Lineas leidas: 0\n"
            "Eventos validos: 0 (0.00%)\n"
            "Lineas corruptas: 0 (0.00%)\n"
            "Sesiones incompletas: 0 (SESSION_START sin SESSION_END)"
        ))

    def test_print_report_prints_formatted_text(self):
        report = QualityReport()
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            report.print_report()
        self.assertEqual(output.getvalue(), report.format() + "\n")

    def test_finish_is_not_called_when_generator_is_abandoned(self):
        self.write_log("events_001.log", (
            "1.0|S0001|SESSION_START|player=ana\n",
            "1.1|S0001|CUSTOM|value=1\n",
        ))
        report = FinishTrackingReport()
        events = iter_events(self.log_dir, report=report)

        next(events)
        events.close()

        self.assertEqual(report.finish_calls, 0)
        self.assertEqual(report.incomplete_sessions, 1)

    def test_finish_is_called_after_complete_traversal(self):
        self.write_log("events_001.log", ("1.0|S0001|CUSTOM|value=1\n",))
        report = FinishTrackingReport()

        for _ in iter_events(self.log_dir, report=report):
            pass

        self.assertEqual(report.finish_calls, 1)

    def test_streaming_memory_does_not_scale_with_number_of_lines(self):
        small_path = os.path.join(self.log_dir, "events_001.log")
        large_dir = os.path.join(self.temp_dir.name, "large_logs")
        os.makedirs(large_dir)
        large_path = os.path.join(large_dir, "events_001.log")
        line = "1.0|S0001|CUSTOM|value=1\n"
        for path, line_count in ((small_path, 300), (large_path, 30000)):
            with open(path, "w", encoding="utf-8") as log_file:
                for _ in range(line_count):
                    log_file.write(line)

        def measure_peak(path):
            event_count = 0
            tracemalloc.start()
            try:
                for _ in iter_events(os.path.dirname(path)):
                    event_count += 1
                _, peak = tracemalloc.get_traced_memory()
            finally:
                tracemalloc.stop()
            return event_count, peak

        small_count, small_peak = measure_peak(small_path)
        large_count, large_peak = measure_peak(large_path)

        self.assertEqual(small_count, 300)
        self.assertEqual(large_count, 30000)
        self.assertLessEqual(large_peak, small_peak + 32768)


if __name__ == "__main__":
    unittest.main()