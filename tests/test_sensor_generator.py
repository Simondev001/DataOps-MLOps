
import unittest
import random
from datetime import datetime, timezone

from src.ingestion.sensor_generator import (
    EVENT_FIELDS,
    generate_event,
    generate_events,
    generate_sensor,
    generate_sensors,
    simulate_capture,
    validate_event,
)


class TestSensorGenerator(unittest.TestCase):

    def test_sensor_id(self):
        sensor = generate_sensor(1)
        self.assertEqual(sensor["sensor_id"], "CAP_001")

    def test_valid_coordinates(self):
        sensor = generate_sensor(1)

        self.assertGreaterEqual(sensor["latitude"], -90)
        self.assertLessEqual(sensor["latitude"], 90)

        self.assertGreaterEqual(sensor["longitude"], -180)
        self.assertLessEqual(sensor["longitude"], 180)

    def test_valid_status(self):
        sensor = generate_sensor(1)

        self.assertIn(sensor["status"], ["active", "inactive"])

    def test_generate_multiple_sensors(self):
        sensors = generate_sensors(5)

        self.assertEqual(len(sensors), 5)

    def test_unique_sensor_ids(self):
        sensors = generate_sensors(10)

        sensor_ids = [
            sensor["sensor_id"]
            for sensor in sensors
        ]

        self.assertEqual(len(sensor_ids), len(set(sensor_ids)))

    def test_invalid_sensor_number(self):
        with self.assertRaises(ValueError):
            generate_sensor(0)

    def test_invalid_sensor_count(self):
        with self.assertRaises(ValueError):
            generate_sensors(0)

    def test_sensor_is_in_agadir_zone_and_has_utc_timestamp(self):
        sensor = generate_sensor(8, rng=random.Random(12))
        self.assertAlmostEqual(sensor["latitude"], 30.4278, delta=0.08)
        self.assertAlmostEqual(sensor["longitude"], -9.5981, delta=0.08)
        self.assertTrue(datetime.fromisoformat(sensor["created_at"]).utcoffset().total_seconds() == 0)

    def test_event_follows_json_contract_and_validates(self):
        event = generate_event("CAP_001", datetime(2026, 1, 1, tzinfo=timezone.utc),
                               rng=random.Random(1), anomaly_probability=0)
        self.assertEqual(set(event), EVENT_FIELDS)
        self.assertEqual(event["sensor_id"], "CAP_001")
        self.assertEqual(event["status"], "active")
        self.assertEqual(set(event["location"]), {"lat", "lon"})
        self.assertEqual(set(event["measurements"]), {
            "pm2_5", "pm10", "no2", "o3", "temperature", "humidity"
        })
        validate_event(event)

    def test_event_rejects_invalid_fields_and_values(self):
        event = generate_event("CAP_001", rng=random.Random(2), anomaly_probability=0)
        event["measurements"]["humidity"] = 101
        with self.assertRaises(ValueError):
            validate_event(event)

    def test_generate_events_have_regular_timestamps(self):
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        events = generate_events("CAP_001", 3, start_at=start, interval_seconds=30,
                                 rng=random.Random(3), anomaly_probability=0)
        self.assertEqual(len(events), 3)
        self.assertEqual(events[2]["timestamp"], "2026-01-01T00:01:00Z")

    def test_capture_adds_sensor_location_to_common_contract(self):
        sensors = [{"sensor_id": "CAP_001", "status": "active",
                    "latitude": 30.4, "longitude": -9.6}]
        event = simulate_capture(sensors, 1, rng=random.Random(5))[0]
        self.assertEqual(event["location"], {"lat": 30.4, "lon": -9.6})
        validate_event(event)

    def test_temporal_variation_and_anomaly_peaks_are_simulated(self):
        midnight = datetime(2026, 1, 1, 0, tzinfo=timezone.utc)
        noon = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)
        night_event = generate_event("CAP_001", midnight, rng=random.Random(20),
                                     anomaly_probability=0)
        day_event = generate_event("CAP_001", noon, rng=random.Random(20),
                                   anomaly_probability=0)
        self.assertGreater(day_event["measurements"]["temperature"],
                           night_event["measurements"]["temperature"])

        normal = generate_event("CAP_001", noon, rng=random.Random(21),
                                anomaly_probability=0)
        peak = generate_event("CAP_001", noon, rng=random.Random(21),
                              anomaly_probability=1)
        for field in ("pm2_5", "pm10", "no2", "o3"):
            self.assertGreater(peak["measurements"][field], normal["measurements"][field])

    def test_capture_skips_inactive_sensors(self):
        sensors = [
            {"sensor_id": "CAP_001", "status": "active", "latitude": 30.4,
             "longitude": -9.6},
            {"sensor_id": "CAP_002", "status": "inactive", "latitude": 30.5,
             "longitude": -9.7},
        ]
        events = simulate_capture(sensors, 2, rng=random.Random(4))
        self.assertEqual(len(events), 2)
        self.assertEqual({event["sensor_id"] for event in events}, {"CAP_001"})


if __name__ == "__main__":
    unittest.main()
