"""Shared utilities used across multiple modules to break dependency cycles."""

import pandas as _pd

# BL-42: com pyarrow instalado, o dtype str do pandas 3 usa armazenamento pyarrow e a regex
# roda no RE2, onde \w, \s e \b sao so ASCII ('^\w+$' nao casa palavra com acento, cedilha,
# til, ene ou eszett). Armazenamento python deixa toda busca no re do Python, com ou sem
# pyarrow. Os modulos que criam DataFrames (loader, extrator, armazenamento) importam shared antes.
_pd.set_option("mode.string_storage", "python")
