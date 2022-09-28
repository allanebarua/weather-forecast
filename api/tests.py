"""Tests."""
import base64
import random
from unittest.mock import MagicMock, patch

from django.contrib.auth import hashers, models
from django.urls import reverse
from model_bakery import baker
from requests import ConnectionError, exceptions
from rest_framework import HTTP_HEADER_ENCODING, status, test


def create_test_user_account():
    """Create a system user."""
    return baker.make(
        models.User, username='tester',
        password=hashers.make_password('123'))


def add_auth_credentials(client):
    """Add authentication information to the client."""
    credentials = 'tester:123'
    base64_credentials = base64.b64encode(
        credentials.encode(HTTP_HEADER_ENCODING)).decode(HTTP_HEADER_ENCODING)

    client.credentials(HTTP_AUTHORIZATION=f'Basic {base64_credentials}')

    return client


class WeatherForecastAPITests(test.APITestCase):
    """Test Class for Weather forecasting API."""

    def setUp(self):
        """Create API user."""
        self.test_user = create_test_user_account()

    def test_unauthenticated_client(self):
        """Attempt to access the API via an unauthorized client."""
        url = reverse('list-forecast', args=('LONDON', ))
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_client__days_not_supplied(self):
        """Attempt to access the API without supplying the number of days."""
        url = reverse('list-forecast', args=('LONDON', ))
        self.client = add_auth_credentials(self.client)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, 'Number of days has not been supplied.')

    def test_more_than_14_days_supplied(self):
        """Attemp to get forecast for more that 14 days in the future."""
        url = reverse('list-forecast', args=('LONDON', ))
        url = url + '?days=20'
        self.client = add_auth_credentials(self.client)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, 'The API can only forecast up to 14 days.')

    def test_less_than_one_days_provided(self):
        """Attemp to get forecast for more that 14 days in the future."""
        url = reverse('list-forecast', args=('LONDON', ))
        url = url + '?days=-1'
        self.client = add_auth_credentials(self.client)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, 'Number of days should range from 1 to 14.')

    def test_non_numeric_value_passed_as_number_of_days(self):
        """Attemp to access the API using an invalid number of days."""
        url = reverse('list-forecast', args=('LONDON', ))
        url = url + '?days=xyz'
        self.client = add_auth_credentials(self.client)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, 'Invalid number of days provided.')

    @patch('api.views.requests')
    def test_public_api_throws_a_connection_error(self, requests_mock):
        """Test Connection error."""
        requests_mock.get.side_effect = ConnectionError('errrr!')

        url = reverse('list-forecast', args=('LONDON', ))
        url = url + '?days=10'
        self.client = add_auth_credentials(self.client)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

    @patch('api.views.requests')
    def test_public_api_throws_a_httperror(self, requests_mock):
        """Test HTTPError."""
        exc = exceptions.HTTPError('errrr!')
        exc.response = MagicMock()
        exc.response.json.return_value = {
            'error': {'code': 5000, 'message': 'Business error'}
        }

        requests_mock.get.side_effect = exc

        url = reverse('list-forecast', args=('LONDON', ))
        url = url + '?days=10'
        self.client = add_auth_credentials(self.client)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, 'Business error')

    @patch('api.views.requests')
    def test_public_api_throws_a_httperror_with_non_json_response(
            self, requests_mock):
        """Test response for unserializable HTTPError."""
        exc = exceptions.HTTPError('errrr!')
        exc.response = MagicMock()
        exc.response.json.side_effect = Exception()
        exc.response.reason = 'Not found'

        requests_mock.get.side_effect = exc

        url = reverse('list-forecast', args=('LONDON', ))
        url = url + '?days=10'
        self.client = add_auth_credentials(self.client)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, 'Not found')

    @patch('api.views.requests')
    def test_construct_forecast_payload_fails(self, requests_mock):
        """Test un-expected api response."""
        malformed_api_response = MagicMock()
        malformed_api_response.json.return_value = {}
        requests_mock.get.return_value = malformed_api_response

        url = reverse('list-forecast', args=('LONDON', ))
        url = url + '?days=5'
        self.client = add_auth_credentials(self.client)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(response.data, 'Internal server error.')

    @patch('api.views.requests')
    def test_get_aggregated_weather_forecast(self, requests_mock):
        """Test core logic of the API with multiple forecasts."""
        api_response = MagicMock()
        FORECAST_DATA = {
            'forecast': {
                'forecastday': []
            }
        }

        # Create random sample forecast data for 5 days.
        for _ in range(0, 5):
            daily_data = {
                'day': {
                    'maxtemp_c': round(random.uniform(20, 30), 1),
                    'mintemp_c': round(random.uniform(1, 9), 1),
                    'avgtemp_c': round(random.uniform(10, 19), 1),
                },
                'hour': []
            }
            for _ in range(0, 24):
                hourly_data = {
                    'temp_c': round(random.uniform(5, 30), 1)
                }

                daily_data['hour'].append(hourly_data)

            FORECAST_DATA['forecast']['forecastday'].append(daily_data)

        api_response.json.return_value = FORECAST_DATA
        requests_mock.get.return_value = api_response

        # The median temperature will be average temperature
        # recorded at the 12th hour and 13th hour of the 3rd day.
        temp_sum = FORECAST_DATA['forecast'][
            'forecastday'][2]['hour'][11]['temp_c'] + FORECAST_DATA['forecast'][
            'forecastday'][2]['hour'][12]['temp_c']
        expected_median = round(temp_sum / 2, 1)

        # The expected maximum temperature will be the highest maxtemp_c
        # across the 5 days
        expected_maxtemp = max([
            i['day']['maxtemp_c'] for i in FORECAST_DATA['forecast']['forecastday']])

        # The expected minimum temperature will be the lowest mintemp_c
        # across the 5 days
        expected_mintemp = min([
            i['day']['mintemp_c'] for i in FORECAST_DATA['forecast']['forecastday']])

        # The expected average temperature will be the
        # total hourly temperatures across the 5 days divided by
        # the number of hours (5*24)
        running_sum = 0
        for i in FORECAST_DATA['forecast']['forecastday']:
            for j in i['hour']:
                running_sum += j['temp_c']
        expected_avgtemp = round(running_sum/(5*24), 1)

        expected_response = {
            'maximum': expected_maxtemp,
            'minimum': expected_mintemp,
            'average': expected_avgtemp,
            'median': expected_median,
        }

        url = reverse('list-forecast', args=('LONDON', ))
        url = url + '?days=5'
        self.client = add_auth_credentials(self.client)
        actual_response = self.client.get(url)
        self.assertEqual(expected_response, actual_response.data)

    @patch('api.views.requests')
    def test_get_aggregated_weather_forecast_trivial_example(self, requests_mock):
        """Tests core logic with manual data from a single day."""
        api_response = MagicMock()
        FORECAST_DATA = {
            'forecast': {
                'forecastday': [{
                        'day': {
                            'maxtemp_c': 34.2,
                            'mintemp_c': 3.9
                        },
                        'hour': [
                            {'temp_c': 10.1},
                            {'temp_c': 15.0},
                            {'temp_c': 10.3},
                            {'temp_c': 24.9},
                            {'temp_c': 10.2},
                            {'temp_c': 10.0},
                            {'temp_c': 10.0},
                            {'temp_c': 4.0},
                            {'temp_c': 10.0},
                            {'temp_c': 21.0},
                            {'temp_c': 10.3},
                            {'temp_c': 3.8},  # .. Median
                            {'temp_c': 8.3},  # .. Median
                            {'temp_c': 10.5},
                            {'temp_c': 10.7},
                            {'temp_c': 7.3},
                            {'temp_c': 10.2},
                            {'temp_c': 10.5},
                            {'temp_c': 6.0},
                            {'temp_c': 10.0},
                            {'temp_c': 10.9},
                            {'temp_c': 3.9},  # .. Lowest
                            {'temp_c': 10.1},
                            {'temp_c': 34.2},  # .. Highest
                        ]
                    }
                ]
            }
        }

        # Avegare temperature recorded at the 11th and 12th hour.
        expected_median = round((3.8 + 8.3) / 2, 1)

        # Highest hourly temperature within the the day
        expected_maxtemp = 34.2

        # Lowest hourly temperature within the the day
        expected_mintemp = 3.9

        # Sum of all hourly temperatures divided by 24
        expected_avgtemp = 11.3

        expected_response = {
            'maximum': expected_maxtemp,
            'minimum': expected_mintemp,
            'average': expected_avgtemp,
            'median': expected_median,
        }

        api_response.json.return_value = FORECAST_DATA
        requests_mock.get.return_value = api_response

        url = reverse('list-forecast', args=('LONDON', ))
        url = url + '?days=5'
        self.client = add_auth_credentials(self.client)
        actual_response = self.client.get(url)
        self.assertEqual(expected_response, actual_response.data)

    @patch('api.views.requests')
    def test_median_temperature_for_even_number_of_days(self, requests_mock):
        """Test median computation with data from an even number of days."""
        api_response = MagicMock()
        FORECAST_DATA = {
            'forecast': {
                'forecastday': []
            }
        }

        # Create random sample forecast data for 2 days.
        for _ in range(0, 2):
            daily_data = {
                'day': {
                    'maxtemp_c': round(random.uniform(20, 30), 1),
                    'mintemp_c': round(random.uniform(1, 9), 1),
                    'avgtemp_c': round(random.uniform(10, 19), 1),
                },
                'hour': []
            }
            for _ in range(0, 24):
                hourly_data = {
                    'temp_c': round(random.uniform(5, 30), 1)
                }

                daily_data['hour'].append(hourly_data)

            FORECAST_DATA['forecast']['forecastday'].append(daily_data)

        api_response.json.return_value = FORECAST_DATA
        requests_mock.get.return_value = api_response

        # The median temperature will be the average temperature
        # recorded at the last hour of the 1st day and the 1st hour
        # of the 2nd day.
        temp_sum = FORECAST_DATA['forecast'][
            'forecastday'][0]['hour'][23]['temp_c'] + FORECAST_DATA['forecast'][
            'forecastday'][1]['hour'][0]['temp_c']
        expected_median = round(temp_sum / 2, 1)

        url = reverse('list-forecast', args=('LONDON', ))
        url = url + '?days=5'
        self.client = add_auth_credentials(self.client)
        actual_response = self.client.get(url)
        self.assertEqual(actual_response.status_code, status.HTTP_200_OK)
        assert expected_median == actual_response.data['median']
