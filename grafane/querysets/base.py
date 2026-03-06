"""Base query set interface for Grafane.

This module defines the abstract base class that both InfluxQL and Flux
query builders must implement to maintain API parity.
"""

from abc import ABC, abstractmethod
from typing import Any, Self


class BaseQuerySet(ABC):
    """Abstract base class for query builders.

    This defines the interface that all query set implementations must follow
    to ensure API parity between InfluxDB v1 (InfluxQL) and v2 (Flux).
    """

    @abstractmethod
    def reset(self) -> None:
        """Reset all query state to defaults."""
        pass

    @abstractmethod
    def rebuild(self) -> None:
        """Rebuild the query string from current state."""
        pass

    @property
    @abstractmethod
    def query(self) -> str:
        """Return the built query string."""
        pass

    @abstractmethod
    def select(self, fields: Any = None, aggregation: Any = None) -> Self:
        """Set fields and optional aggregations.

        Args:
            fields: Field name(s) to select
            aggregation: Aggregation function(s) to apply

        Returns:
            Self for method chaining
        """
        pass

    @abstractmethod
    def filter_by(self, tag: str, operator: str, value: str) -> Self:
        """Add a filter condition.

        Args:
            tag: Tag name to filter on
            operator: Comparison operator (=, !=, <, >, etc.)
            value: Value to compare against

        Returns:
            Self for method chaining
        """
        pass

    @abstractmethod
    def filter_time_range(self, r: Any) -> Self:
        """Filter results by time range.

        Args:
            r: Tuple/list of (start, end) datetime objects

        Returns:
            Self for method chaining
        """
        pass

    @abstractmethod
    def time_block(self, block: str) -> Self:
        """Group results by time interval.

        Args:
            block: Time interval (e.g., '1h', '5m', '1d')

        Returns:
            Self for method chaining
        """
        pass

    @abstractmethod
    def group_by(self, group: Any) -> Self:
        """Group results by tag(s).

        Args:
            group: Tag name(s) to group by

        Returns:
            Self for method chaining
        """
        pass

    @abstractmethod
    def fill_with(self, fill: str | bool = False) -> Self:
        """Fill missing values in the result set.

        Args:
            fill: Fill strategy ('none', 'null', '0', 'previous', 'linear')
                  or False to disable

        Returns:
            Self for method chaining
        """
        pass

    @abstractmethod
    def filter_value_in(self, tag: str, values: list) -> Self:
        """Filter where tag value is in a list of values.

        Args:
            tag: Tag name to filter on
            values: List of acceptable values

        Returns:
            Self for method chaining
        """
        pass

    @abstractmethod
    def parse_results(self, raw_results: Any) -> list:
        """Parse raw database results into a list of dicts.

        Args:
            raw_results: Raw response from InfluxDB client

        Returns:
            List of result dictionaries with consistent format
        """
        pass
