import math


def round_to_nearest(value, base):
    return base * round(value / base)


def floor_to_nearest(value, base):
    return base * math.floor(value / base)


def ceil_to_nearest(value, base):
    return base * math.ceil(value / base)


def distance(point1, point2):
    return math.sqrt((point1.x() - point2.x()) ** 2 + (point1.y() - point2.y()) ** 2)


def sign(n):
    return -1 if n < 0 else 1


def mabs(n):
    return sign(n) * n