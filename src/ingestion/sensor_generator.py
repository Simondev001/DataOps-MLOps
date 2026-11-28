"""Génération des capteurs et des événements IoT de qualité de l'air.

Chaque événement respecte le contrat commun : ``sensor_id``, ``timestamp``
(UTC ISO 8601), ``location`` (lat/lon), ``measurements`` et ``status``.
Les concentrations sont en µg/m³, la température en °C et l'humidité relative
est exprimée en pourcentage."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import math
import random
import sys
from typing import Any, Iterable


# Zone de simulation : Agadir, Maroc.
AGADIR_LATITUDE = 30.4278
AGADIR_LONGITUDE = -9.5981
LATITUDE_RANGE = 0.08
LONGITUDE_RANGE = 0.08

EVENT_FIELDS = frozenset({
    "sensor_id", "timestamp", "location", "measurements", "status",
})
POLLUTANT_FIELDS = ("pm2_5", "pm10", "no2", "o3")
MEASUREMENT_FIELDS = frozenset((*POLLUTANT_FIELDS, "temperature", "humidity"))
BASELINES = {"pm2_5": 12.0, "pm10": 24.0, "no2": 18.0, "o3": 35.0}


def _rng(rng: random.Random | None) -> random.Random:
    return rng if rng is not None else random


def generate_sensor(sensor_number: int, *, rng: random.Random | None = None) -> dict[str, Any]:
    """Génère un capteur avec identifiant unique, coordonnées et statut."""
    if isinstance(sensor_number, bool) or not isinstance(sensor_number, int) or sensor_number <= 0:
        raise ValueError("sensor_number doit être un entier strictement positif.")

    random_source = _rng(rng)
    return {
        "sensor_id": f"CAP_{sensor_number:03d}",
        "latitude": round(random_source.uniform(AGADIR_LATITUDE - LATITUDE_RANGE,
                                                AGADIR_LATITUDE + LATITUDE_RANGE), 6),
        "longitude": round(random_source.uniform(AGADIR_LONGITUDE - LONGITUDE_RANGE,
                                                 AGADIR_LONGITUDE + LONGITUDE_RANGE), 6),
        "status": random_source.choices(["active", "inactive"], weights=[0.9, 0.1], k=1)[0],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def generate_sensors(number_of_sensors: int = 5, *, rng: random.Random | None = None) -> list[dict[str, Any]]:
    """Génère une liste de capteurs."""
    if isinstance(number_of_sensors, bool) or not isinstance(number_of_sensors, int) or number_of_sensors <= 0:
        raise ValueError("number_of_sensors doit être un entier strictement positif.")
    random_source = _rng(rng)
    return [generate_sensor(i, rng=random_source) for i in range(1, number_of_sensors + 1)]


def _timestamp(value: datetime | None) -> datetime:
    result = value if value is not None else datetime.now(timezone.utc)
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("measured_at doit inclure un fuseau horaire.")
    return result.astimezone(timezone.utc)


def generate_event(sensor_id: str, measured_at: datetime | None = None, *,
                   sequence: int = 0, rng: random.Random | None = None,
                   anomaly_probability: float = 0.02,
                   location: dict[str, float] | None = None,
                   status: str = "active") -> dict[str, Any]:
    """Génère une mesure avec variations temporelles et quelques pics simulés.

    ``sequence`` rend le cycle journalier reproductible et permet de simuler
    des événements espacés régulièrement. Un ``rng`` peut être fourni pour
    obtenir des données reproductibles.
    """
    if not isinstance(sensor_id, str) or not sensor_id.strip():
        raise ValueError("sensor_id doit être une chaîne non vide.")
    if status != "active":
        raise ValueError("Un événement ne peut être émis que par un capteur actif.")
    if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 0:
        raise ValueError("sequence doit être un entier positif ou nul.")
    if not 0 <= anomaly_probability <= 1:
        raise ValueError("anomaly_probability doit être comprise entre 0 et 1.")

    random_source = _rng(rng)
    timestamp = _timestamp(measured_at)
    # Cycle de 24 heures : trafic plus élevé le matin et le soir, ozone l'après-midi.
    hour = timestamp.hour + timestamp.minute / 60 + timestamp.second / 3600
    traffic = max(0.0, math.cos((hour - 8) * math.tau / 24)) + max(0.0, math.cos((hour - 18) * math.tau / 24))
    daylight = max(0.0, math.sin((hour - 6) * math.pi / 12))

    event: dict[str, Any] = {
        "sensor_id": sensor_id,
        "timestamp": timestamp.isoformat().replace("+00:00", "Z"),
        "location": location if location is not None else {"lat": AGADIR_LATITUDE, "lon": AGADIR_LONGITUDE},
        "measurements": {},
        "status": status,
    }
    for field in POLLUTANT_FIELDS:
        baseline = BASELINES[field]
        if field in ("pm2_5", "pm10", "no2"):
            baseline += traffic * {"pm2_5": 8, "pm10": 12, "no2": 15}[field]
        else:
            baseline += daylight * 22
        value = max(0.0, baseline + random_source.gauss(0, baseline * 0.12))
        if random_source.random() < anomaly_probability:
            value *= random_source.uniform(3, 8)
        event["measurements"][field] = round(value, 2)

    event["measurements"]["temperature"] = round(19 + 8 * daylight + random_source.gauss(0, 1.5), 2)
    event["measurements"]["humidity"] = round(min(100.0, max(0.0, 65 - 25 * daylight + random_source.gauss(0, 5))), 2)
    validate_event(event)
    return event


def generate_events(sensor_id: str, count: int, *, start_at: datetime | None = None,
                    interval_seconds: int = 60, rng: random.Random | None = None,
                    anomaly_probability: float = 0.02,
                    location: dict[str, float] | None = None,
                    status: str = "active") -> list[dict[str, Any]]:
    """Génère une séquence de mesures horodatées à intervalle régulier."""
    if isinstance(count, bool) or not isinstance(count, int) or count < 0:
        raise ValueError("count doit être un entier positif ou nul.")
    if isinstance(interval_seconds, bool) or not isinstance(interval_seconds, int) or interval_seconds <= 0:
        raise ValueError("interval_seconds doit être un entier strictement positif.")
    beginning = _timestamp(start_at)
    random_source = _rng(rng)
    return [generate_event(sensor_id, beginning + timedelta(seconds=i * interval_seconds),
                           sequence=i, rng=random_source,
                           anomaly_probability=anomaly_probability,
                           location=location, status=status) for i in range(count)]


def validate_event(event: Any) -> None:
    """Valide le contrat d'un événement. Lève ValueError en cas d'écart."""
    if not isinstance(event, dict):
        raise ValueError("L'événement doit être un objet JSON.")
    if set(event) != EVENT_FIELDS:
        missing, extra = EVENT_FIELDS - set(event), set(event) - EVENT_FIELDS
        raise ValueError(f"Champs d'événement invalides (manquants={sorted(missing)}, supplémentaires={sorted(extra)}).")
    if not isinstance(event["sensor_id"], str) or not event["sensor_id"].strip():
        raise ValueError("sensor_id doit être une chaîne non vide.")
    if event["status"] not in ("active", "inactive"):
        raise ValueError("status doit valoir active ou inactive.")
    if event["status"] != "active":
        raise ValueError("Seuls les capteurs actifs peuvent émettre une mesure.")
    if not isinstance(event["timestamp"], str):
        raise ValueError("timestamp doit être une date ISO 8601.")
    try:
        timestamp = datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("timestamp doit être une date ISO 8601 valide.") from exc
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ValueError("timestamp doit inclure un fuseau horaire.")

    location = event["location"]
    if not isinstance(location, dict) or set(location) != {"lat", "lon"}:
        raise ValueError("location doit contenir uniquement lat et lon.")
    for field, minimum, maximum in (("lat", -90, 90), ("lon", -180, 180)):
        value = location[field]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f"location.{field} doit être un nombre fini.")
        if not minimum <= value <= maximum:
            raise ValueError(f"location.{field} est hors limites.")

    measurements = event["measurements"]
    if not isinstance(measurements, dict) or set(measurements) != MEASUREMENT_FIELDS:
        raise ValueError("measurements ne respecte pas le contrat des mesures.")
    for field in MEASUREMENT_FIELDS:
        value = measurements[field]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f"{field} doit être un nombre fini.")
        if field != "temperature" and value < 0:
            raise ValueError(f"{field} ne peut pas être négatif.")
    if measurements["humidity"] > 100:
        raise ValueError("humidity doit être comprise entre 0 et 100.")


def simulate_capture(sensors: Iterable[dict[str, Any]], events_per_sensor: int = 10, *,
                     interval_seconds: int = 60, start_at: datetime | None = None,
                     rng: random.Random | None = None) -> list[dict[str, Any]]:
    """Simule une capture multi-capteurs et renvoie les événements JSON prêts à publier."""
    random_source = _rng(rng)
    events: list[dict[str, Any]] = []
    for sensor in sensors:
        if not isinstance(sensor, dict) or sensor.get("status", "active") not in ("active", "inactive"):
            raise ValueError("Chaque capteur doit avoir un statut active ou inactive.")
        if sensor.get("status", "active") == "active":
            events.extend(generate_events(sensor.get("sensor_id"), events_per_sensor,
                                          start_at=start_at, interval_seconds=interval_seconds,
                                          rng=random_source,
                                          location={"lat": sensor.get("latitude", AGADIR_LATITUDE),
                                                    "lon": sensor.get("longitude", AGADIR_LONGITUDE)},
                                          status=sensor["status"]))
    return events


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Simule des événements IoT de qualité de l'air (JSON Lines).")
    parser.add_argument("--sensors", type=int, default=5, help="Nombre de capteurs (défaut : 5).")
    parser.add_argument("--events-per-sensor", type=int, default=10, help="Mesures par capteur (défaut : 10).")
    parser.add_argument("--interval-seconds", type=int, default=60, help="Intervalle entre mesures (défaut : 60).")
    args = parser.parse_args(argv)
    try:
        sensors = generate_sensors(args.sensors)
        events = simulate_capture(sensors, args.events_per_sensor, interval_seconds=args.interval_seconds)
    except ValueError as exc:
        parser.error(str(exc))
    for event in events:
        print(json.dumps(event, ensure_ascii=False, allow_nan=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
