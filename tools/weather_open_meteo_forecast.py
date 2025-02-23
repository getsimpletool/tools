from simpletool import SimpleTool, SimpleInputModel, Field, Dict, Any, Optional, Union, Sequence
from simpletool.types import TextContent, ErrorContent, ImageContent
import openmeteo_requests
import requests_cache
import retry_requests
import pandas as pd
import io
import base64
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import matplotlib.pyplot as plt


class InputModel(SimpleInputModel):
    """Input model for Open Meteo Weather Forecast."""
    city: Optional[str] = Field(
        description="Name of the city",
        max_length=60,
        default=None
    )
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
    days: Optional[int] = Field(
        default=7,
        description="Number of forecast days to retrieve (max 14)",
        ge=1,
        le=14
    )
    include_current: bool = Field(
        default=True,
        description="Include current weather conditions"
    )
    include_hourly: Optional[bool] = Field(
        default=False,
        description="Include hourly forecast data"
    )


class WeatherOpenMeteoForecastTool(SimpleTool):
    name = "weather_open_meteo_forecast"
    description = """Get weather forecast using Open Meteo API.
    Can be searched by city name or latitude/longitude.
    Supports current and hourly weather data.
    """
    input_model = InputModel

    OPEN_METEO_API_BASE = "https://api.open-meteo.com/v1/forecast"

    @classmethod
    def _geocode_city(cls, city: str) -> tuple[float, float]:
        """
        Geocode a city name to latitude and longitude.

        Args:
            city (str): Name of the city

        Returns:
            tuple[float, float]: Latitude and longitude of the city

        Raises:
            ValueError: If city cannot be geocoded
        """
        geolocator = Nominatim(user_agent="WeatherApp/1.0")
        try:
            location = geolocator.geocode(city, addressdetails=True)

            if not location:
                raise ValueError(f"Could not find location for city: {city}")

            # Validate latitude and longitude are numeric
            try:
                lat = float(location.latitude)      # type: ignore
                lon = float(location.longitude)     # type: ignore
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Invalid coordinates for city: {city}") from exc

            return lat, lon

        except (GeocoderTimedOut, GeocoderServiceError) as e:
            raise ValueError(f"Geocoding error: {str(e)}") from e

    async def run(self, arguments: Dict[str, Any]) -> Sequence[Union[TextContent, ErrorContent, ImageContent]]:
        """
        Run the Open Meteo weather forecast tool.

        Args:
            arguments (Dict[str, Any]): Input arguments for the tool

        Returns:
            list[Union[TextContent, ErrorContent, ImageContent]]: Weather forecast results
        """
        try:
            # Determine latitude and longitude
            if arguments.get('city'):
                lat, lon = self._geocode_city(arguments['city'])
            elif arguments.get('latitude') and arguments.get('longitude'):
                lat, lon = arguments['latitude'], arguments['longitude']
            else:
                return [ErrorContent(
                    code=400,
                    message="Either city or latitude/longitude must be provided"
                )]

            # Setup the Open-Meteo API client with cache and retry on error
            cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
            retry_session = retry_requests.retry(cache_session, retries=5, backoff_factor=0.2)
            openmeteo = openmeteo_requests.Client(session=retry_session)

            # Prepare API parameters
            params = {
                "latitude": lat,
                "longitude": lon,
                "forecast_days": arguments.get('days', 7)
            }

            # Add optional parameters
            hourly_params = []
            current_params = []

            if arguments.get('include_hourly', False):
                hourly_params = [
                    "temperature_2m",
                    "relative_humidity_2m",
                    "wind_speed_10m"
                ]
                params["hourly"] = hourly_params

            if arguments.get('include_current', True):
                current_params = [
                    "temperature_2m",
                    "wind_speed_10m",
                    "relative_humidity_2m"
                ]
                params["current"] = current_params

            # Make API request
            responses = openmeteo.weather_api(self.OPEN_METEO_API_BASE, params=params)

            # Process first location
            response = responses[0]

            # Prepare result dictionary
            result_data = {
                "coordinates": {
                    "latitude": response.Latitude(),
                    "longitude": response.Longitude(),
                    "elevation": response.Elevation()
                },
                "timezone": {
                    "name": response.Timezone(),
                    "abbreviation": response.TimezoneAbbreviation(),
                    "utc_offset_seconds": response.UtcOffsetSeconds()
                }
            }

            image_base64 = None
            # Process hourly data if requested
            if hourly_params:
                hourly = response.Hourly()
                if hourly is not None:
                    # Create datetime index
                    date_index = pd.date_range(
                        start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
                        end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
                        freq=pd.Timedelta(seconds=hourly.Interval()),
                        inclusive="left"
                    )

                    # Prepare data dictionary for DataFrame
                    hourly_data = {}
                    hourly_data['date'] = date_index

                    # Add each hourly parameter
                    for i, param in enumerate(hourly_params):
                        hourly_data[param] = hourly.Variables(i).ValuesAsNumpy().tolist()

                    # Create DataFrame
                    hourly_df = pd.DataFrame(data=hourly_data)
                    result_data["hourly"] = hourly_df.to_dict(orient='records')

                    # Generate graph
                    hourly_df.plot(x='date', y=['temperature_2m', 'relative_humidity_2m'], figsize=(12, 6))
                    plt.title(f"Hourly Weather Forecast for {arguments.get('city', f'Lat {lat}, Lon {lon}')}")
                    plt.xlabel('Date')
                    plt.xticks(rotation=45)
                    plt.tight_layout()

                    # Save plot to a base64 encoded image
                    buffer = io.BytesIO()
                    plt.savefig(buffer, format='png')
                    buffer.seek(0)
                    image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
                    plt.close()

            # Process current data if requested
            if current_params:
                current = response.Current()
                current_data = {}
                for i, param in enumerate(current_params):
                    current_data[param] = float(current.Variables(i).Value())

                result_data["current"] = current_data

            # Prepare return values
            return_values: Sequence = [TextContent(text=str(result_data))]

            # Add graph if generated
            if 'image_base64' in locals() and image_base64:
                return_values.append(ImageContent(
                    data=image_base64,
                    mime_type='image/png',
                    description='Hourly Weather Forecast Graph'
                ))

            return return_values

        except Exception as e:
            return [ErrorContent(code=500, message=f"Weather retrieval error: {str(e)}")]
