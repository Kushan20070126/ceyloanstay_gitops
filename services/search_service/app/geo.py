import hashlib
import math
from typing import Tuple

from .models import PropertyAd

# District center coordinates in Sri Lanka.
DISTRICT_COORDS: dict[str, tuple[float, float]] = {
    "colombo": (6.9271, 79.8612),
    "gampaha": (7.0840, 79.9990),
    "kalutara": (6.5854, 79.9607),
    "kandy": (7.2906, 80.6337),
    "matale": (7.4675, 80.6234),
    "nuwara eliya": (6.9497, 80.7891),
    "galle": (6.0535, 80.2210),
    "matara": (5.9549, 80.5550),
    "hambantota": (6.1241, 81.1185),
    "jaffna": (9.6615, 80.0255),
    "kilinochchi": (9.3803, 80.4037),
    "mannar": (8.9810, 79.9042),
    "vavuniya": (8.7514, 80.4971),
    "mullaitivu": (9.2667, 80.8167),
    "batticaloa": (7.7170, 81.7000),
    "ampara": (7.2965, 81.6820),
    "trincomalee": (8.5874, 81.2152),
    "kurunegala": (7.4863, 80.3647),
    "puttalam": (8.0362, 79.8283),
    "anuradhapura": (8.3114, 80.4037),
    "polonnaruwa": (7.9403, 81.0188),
    "badulla": (6.9934, 81.0550),
    "monaragala": (6.8725, 81.3507),
    "ratnapura": (6.6828, 80.3992),
    "kegalle": (7.2513, 80.3464),
}

DEFAULT_CENTER = (7.8731, 80.7718)


def _stable_offset(seed: str) -> tuple[float, float]:
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    a = int(digest[:8], 16)
    b = int(digest[8:16], 16)
    lat_offset = ((a % 1000) / 1000.0 - 0.5) * 0.04
    lon_offset = ((b % 1000) / 1000.0 - 0.5) * 0.04
    return lat_offset, lon_offset


def ad_coordinates(ad: PropertyAd) -> tuple[float, float]:
    
    district_key = (ad.district or "").strip().lower()
    base_lat, base_lon = DISTRICT_COORDS.get(district_key, DEFAULT_CENTER)
    seed = f"{ad.id}:{ad.address or ''}:{ad.district or ''}"
    d_lat, d_lon = _stable_offset(seed)
    return round(base_lat + d_lat, 6), round(base_lon + d_lon, 6)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radius * c
