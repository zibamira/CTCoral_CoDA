"""
:mod:`cora.data_provider`

This package contains small handlers and wrappers for loading 
data from different sources. 
"""


from .base import DataProvider
from .amira import AmiraDataProvider
from .filesystem import FilesystemDataProvider
from .random import RandomDataProvider