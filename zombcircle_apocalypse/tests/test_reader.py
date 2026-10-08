"""Tests for robust streaming event log parsing."""

import os
import tempfile
import unittest

from telemetry import iter_events, parse_line


class TelemetryReaderTests(unittest.TestCase):
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

    def test_parse_line_rejects_each_required_corrupt_case(self):
        corrupt_lines = (
            "",
            "   \t",
            "1.0|S0001|CUSTOM",
            "1.0|S0001|CUSTOM|value=1|extra",
            "1.0|S0001|CUSTOM|missing_equals",
            "1.0|S0001|CUSTOM|player=",
            "1.0|S0001|SESSION_END|score=abc",
            "not-a-timestamp|S0001|CUSTOM|",
        )
        for line in corrupt_lines:
            with self.subTest(line=line):
                self.assertIsNone(parse_line(line))

    def test_iter_events_discards_an_unterminated_last_line(self):
        complete = "1.0|S0001|SESSION_START|player=ana\n"
        truncated = "2.0|S0001|SESSION_END|score=10"
        self.write_log("events_001.log", (complete, truncated))

        events = list(iter_events(self.log_dir))

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["event_type"], "SESSION_START")

    def test_missing_directory_returns_no_events(self):
        missing_dir = os.path.join(self.temp_dir.name, "missing")
        self.assertEqual(list(iter_events(missing_dir)), [])

    def test_empty_directory_returns_no_events(self):
        self.assertEqual(list(iter_events(self.log_dir)), [])

    def test_log_files_are_ordered_numerically(self):
        self.write_log("events_1000.log", ("2.0|S1000|CUSTOM|value=1000\n",))
        self.write_log("events_999.log", ("1.0|S0999|CUSTOM|value=999\n",))

        events = list(iter_events(self.log_dir))

        self.assertEqual([event["session_id"] for event in events],
                         ["S0999", "S1000"])

    def test_numeric_values_are_converted_to_int_or_float(self):
        line = (
            "1.5|S0001|SESSION_END|score=3200;level=4;duration=77.6;"
            "amount=12;wave=2;time=1.25\n"
        )
        self.write_log("events_001.log", (line,))

        event = next(iter_events(self.log_dir))
        params = event["params"]

        self.assertIs(type(params["score"]), int)
        self.assertIs(type(params["level"]), int)
        self.assertIs(type(params["amount"]), int)
        self.assertIs(type(params["wave"]), int)
        self.assertIs(type(params["duration"]), float)
        self.assertIs(type(params["time"]), float)
        self.assertIs(type(event["timestamp"]), float)
        self.assertEqual(params["score"], 3200)
        self.assertEqual(params["duration"], 77.6)


if __name__ == "__main__":
    unittest.main()