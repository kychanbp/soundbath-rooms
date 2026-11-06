"""Where each room sits on the gallery. Each room is built with its door at local (0,0) and its body toward local +Y."""
import numpy as np
HALL_W = 3.6
def rot(deg, x, y):
    c, s = np.cos(np.radians(deg)), np.sin(np.radians(deg))
    return np.array([[c, -s, 0, x], [s, c, 0, y], [0, 0, 1, 0], [0, 0, 0, 1.]])
PLACE = dict(
    himalayan=rot(90, -30, -12), crystal=rot(-90, 30, -12),
    gong=rot(90, -34, 26), rain=rot(-90, 34, 26),
    rin=rot(0, -14, 58), strings=rot(0, 16, 58),
    cave=rot(0, 0, 92), hall=rot(0, 0, 0),
)
