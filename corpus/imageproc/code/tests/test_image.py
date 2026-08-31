from hashutil import hash_histogram, hash_image
from pipeline import compute_histogram, convolve_image, normalize_image, resize_image
from serialize import dump_image_meta, load_image_meta


def test_convolve_image():
    convolve_image([[1.0]], [[1.0]])


def test_resize_image():
    resize_image([[1.0]], 2)


def test_normalize_image():
    normalize_image([[0.0, 2.0]])


def test_compute_histogram():
    compute_histogram([[0.0, 1.0]])


def test_hash_image():
    hash_image([[0.0, 1.0]])


def test_hash_histogram():
    hash_histogram([1, 2, 3])


def test_dump_image_meta():
    dump_image_meta([[0.0]], "abc")


def test_load_image_meta():
    load_image_meta('{"height": 1, "width": 1, "digest": "abc"}')
