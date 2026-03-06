import requests
import logging
from typing import List, Dict, Any, Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)

class AzureDevOpsAPIError(Exception):
    """Exception raised for errors in the Azure DevOps API."""
    pass

class AzureDevOpsClient:
    def __init__(self, token: str, base_url: str, org: str, project_id: str):
        self.token = token
        self.base_url = base_url
        self.org = org
        self.project_id = project_id
        self.headers = {
            "Authorization": self.token,
            "Content-Type": "application/json"
        }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(requests.exceptions.RequestException),
        reraise=True
    )
    def _make_request(self, method: str, url: str, json_data: Optional[Dict] = None) -> requests.Response:
        logger.info(f"Making {method} request to {url}")
        
        response = requests.request(method, url, headers=self.headers, json=json_data)
        
        if response.status_code in (429, 500, 502, 503, 504):
            response.raise_for_status()
            
        if not response.ok:
            logger.error(f"ADO API error: {response.status_code} - {response.text}")
            response.raise_for_status()
            
        return response

    def get_query_wiql_url(self, query_id: str) -> str:
        url = f"{self.base_url}/{self.org}/{self.project_id}/_apis/wit/queries/{query_id}?api-version=7.0"
        response = self._make_request("GET", url)
        data = response.json()
        return data["_links"]["wiql"]["href"]

    def execute_wiql(self, wiql_url: str) -> List[int]:
        response = self._make_request("GET", wiql_url)
        data = response.json()
        return [item["id"] for item in data.get("workItems", [])]

    def get_work_items_batch(self, ids: List[int], fields: List[str]) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/{self.org}/{self.project_id}/_apis/wit/workitemsbatch?api-version=7.0"
        payload = {
            "ids": ids,
            "fields": fields
        }
        response = self._make_request("POST", url, json_data=payload)
        data = response.json()
        return data.get("value", [])
