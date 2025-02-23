from simpletool import SimpleTool, SimpleInputModel, Field, Dict, Any
from simpletool.types import TextContent
import httpx


class InputModel(SimpleInputModel):
    """Input model for US Weather Alerts."""
    state: str = Field(
        description="Two-letter state code (e.g., 'CA', 'NY')",
        min_length=2,
        max_length=2,
        pattern=r'^[A-Z]{2}$'
    )


class WeatherUSAlertsTool(SimpleTool):
    name = "weather_us_alerts"
    description = '''
    Retrieves current weather alerts for a specified US location.
    Returns active severe weather warnings, watches, and advisories.
    Only for the United States (USA).
    '''
    input_model = InputModel

    NWS_API_BASE: str = "https://api.weather.gov"
    USER_AGENT: str = "WeatherApp/1.0 (contact@example.com)"

    async def _make_nws_request(self, url: str) -> dict:
        headers = {"User-Agent": self.USER_AGENT}
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()

    async def run(self, arguments: Dict[str, Any]) -> list[TextContent]:
        # Validation and parsing of input arguments
        arg = InputModel(**arguments)

        try:
            state = arg.state
            url = f"{self.NWS_API_BASE}/alerts/active?area={state}"
            data = await self._make_nws_request(url)

            alerts = []
            for feature in data.get("features", []):
                props = feature.get("properties", {})
                alerts.append({
                    "event": props.get("event"),
                    "area": props.get("areaDesc"),
                    "severity": props.get("severity"),
                    "status": props.get("status"),
                    "description": props.get("description")
                })

            if not alerts:
                return [TextContent(type="text", text=f"No active weather alerts for {state}")]

            alert_texts = []
            for alert in alerts:
                alert_text = (
                    f"Event: {alert['event']}\n"
                    f"Area: {alert['area']}\n"
                    f"Severity: {alert['severity']}\n"
                    f"Status: {alert['status']}\n"
                    f"Description: {alert['description']}\n"
                    "---"
                )
                alert_texts.append(alert_text)

            return [TextContent(type="text", text="\n".join(alert_texts))]

        except httpx.HTTPError as e:
            return [TextContent(type="text", text=f"HTTP Error: {str(e)}")]
        except Exception as e:
            return [TextContent(type="text", text=f"Unexpected error: {str(e)}")]
