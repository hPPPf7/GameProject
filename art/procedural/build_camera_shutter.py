"""A dry, bright mechanical shutter: two short clicks, without bass or reverb."""
from array import array
import math
from pathlib import Path
import random
import sys
import wave


def build_shutter():
    rate = 44100
    rng = random.Random(501)
    samples = []
    previous_noise = 0.0
    for index in range(round(rate * .14)):
        time = index / rate
        noise = rng.uniform(-1, 1)
        bright = noise - .92 * previous_noise
        previous_noise = noise
        value = 0.0
        for onset, level, decay in ((.0, 1.0, .0045), (.009, .24, .003), (.052, .85, .006)):
            age = time - onset
            if age >= 0:
                envelope = min(1, age / .00025) * math.exp(-age / decay)
                snap = bright * .8 + math.sin(math.tau * 3900 * age) * .16
                value += level * envelope * snap
        samples.append(value)
    peak = max(abs(value) for value in samples)
    pcm = array('h', (round(value / peak * .88 * 32767) for value in samples))
    if sys.byteorder != 'little':
        pcm.byteswap()
    output = Path(__file__).resolve().parents[2] / 'assets/sounds/sfx/camera_shutter.wav'
    with wave.open(str(output), 'wb') as stream:
        stream.setparams((1, 2, rate, 0, 'NONE', 'not compressed'))
        stream.writeframes(pcm.tobytes())
    print(output)


if __name__ == '__main__':
    build_shutter()
