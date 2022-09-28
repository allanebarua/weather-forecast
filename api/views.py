"""Logic powering weather forecast."""
import logging
import math

import requests
from django.conf import settings
from requests.exceptions import HTTPError
from rest_framework import authentication, permissions, status
from rest_framework.decorators import (
    api_view, authentication_classes, permission_classes)
from rest_framework.response import Response

LOGGER = logging.getLogger(__name__)


@api_view(['GET'])
@authentication_classes([authentication.BasicAuthentication])
@permission_classes([permissions.IsAuthenticated])
def get_aggregated_weather_forecast(request, city):
    """Get aggregate city-specific weather forecast over a period of time.

    The API endpoint expects the client to provide the city name as part
    of the url and the number of days as a query parameter as below;

    http://127.0.0.1:8000/api/locations/{city_name}/?days={no_of_days}

    The API then computes the maximum temperature, minimum temperature,
    average temperature and median temperature using data querried from
    a public API (http://api.weatherapi.com/v1/forecast.json) then returns
    a consolidated dictionary with the information to the client;

    Sample return payload:
        {
            'maximum': 20.0,
            'minimum': 10.0,
            'average': 15.0,
            'median': 12.0,
        }
    """
    is_valid, data = validate_days(request.query_params.get('days'))
    if not is_valid:
        return Response(data, status=status.HTTP_400_BAD_REQUEST)

    payload = {
        'key': settings.API_KEY,
        'days': data,
        'q': city
    }

    try:
        response = requests.get(
            settings.FORECAST_API_URL, params=payload,
            timeout=settings.API_TIMEOUT_IN_SECONDS)
        response.raise_for_status()

    except HTTPError as exc:
        LOGGER.error(exc.args[0], exc_info=True)
        # From the public API documentation, all business errors
        # will be wrapped under status code 4XX.
        # https://www.weatherapi.com/docs/#intro-error-codes
        response_status = status.HTTP_400_BAD_REQUEST
        msg = process_httperror(exc)

    except Exception as exc:
        LOGGER.error(exc.args[0], exc_info=True)
        # Mask all other errors as internal server errors.
        msg = 'Internal server error.'
        response_status = status.HTTP_500_INTERNAL_SERVER_ERROR

    else:
        response_status = status.HTTP_200_OK
        msg, error = construct_forecast_payload(response)
        if error:
            response_status = status.HTTP_500_INTERNAL_SERVER_ERROR

    finally:
        return Response(msg, status=response_status)


def construct_forecast_payload(api_response_object):
    """Construct final weather forecast payload."""
    try:
        daily_forecasts = api_response_object.json()[
            'forecast']['forecastday']
        days = len(daily_forecasts)
        # For accuracy, the median temperature is calculated
        # from the hourly temperatures recorded across the
        # days queried.
        record_count = days * 24
        middle_position = record_count // 2
        day_index, hour = divmod(middle_position, 24)

        if hour == 0:
            data_points = ((day_index-1, 23), (day_index, hour))
        else:
            data_points = ((day_index, hour-1), (day_index, hour))

        temp1 = daily_forecasts[data_points[0][0]]['hour'][data_points[0][1]]['temp_c']
        temp2 = daily_forecasts[data_points[1][0]]['hour'][data_points[1][1]]['temp_c']

        median_temp = round((temp1 + temp2)/2, 1)

        # Calculate the maximum, minimum and average temperatures
        # from the hourly recorded temperatures to enhance accuracy
        # for floating point operations.
        max_temp = -math.inf
        min_temp = math.inf
        running_sum = 0

        for forecast in daily_forecasts:

            max_temp = max(forecast['day']['maxtemp_c'], max_temp)
            min_temp = min(forecast['day']['mintemp_c'], min_temp)

            for hourly_forecast in forecast['hour']:
                running_sum += hourly_forecast['temp_c']

        avg_temp = round(running_sum/record_count, 1)

        forecast_data = {
            'maximum': max_temp,
            'minimum': min_temp,
            'average': round(avg_temp, 1),
            'median': median_temp,
        }

        return forecast_data, False

    except Exception as exc:
        LOGGER.error(exc.args[0], exc_info=True)
        return 'Internal server error.', True


def validate_days(no_of_days):
    """Validate number of days supplied by the client."""
    if no_of_days is None:
        msg = 'Number of days has not been supplied.'
        return False, msg

    try:
        no_of_days = int(no_of_days)

        # The public endpoint being used only supports forecasts
        # up to 14 days.
        if no_of_days > 14:
            msg = 'The API can only forecast up to 14 days.'
            return False, msg

        if no_of_days < 1:
            msg = 'Number of days should range from 1 to 14.'
            return False, msg

    except (TypeError, ValueError):
        msg = 'Invalid number of days provided.'
        return False, msg

    else:
        return True, no_of_days


def process_httperror(exc):
    """Retrieve an appropriate error message from the httperror."""
    try:
        msg = exc.response.json()
        error_msg = msg.get('error', {}).get('message')
        return error_msg or exc.response.reason

    except Exception:
        LOGGER.error(exc.args[0], exc_info=True)
        return exc.response.reason
