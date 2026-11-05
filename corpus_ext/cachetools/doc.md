# cachetools

[![Latest PyPI version](https://img.shields.io/pypi/v/cachetools)](https://pypi.org/project/cachetools/)

[![CI build status](https://img.shields.io/github/actions/workflow/status/tkem/cachetools/ci.yml)](https://github.com/tkem/cachetools/actions/workflows/ci.yml)

[![Documentation build status](https://img.shields.io/readthedocs/cachetools)](https://cachetools.readthedocs.io/)

[![Test coverage](https://img.shields.io/codecov/c/github/tkem/cachetools/master.svg)](https://codecov.io/gh/tkem/cachetools)

[![Libraries.io SourceRank](https://img.shields.io/librariesio/sourcerank/pypi/cachetools)](https://libraries.io/pypi/cachetools)

[![License](https://img.shields.io/github/license/tkem/cachetools)](https://raw.github.com/tkem/cachetools/master/LICENSE)

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

This module provides various memoizing collections and decorators,
including variants of the Python Standard Library's
[@lru_cache](https://docs.python.org/3/library/functools.html#functools.lru_cache)
function decorator.

``` python
from cachetools import cached, LRUCache, TTLCache

# speed up calculating Fibonacci numbers with dynamic programming
@cached(cache={})
def fib(n):
    return n if n < 2 else fib(n - 1) + fib(n - 2)

# cache least recently used Python Enhancement Proposals
@cached(cache=LRUCache(maxsize=32))
def get_pep(num):
    url = 'http://www.python.org/dev/peps/pep-%04d/' % num
    with urllib.request.urlopen(url) as s:
        return s.read()

# cache weather data for no longer than ten minutes
@cached(cache=TTLCache(maxsize=1024, ttl=600))
def get_weather(place):
    return owm.weather_at_place(place).get_weather()
```

For the purpose of this module, a *cache* is a
[mutable](https://docs.python.org/dev/glossary.html#term-mutable)
[mapping](https://docs.python.org/dev/glossary.html#term-mapping) of a
fixed maximum size. When the cache is full, i.e. by adding another item
the cache would exceed its maximum size, the cache must choose which
item(s) to discard based on a suitable [cache
algorithm](https://en.wikipedia.org/wiki/Cache_algorithms).

This module provides multiple cache classes based on different cache
algorithms, as well as decorators for easily memoizing function and
method calls.

## Installation

cachetools is available from
[PyPI](https://pypi.org/project/cachetools/) and can be installed by
running:

    pip install cachetools

Typing stubs for this package are provided by
[typeshed](https://github.com/python/typeshed/) and can be installed by
running:

    pip install types-cachetools

## Project Resources

- [Documentation](https://cachetools.readthedocs.io/)
- [Issue tracker](https://github.com/tkem/cachetools/issues/)
- [Source code](https://github.com/tkem/cachetools/)
- [Change
  log](https://github.com/tkem/cachetools/blob/master/CHANGELOG.rst)

## Related Projects

- [asyncache](https://pypi.org/project/asyncache/): Helpers to use
  cachetools with async functions
- [cacheing](https://github.com/breid48/cacheing): Pure Python Cacheing
  Library
- [CacheToolsUtils](https://pypi.org/project/CacheToolsUtils/):
  Cachetools Utilities
- [kids.cache](https://pypi.org/project/kids.cache/): Kids caching
  library
- [shelved-cache](https://pypi.org/project/shelved-cache/): Persistent
  cache for Python cachetools

## License

Copyright (c) 2014-2024 Thomas Kemmer.

Licensed under the [MIT
License](https://raw.github.com/tkem/cachetools/master/LICENSE).
