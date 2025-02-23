from simpletool import SimpleTool, SimpleInputModel, Field, Dict, Any
from simpletool.types import TextContent
import httpx
from typing import Optional
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError


class InputModel(SimpleInputModel):
    """Input model for US Current Weather."""
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


class WeatherUSCurrentTool(SimpleTool):
    name = "weather_us_current"
    description = """Get the current weather for a location in the United States.
    Can be searched by city name or latitude/longitude.
    Only for the United States (USA).
    """
    input_model = InputModel

    NWS_API_BASE: str = "https://api.weather.gov"
    USER_AGENT: str = "WeatherApp/1.0"

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

    async def run(self, arguments: Dict[str, Any]) -> list[TextContent]:
        try:
            arg = InputModel(**arguments)

            # If city is provided but lat/lon are not, geocode the city
            if arg.city and (arg.latitude is None or arg.longitude is None):
                arg.latitude, arg.longitude = self._geocode_city(arg.city)

            # Validate that we have coordinates
            if arg.latitude is None or arg.longitude is None:
                return [TextContent(type="text", text="Error: Either city or latitude/longitude must be provided")]

            async with httpx.AsyncClient(follow_redirects=True) as client:
                # First get the forecast grid endpoint
                points_url = f"{self.NWS_API_BASE}/points/{arg.latitude},{arg.longitude}"
                headers = {"User-Agent": self.USER_AGENT}

                response = await client.get(points_url, headers=headers)
                response.raise_for_status()

                data = response.json()
                forecast_url = data["properties"]["forecast"]

                # Now get the actual forecast
                response = await client.get(forecast_url, headers=headers)
                response.raise_for_status()

                forecast_data = response.json()
                current_period = forecast_data["properties"]["periods"][0]

                # Format the current weather information
                # Convert Fahrenheit to Celsius if original temperature is in Fahrenheit
                temp_f = current_period['temperature']
                temp_unit = current_period['temperatureUnit']
                temp_c = round((temp_f - 32) * 5 / 9, 1) if temp_unit == 'F' else None

                weather_info = (
                    f"Location: {arg.city or ''} ({arg.latitude}, {arg.longitude})\n"
                    f"Temperature: {temp_f}°{temp_unit} "
                    f"{f'({temp_c}°C)' if temp_c is not None else ''}\n"
                    f"Wind: {current_period['windSpeed']} {current_period['windDirection']}\n"
                    f"Forecast: {current_period['shortForecast']}\n"
                    f"Detailed Forecast: {current_period['detailedForecast']}"
                )

                return [TextContent(type="text", text=weather_info)]

        except httpx.HTTPError as e:
            return [TextContent(type="text", text=f"HTTP Error: {str(e)}")]
        except KeyError as e:
            return [TextContent(type="text", text=f"Data parsing error: {str(e)}")]
        except ValueError as e:
            return [TextContent(type="text", text=f"Geocoding error: {str(e)}")]
        except Exception as e:
            return [TextContent(type="text", text=f"Unexpected error: {str(e)}")]
