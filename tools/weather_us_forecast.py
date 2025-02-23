from simpletool import SimpleTool, SimpleInputModel, Field, Dict, Any, Optional, Union
from simpletool.types import TextContent, ErrorContent
import httpx
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError


class InputModel(SimpleInputModel):
    """Input model for US Weather Forecast."""
    latitude: Optional[float] = Field(
        description="Latitude of the location",
        ge=-90,
        le=90,
        default=None
    )
    longitude: Optional[float] = Field(
        description="Longitude of the location",
        ge=-180,
        le=180,
        default=None
    )
    city: Optional[str] = Field(
        description="Name of the city in the United States",
        max_length=60,
        default=None
    )
    days: Optional[int] = Field(
        default=7,
        description="Number of forecast days to retrieve (max 14)",
        ge=1,
        le=14
    )


class WeatherUSForecastTool(SimpleTool):
    name = "weather_us_forecast"
    description = """Get weather forecast for a United States location.
    Can be searched by city name or latitude/longitude.
    Only for the United States (USA).
    """
    input_model = InputModel

    NWS_API_BASE = "https://api.weather.gov"
    USER_AGENT = "WeatherApp/1.0 (contact@example.com)"

    @classmethod
    def _geocode_city(cls, city: str) -> tuple[float, float]:
        """
        Geocode a city name to latitude and longitude.

        Args:
            city (str): Name of the city in the United States

        Returns:
            tuple[float, float]: Latitude and longitude of the city

        Raises:
            ValueError: If city cannot be geocoded or is outside the US
        """
        geolocator = Nominatim(user_agent=cls.USER_AGENT)
        try:
            location = geolocator.geocode(f"{city}, USA", addressdetails=True)

            if not location:
                raise ValueError(f"Could not find location for city: {city}")

            # Ensure location is not a coroutine and has expected attributes
            if not hasattr(location, 'latitude') or not hasattr(location, 'longitude'):
                raise ValueError(f"Invalid location data for city: {city}")

            # Safely access raw attribute with type checking
            raw_data = getattr(location, 'raw', {})
            if not isinstance(raw_data, dict):
                raise ValueError(f"Invalid location metadata for city: {city}")

            # Additional check to ensure it's in the US
            address = raw_data.get('address', {})
            if not isinstance(address, dict) or address.get('country_code') != 'us':
                raise ValueError(f"Location {city} is not in the United States")

            # Validate latitude and longitude are numeric
            try:
                lat = float(location.latitude)      # type: ignore
                lon = float(location.longitude)     # type: ignore
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Invalid coordinates for city: {city}") from exc

            return lat, lon

        except (GeocoderTimedOut, GeocoderServiceError) as e:
            raise ValueError(f"Geocoding error: {str(e)}") from e

    async def _make_nws_request(self, url: str) -> dict:
        headers = {"User-Agent": self.USER_AGENT}
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()

    async def run(self, arguments: Dict[str, Any]) -> list[Union[TextContent, ErrorContent]]:
        try:
            arg = InputModel(**arguments)
        except ValueError as e:
            return [ErrorContent(code=400, message=str(e))]

        try:
            # If city is provided but lat/lon are not, geocode the city
            if arg.city and (arg.latitude is None or arg.longitude is None):
                arg.latitude, arg.longitude = self._geocode_city(arg.city)
        except ValueError as e:
            if arg.latitude is None or arg.longitude is None:
                return [ErrorContent(code=400, message=str(e)), TextContent(type="text", text="Error: Either city or latitude/longitude must be provided")]

        except GeocoderTimedOut:
            return [TextContent(type="text", text="Error: Geocoding timed out")]

        except GeocoderServiceError:
            return [TextContent(type="text", text="Error: Geocoding service error")]

        try:
            days_to_retrieve = arg.days or 7

            # First get the forecast grid endpoint
            points_url = f"{self.NWS_API_BASE}/points/{arg.latitude},{arg.longitude}"
            points_data = await self._make_nws_request(points_url)

            # Get the forecast URL from the points response
            forecast_url = points_data["properties"]["forecast"]
            forecast_data = await self._make_nws_request(forecast_url)

            # Extract relevant forecast information
            periods = forecast_data["properties"]["periods"]

            # Limit forecast to specified number of days
            periods = periods[:min(days_to_retrieve * 2, len(periods))]  # Each day has day and night periods

            forecast_texts = []
            for period in periods:
                # Convert Fahrenheit to Celsius if original temperature is in Fahrenheit
                temp_f = period['temperature']
                temp_unit = period['temperatureUnit']
                temp_c = round((temp_f - 32) * 5 / 9, 1) if temp_unit == 'F' else None

                forecast_text = (
                    f"Location: {arg.city or ''}({arg.latitude}, {arg.longitude})\n"
                    f"{period['name']}: "
                    f"{temp_f}°{temp_unit} "
                    f"{f'({temp_c}°C)' if temp_c is not None else ''} {period['shortForecast']}\n"
                    f"Wind: {period['windSpeed']} {period['windDirection']}\n"
                    f"Detailed: {period['detailedForecast']}\n"
                    "---"
                )
                forecast_texts.append(forecast_text)

            return [TextContent(type="text", text="\n".join(forecast_texts))]

        except httpx.HTTPError as e:
            return [TextContent(type="text", text=f"HTTP Error: {str(e)}")]
        except KeyError as e:
            return [TextContent(type="text", text=f"Data parsing error: {str(e)}")]
        except ValueError as e:
            return [TextContent(type="text", text=f"Geocoding error: {str(e)}")]
        except Exception as e:
            return [TextContent(type="text", text=f"Unexpected error: {str(e)}")]
