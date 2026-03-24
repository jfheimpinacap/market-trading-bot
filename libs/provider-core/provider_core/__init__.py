"""Shared provider read-only interfaces."""

from .client import ReadOnlyProviderClient
from .types import NormalizedMarketRecord

__all__ = ['ReadOnlyProviderClient', 'NormalizedMarketRecord']
