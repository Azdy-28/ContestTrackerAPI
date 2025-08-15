# Upcoming Contest API

An API that delivers upcoming programming contest information from platforms like Codeforces, LeetCode, and CodeChef.

## ✨ Features

  * **Platform Aggregation**: Fetches and combines contest data from multiple popular coding platforms.
  * **Platform Filtering**: Supports filtering contests by specific platforms via API endpoints.
  * **Real-time Data**: Provides up-to-date JSON responses by scraping and using public APIs.
  * **Swagger Documentation**: Automatically generated, interactive API documentation is available at the `/docs` endpoint.
  * **Simple Frontend**: Includes a basic web interface to visualize the upcoming contests.
  * **Containerized Deployment**: Ready for deployment using `Procfile` on services like Render.

## 🚀 Technologies

  * **FastAPI**: A modern, high-performance web framework for building APIs with Python.
  * **Python**: The primary programming language used for the backend logic.
  * **BeautifulSoup & Requests**: Used for web scraping contest data from LeetCode and CodeChef.
  * **Render**: The cloud platform used for continuous deployment of the API.

## 📦 Getting Started

### Prerequisites

  * Python 3.8+
  * `pip` (Python package installer)
  * `venv` (Python virtual environment)

### Installation

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/Azdy-28/ContestTrackerAPI.git
    cd ContestTrackerAPI
    ```

2.  **Create and activate a virtual environment:**

    ```bash
    # On macOS/Linux
    python3 -m venv venv
    source venv/bin/activate

    # On Windows
    python -m venv venv
    venv\Scripts\activate
    ```

3.  **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

### Running Locally

To run the application on your local machine, use the `uvicorn` server:

```bash
uvicorn main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.

  * **Frontend**: `http://127.0.0.1:8000`
  * **API Docs**: `http://127.0.0.1:8000/docs`

## 📋 API Endpoints

### Get all upcoming contests

**`GET /contests`**

Retrieves a list of all upcoming contests from all supported platforms.

**Example Response:**

```json
[
  {
    "name": "Codeforces Round 123",
    "platform": "Codeforces",
    "start_time": "2025-08-16T15:00:00+00:00",
    "duration_seconds": 7200,
    "url": "https://codeforces.com/contest/123"
  },
  ...
]
```

### Get contests by platform

**`GET /contests/{platform_name}`**

Retrieves upcoming contests for a specific platform.

| Path Parameter | Description |
| :--- | :--- |
| `platform_name` | The name of the platform (e.g., `Codeforces`, `LeetCode`, `CodeChef`). |

**Example Response for `GET /contests/CodeChef`:**

```json
[
  {
    "name": "CodeChef Starter 100",
    "platform": "CodeChef",
    "start_time": "2025-08-17T14:30:00+00:00",
    "duration_seconds": 5400,
    "url": "https://www.codechef.com/START100"
  },
  ...
]
```
