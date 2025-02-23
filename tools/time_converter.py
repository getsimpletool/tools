"""
name: Time Converter
minimum_python_version: "3.10"
description: "Converts a date and time to a specific timezone."
version: "1.0.0"
author: "Artur Zdolinski"
requirements: geopy,pydantic,pytz,simpletool>=0.0.13,timezonefinder
"""

import datetime
import pytz
from simpletool import SimpleTool, SimpleInputModel, Field, Dict, Any, List
from simpletool.types import TextContent
from timezonefinder import TimezoneFinder
from geopy.geocoders import Nominatim


class InputModel(SimpleInputModel):
    """Input model for time conversion."""
    date_time_str: str = Field(
        description="The time to convert. Can be 'NOW' or a specific date and time.",
        default="NOW",
        examples=["2022-03-01 12:00:00", "NOW"]
    )
    from_timezone: str = Field(
        default="UTC",
        description="Source timezone (default: UTC)",
        examples=["America/New_York", "Asia/Tokyo", "Europe/London"]
    )
    to_timezone: str = Field(
        default="UTC",
        description="Target timezone (default: UTC)",
        examples=["America/New_York", "Asia/Tokyo", "Europe/London"]
    )


class TimeConverterTool(SimpleTool):
    name = "time_converter"
    description = '''
    Converts time between different formats and time zones.
    Supports various input formats and can convert to different time zones.
    '''
    input_model = InputModel

    def __init__(self):     # pylint: disable=W0231:useless-super-delegation
        self.geolocator = Nominatim(user_agent="my_geocoder")
        self.tf = TimezoneFinder()

    async def run(self, arguments: Dict[str, Any]) -> List[TextContent]:
        # Validation and parsing of input arguments
        arg = InputModel(**arguments)

        date_time_str = arg.date_time_str
        from_timezone = arg.from_timezone
        to_timezone = arg.to_timezone

        if not date_time_str:
            return [TextContent(type="text", text="Missing required argument: date_time_str")]

        try:
            # Parse input datetime or get current time
            if str(date_time_str).upper() == "NOW":
                dt = datetime.datetime.now(datetime.timezone.utc)
            else:
                dt = datetime.datetime.strptime(date_time_str, '%Y-%m-%d %H:%M:%S')
                dt = pytz.utc.localize(dt)  # Treat input as UTC

            # Initialize target timezone
            to_tz = pytz.timezone(to_timezone)

            # Convert from source timezone if specified
            if from_timezone:
                from_tz = pytz.timezone(from_timezone)
                dt = dt.astimezone(from_tz)

            # Convert to target timezone
            dt = dt.astimezone(to_tz)
            result_text = f"<{to_tz.zone}> {dt.isoformat()}"
            return [TextContent(type="text", text=result_text)]

        except ValueError:
            return [TextContent(type="text", text="Invalid date and time format. Use 'YYYY-MM-DD HH:MM:SS' or 'NOW'")]
        except pytz.exceptions.UnknownTimeZoneError as e:
            return [TextContent(type="text", text=f"Unknown timezone: {str(e)}")]
