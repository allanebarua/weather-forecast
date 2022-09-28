# weather-forecast

Background
---------------
This project provides an API that analyzes forecasted weather conditions based on the data provided by the https://www.weatherapi.com/ public API.

The API computes the minimum, maximum, average and median temperatures in degrees celcius for a given geographical location over a given number of subsequent days. To achive this, the API relies upon the data provided by the weather forecast API endpoint (http://api.weatherapi.com/v1/forecast.json) which provides weather forecast up to a maximum of 14 days.

TO-DO: The functionality of the API can be extended to include more futuristict weather predictions by incorparating the data provided by the Future API (http://api.weatherapi.com/v1/future.json)

Key technologies
----------------
  * *Language*: Python
  * *Framework*: Django
  * *Relational Database*: SQLite
  * *REST API Framework*: DRF
  * *Testing, Code styling and linting*: Tox, Pytest, Coverage, Flake8

Getting Started
---------------

*Assumes a \*nix setup

1. Install git, python3, pip, virtualenv in your system. For example in ubuntu::

    ```
    sudo apt update
    sudo apt install git python3 python3-setuptools
    sudo apt install libpq-dev
    ```

2. Clone this project: ``git clone https://github.com/allanebarua/weather-forecast.git``

4. Create and start using a local environment::
    ```
    cd weather-forecast
    python3 -m venv forecast-venv
    source forecast-venv/bin/activate
    pip install -r requirements.txt
    ```

5. Run tests to make sure that everything is okay

    ```
    tox
    ```
 
6. Run the server
    ```
    python manage.py runserver
    ```

7. After running the server use the below credentials to test out the API on your browser
    ```
    *URL*: http://127.0.0.1:8000/api/locations/LONDON/?days=1
    *USERNAME*: admin
    *PASSWORD*: 123
    ```
