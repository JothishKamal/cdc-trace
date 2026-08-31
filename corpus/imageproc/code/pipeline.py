def convolve_image(pixels, kernel):
    """Convolve a numeric image with a square kernel.

    Out-of-range taps clamp to the border so the output has the same
    shape as the input.
    """
    if not pixels:
        return []
    height = len(pixels)
    width = len(pixels[0])
    k = len(kernel)
    origin = k // 2
    out = []
    for y in range(height):
        row = []
        for x in range(width):
            acc = 0.0
            for i in range(k):
                for j in range(k):
                    yy = y + i - origin
                    xx = x + j - origin
                    if yy < 0:
                        yy = 0
                    elif yy >= height:
                        yy = height - 1
                    if xx < 0:
                        xx = 0
                    elif xx >= width:
                        xx = width - 1
                    acc += pixels[yy][xx] * kernel[i][j]
            row.append(acc)
        out.append(row)
    return out


def resize_image(pixels, scale):
    """Return a scaled image by integer nearest-neighbour replication."""
    if scale < 1:
        raise ValueError("scale must be at least 1")
    out = []
    for row in pixels:
        expanded = []
        for cell in row:
            for _ in range(scale):
                expanded.append(cell)
        for _ in range(scale):
            out.append(list(expanded))
    return out


def normalize_image(pixels):
    """Return normalized pixels in the unit interval.

    A flat image is left unchanged because the span would be zero.
    """
    flat = []
    for row in pixels:
        for cell in row:
            flat.append(cell)
    if not flat:
        return pixels
    lo = min(flat)
    hi = max(flat)
    span = hi - lo
    if span == 0:
        return pixels
    out = []
    for row in pixels:
        out.append([(cell - lo) / span for cell in row])
    return out


def compute_histogram(pixels, bins=8):
    """Compute a histogram of unit-interval pixels."""
    if bins < 1:
        raise ValueError("bins must be positive")
    counts = [0] * bins
    for row in pixels:
        for cell in row:
            idx = int(cell * (bins - 1))
            if idx < 0:
                idx = 0
            elif idx >= bins:
                idx = bins - 1
            counts[idx] += 1
    return counts
