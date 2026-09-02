from hashutil import hash_histogram, hash_image
from pipeline import compute_histogram, convolve_image, normalize_image, resize_image
from serialize import dump_image_meta, load_image_meta


def main():
    """Run convolution, resize, histogram, and json metadata dump."""
    pixels = [[0.0, 1.0], [1.0, 0.0]]
    kernel = [[0.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 0.0]]
    conv = convolve_image(pixels, kernel)
    scaled = resize_image(conv, 1)
    norm = normalize_image(scaled)
    hist = compute_histogram(norm)
    digest = hash_image(norm)
    hist_digest = hash_histogram(hist)
    dumped = dump_image_meta(norm, digest)
    loaded = load_image_meta(dumped)
    return {"digest": digest, "hist": hist_digest, "meta": loaded}


if __name__ == "__main__":
    main()
