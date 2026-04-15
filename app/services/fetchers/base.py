from __future__ import annotations

import abc
from typing import List

from app.schemas.job import JobListing


class BaseJobFetcher(abc.ABC):
    @abc.abstractmethod
    def fetch(self, lookback_hours: int = 24) -> List[JobListing]:
        ...
