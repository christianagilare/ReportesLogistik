import requests
import logging
from typing import List, Dict, Any, Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)

class TrackingTimeAPIError(Exception):
    """Exception raised for errors in the TrackingTime API."""
    pass

class TrackingTimeClient:
    def __init__(self, token: str, base_url: str):
        self.token = token
        self.base_url = base_url
        self.headers = {
            "Authorization": self.token
        }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(requests.exceptions.RequestException),
        reraise=True
    )
    def _make_request(self, method: str, endpoint: str, params: Optional[Dict] = None, headers: Optional[Dict] = None) -> requests.Response:
        url = f"{self.base_url}{endpoint}"
        req_headers = {**self.headers, **(headers or {})}
        
        # Ocultar query params por seguridad de auth si es necesario o logging basico
        logger.info(f"Making {method} request to {url}")
        
        response = requests.request(method, url, headers=req_headers, params=params)
        
        if response.status_code in (429, 500, 502, 503, 504):
            response.raise_for_status() # Trigger retry mechanism
            
        if not response.ok:
            logger.error(f"TrackingTime API error: {response.status_code} - {response.text}")
            response.raise_for_status()
            
        return response

    def get_users(self) -> List[Dict[str, Any]]:
        """Extrae la lista de todos los usuarios validos."""
        endpoint = "/users"
        headers = {"Content-Type": "application/json"}
        
        response = self._make_request("GET", endpoint, headers=headers)
        data = response.json()
        
        if data.get("response", {}).get("status") != 200:
            raise TrackingTimeAPIError(f"Error fetching users: {data.get('response', {}).get('message')}")
            
        return data.get("data", [])
        
    def export_events(self, user_id: int, date_from: str, date_to: str) -> str:
        """Exporta eventos del usuario en formato CSV y retorna el string crudo."""
        endpoint = "/events/export"
        params = {
            "from": date_from,
            "to": date_to,
            "type": "user",
            "id": user_id
        }
        headers = {"Accept": "text/csv"}
        
        response = self._make_request("GET", endpoint, params=params, headers=headers)
        return response.text
