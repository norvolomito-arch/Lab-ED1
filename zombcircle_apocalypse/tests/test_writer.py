"""Tests for incremental telemetry writing."""

import os
import tempfile
import unittest

from telemetry import TelemetryWriter, iter_events, parse_line


class TelemetryWriterTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.log_dir = os.path.join(self.temp_dir.name, "logs")

    def tearDown(self):
        self.temp_dir.cleanup()

    def read_lines(self, path):
        """Read a small test log using the required lazy iteration pattern."""
        with open(path, "r", encoding="utf-8") as log_file:
            return [line for line in log_file]

    def test_reopening_appends_instead_of_overwriting(self):
        first = TelemetryWriter(self.log_dir, buffer_size=1)
        first.log("SESSION_START", "S0001", player="ana")
        first.close()

        second = TelemetryWriter(self.log_dir, buffer_size=1)
        second.log("SESSION_END", "S0001", score=12)
        second.close()

        lines = self.read_lines(first.current_path)
        self.assertEqual(len(lines), 2)
        self.assertEqual(parse_line(lines[0])["event_type"], "SESSION_START")
        self.assertEqual(parse_line(lines[1])["event_type"], "SESSION_END")

    def test_each_event_has_exactly_four_fields(self):
        writer = TelemetryWriter(self.log_dir, buffer_size=1)
        writer.log("SESSION_START", "S0001", player="ana", difficulty="easy")
        writer.close()

        line = self.read_lines(writer.current_path)[0].rstrip("\n")
        self.assertEqual(len(line.split("|")), 4)
        self.assertIsNotNone(parse_line(line))

    def test_timestamps_increase_strictly(self):
        writer = TelemetryWriter(self.log_dir, buffer_size=10)
        for event_number in range(5):
            writer.log("CUSTOM", "S0001", value=event_number)
        writer.close()

        events = [parse_line(line) for line in self.read_lines(writer.current_path)]
        timestamps = [event["timestamp"] for event in events]
        self.assertTrue(all(left < right for left, right in zip(
            timestamps, timestamps[1:])))

    def test_buffer_flushes_when_full(self):
        writer = TelemetryWriter(self.log_dir, buffer_size=3)
        writer.log("CUSTOM", "S0001", value=1)
        self.assertEqual(writer.pending, 1)
        writer.log("CUSTOM", "S0001", value=2)
        self.assertEqual(writer.pending, 2)
        writer.log("CUSTOM", "S0001", value=3)

        self.assertEqual(writer.pending, 0)
        self.assertGreater(os.path.getsize(writer.current_path), 0)
        writer.close()

    def test_manual_flush_writes_pending_lines(self):
        writer = TelemetryWriter(self.log_dir, buffer_size=10)
        writer.log("CUSTOM", "S0001", value=1)
        self.assertEqual(os.path.getsize(writer.current_path), 0)

        writer.flush()

        self.assertEqual(writer.pending, 0)
        self.assertEqual(len(self.read_lines(writer.current_path)), 1)
        writer.close()

    def test_rotation_creates_sequential_files(self):
        writer = TelemetryWriter(self.log_dir, buffer_size=1, max_bytes=1)
        for event_number in range(3):
            writer.log("CUSTOM", "S0001", value=event_number)
        writer.close()

        names = sorted(os.listdir(self.log_dir))
        self.assertEqual(names, ["events_001.log", "events_002.log",
                                 "events_003.log"])

    def test_writer_continues_from_latest_existing_file(self):
        first = TelemetryWriter(self.log_dir, buffer_size=1, max_bytes=10000)
        first.log("CUSTOM", "S0001", value=1)
        first_path = first.current_path
        first.close()

        second = TelemetryWriter(self.log_dir, buffer_size=1, max_bytes=10000)
        self.assertEqual(second.current_path, first_path)
        second.log("CUSTOM", "S0001", value=2)
        second.close()
        self.assertEqual(len(self.read_lines(first_path)), 2)

    def test_close_is_idempotent(self):
        writer = TelemetryWriter(self.log_dir, buffer_size=10)
        writer.log("CUSTOM", "S0001", value=1)
        writer.close()
        writer.close()
        self.assertEqual(len(self.read_lines(writer.current_path)), 1)

    def test_context_manager_flushes_even_when_body_raises(self):
        with self.assertRaises(RuntimeError):
            with TelemetryWriter(self.log_dir, buffer_size=10) as writer:
                writer.log("CUSTOM", "S0001", value=1)
                raise RuntimeError("test close")

        log_path = os.path.join(self.log_dir, "events_001.log")
        self.assertEqual(len(self.read_lines(log_path)), 1)

    def test_try_finally_flushes_pending_lines(self):
        writer = TelemetryWriter(self.log_dir, buffer_size=10)
        try:
            writer.log("CUSTOM", "S0001", value=1)
        finally:
            writer.close()

        self.assertEqual(len(self.read_lines(writer.current_path)), 1)

    def test_delimiters_round_trip_through_reader(self):
        writer = TelemetryWriter(self.log_dir, buffer_size=1)
        original = "ana|blue;level=3"
        writer.log("SESSION_START", "S|0001", player=original)
        writer.close()

        events = list(iter_events(self.log_dir))
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["session_id"], "S|0001")
        self.assertEqual(events[0]["params"]["player"], original)

    def test_empty_values_are_written_as_valid_sentinels(self):
        writer = TelemetryWriter(self.log_dir, buffer_size=1)
        writer.log("CUSTOM", "S0001", empty="", missing=None)
        writer.close()

        event = next(iter_events(self.log_dir))
        self.assertEqual(event["params"]["empty"], "none")
        self.assertEqual(event["params"]["missing"], "none")

    def test_buffer_does_not_wait_until_close_to_write(self):
        writer = TelemetryWriter(self.log_dir, buffer_size=4, max_bytes=100000)
        for event_number in range(4):
            writer.log("CUSTOM", "S0001", value=event_number)
        flushed_size = os.path.getsize(writer.current_path)

        self.assertGreater(flushed_size, 0)
        self.assertEqual(writer.pending, 0)
        for event_number in range(4, 7):
            writer.log("CUSTOM", "S0001", value=event_number)
            self.assertLess(writer.pending, writer.buffer_size)
        self.assertEqual(os.path.getsize(writer.current_path), flushed_size)
        writer.close()


if __name__ == "__main__":
    unittest.main()