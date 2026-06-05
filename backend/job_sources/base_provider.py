from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseJobProvider(ABC):
    @abstractmethod
    async def fetch_jobs(self, keywords: str, location: str, limit: int = 15) -> List[Dict[str, Any]]:
        """
        Fetches jobs from the provider.
        Returns a list of dictionaries with standard keys:
        - title
        - company
        - location
        - salary (string like '$80,000' or 'Not Specified')
        - description
        - skills_required (list of strings)
        - url
        """
        pass
