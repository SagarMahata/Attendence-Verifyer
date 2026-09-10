import math


def haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two lat/lon points, in metres."""
    R = 6_371_000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def euclidean_distance(a, b) -> float:
    """Distance between two equal-length face descriptor vectors."""
    if len(a) != len(b):
        raise ValueError("Descriptor length mismatch")
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))
