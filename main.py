from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import asyncio
import re
import pytz
from fastapi.staticfiles import StaticFiles

app = FastAPI()

# Mount the 'static' directory to serve files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_root():
    # You'll likely serve your index.html here
    return {"message": "Hello from the backend!"}

# Initialize FastAPI app
app = FastAPI(
    title="Upcoming Contest API",
    description="API to fetch upcoming coding contests from Codeforces, LeetCode, and CodeChef.",
    version="1.0.0",
)

# Define a Pydantic model for contest data
class Contest(BaseModel):
    name: str
    platform: str
    start_time: datetime
    duration_seconds: int
    url: str

# --- Data Fetching Functions ---

async def fetch_codeforces_contests():
    """Fetches upcoming contests from Codeforces API."""
    url = "https://codeforces.com/api/contest.list"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Raise an HTTPError for bad responses (4xx or 5xx)
        data = response.json()

        if data['status'] == 'OK':
            contests = []
            for contest in data['result']:
                # Filter for upcoming contests (status 'BEFORE')
                if contest['phase'] == 'BEFORE':
                    start_time_ts = contest['startTimeSeconds']
                    duration_seconds = contest['durationSeconds']
                    # Codeforces API returns timestamps in UTC, convert to datetime
                    start_time_utc = datetime.fromtimestamp(start_time_ts, tz=pytz.utc)
                    contests.append(Contest(
                        name=contest['name'],
                        platform="Codeforces",
                        start_time=start_time_utc,
                        duration_seconds=duration_seconds,
                        url=f"https://codeforces.com/contest/{contest['id']}"
                    ))
            # Sort contests by start time
            return sorted(contests, key=lambda c: c.start_time)
        else:
            print(f"Codeforces API error: {data['comment']}")
            return []
    except requests.exceptions.RequestException as e:
        print(f"Error fetching Codeforces contests: {e}")
        return []

async def fetch_leetcode_contests():
    """Web scrapes upcoming contests from LeetCode."""
    url = "https://leetcode.com/contest/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        contests = []

        # Find contest cards - LeetCode's structure might change, adjust selectors if needed
        # Look for elements that represent upcoming contests.
        # This is a common pattern for cards or list items.
        # We are looking for divs with specific class names that contain contest info.
        contest_cards = soup.find_all('div', class_=re.compile(r'contest-card__container|list-item__2G-P'))

        for card in contest_cards:
            name_tag = card.find('a', class_=re.compile(r'contest-card__title|title__1oA9'))
            time_tag = card.find('div', class_=re.compile(r'contest-card__time|time__2qQO'))
            duration_tag = card.find('div', class_=re.compile(r'contest-card__duration|duration__1lF-'))

            if name_tag and time_tag and duration_tag:
                name = name_tag.get_text(strip=True)
                contest_url = "https://leetcode.com" + name_tag['href']

                time_str = time_tag.get_text(strip=True)
                duration_str = duration_tag.get_text(strip=True)

                # Parse time string (e.g., "Aug 15, 2025 07:30 PM PDT")
                try:
                    # LeetCode often displays time in PDT/PST.
                    # We'll parse it and convert to UTC for consistency.
                    # Use a flexible parser that can handle common time zone abbreviations or offsets.
                    # For simplicity, if PDT/PST is assumed, convert to UTC by adding 7 or 8 hours.
                    # A more robust solution would use a library like `dateutil` to handle timezones properly.
                    # For this example, let's assume PDT is UTC-7 for summer.
                    dt_obj = datetime.strptime(time_str.replace("PDT", "").replace("PST", "").strip(), "%b %d, %Y %I:%M %p")
                    # Assume PDT (UTC-7) for now, convert to UTC
                    start_time_local = pytz.timezone('America/Los_Angeles').localize(dt_obj)
                    start_time_utc = start_time_local.astimezone(pytz.utc)

                except ValueError:
                    print(f"Could not parse LeetCode time: {time_str}")
                    continue

                # Parse duration string (e.g., "1h 30m" or "2 hours 30 minutes")
                duration_seconds = 0
                if 'h' in duration_str:
                    hours_match = re.search(r'(\d+)\s*h', duration_str)
                    if hours_match:
                        duration_seconds += int(hours_match.group(1)) * 3600
                if 'm' in duration_str:
                    minutes_match = re.search(r'(\d+)\s*m', duration_str)
                    if minutes_match:
                        duration_seconds += int(minutes_match.group(1)) * 60
                if 'd' in duration_str: # In case of days, e.g., "2 days"
                    days_match = re.search(r'(\d+)\s*d', duration_str)
                    if days_match:
                        duration_seconds += int(days_match.group(1)) * 24 * 3600

                # Only include contests that are truly upcoming (start_time in the future)
                if start_time_utc > datetime.now(pytz.utc) - timedelta(minutes=5): # Small buffer for recently started
                    contests.append(Contest(
                        name=name,
                        platform="LeetCode",
                        start_time=start_time_utc,
                        duration_seconds=duration_seconds,
                        url=contest_url
                    ))
        return sorted(contests, key=lambda c: c.start_time)
    except requests.exceptions.RequestException as e:
        print(f"Error fetching LeetCode contests: {e}")
        return []

async def fetch_codechef_contests():
    """Web scrapes upcoming contests from CodeChef."""
    url = "https://www.codechef.com/contests"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        contests = []

        # CodeChef uses tables for contests, look for the "Upcoming Contests" table
        # Find the table that likely contains "Upcoming Contests"
        # The structure might vary, so identifying by headers or specific table attributes is key.
        upcoming_contests_div = soup.find('div', class_='contest-table')
        if upcoming_contests_div:
            # Find the actual table within this div
            table = upcoming_contests_div.find('table', class_='table') # Assuming a table with class 'table'

            if table:
                rows = table.find_all('tr')
                # Skip header row
                for row in rows[1:]:
                    cols = row.find_all('td')
                    if len(cols) >= 5: # Ensure enough columns for contest data
                        name_tag = cols[0].find('a')
                        code_tag = cols[1] # Contest Code
                        start_time_str = cols[2].get_text(strip=True)
                        end_time_str = cols[3].get_text(strip=True) # Not directly duration, but can calculate
                        
                        if name_tag:
                            name = name_tag.get_text(strip=True)
                            contest_code = code_tag.get_text(strip=True)
                            contest_url = f"https://www.codechef.com/{contest_code}" # CodeChef contest URL structure

                            try:
                                # CodeChef times are usually in IST. Convert to UTC.
                                # Example: "15 Aug 2025 22:00:00"
                                start_time_local = datetime.strptime(start_time_str, "%d %b %Y %H:%M:%S")
                                end_time_local = datetime.strptime(end_time_str, "%d %b %Y %H:%M:%S")

                                # Assuming CodeChef times are in IST (Indian Standard Time, UTC+5:30)
                                ist_timezone = pytz.timezone('Asia/Kolkata')
                                start_time_ist = ist_timezone.localize(start_time_local)
                                end_time_ist = ist_timezone.localize(end_time_local)

                                start_time_utc = start_time_ist.astimezone(pytz.utc)
                                duration_seconds = int((end_time_utc - start_time_utc).total_seconds())

                                # Only include contests that are truly upcoming
                                if start_time_utc > datetime.now(pytz.utc) - timedelta(minutes=5):
                                    contests.append(Contest(
                                        name=name,
                                        platform="CodeChef",
                                        start_time=start_time_utc,
                                        duration_seconds=duration_seconds,
                                        url=contest_url
                                    ))
                            except ValueError:
                                print(f"Could not parse CodeChef time: Start: {start_time_str}, End: {end_time_str}")
                                continue
        return sorted(contests, key=lambda c: c.start_time)
    except requests.exceptions.RequestException as e:
        print(f"Error fetching CodeChef contests: {e}")
        return []

# --- API Endpoints ---

@app.get(
    "/contests",
    response_model=list[Contest],
    summary="Get All Upcoming Contests",
    description="Retrieves a list of upcoming coding contests from all supported platforms."
)
async def get_all_contests():
    """
    Retrieves all upcoming contests from Codeforces, LeetCode, and CodeChef.
    """
    codeforces_contests = await fetch_codeforces_contests()
    leetcode_contests = await fetch_leetcode_contests()
    codechef_contests = await fetch_codechef_contests()

    all_contests = sorted(
        codeforces_contests + leetcode_contests + codechef_contests,
        key=lambda c: c.start_time
    )
    return all_contests


@app.get(
    "/contests/{platform_name}",
    response_model=list[Contest],
    summary="Get Contests by Platform",
    description="Retrieves a list of upcoming coding contests filtered by a specific platform."
)
async def get_contests_by_platform(
    # Corrected line: FastAPI will infer it's a path parameter
    platform_name: str
):
    """
    Retrieves upcoming contests for a specified platform.
    - **platform_name**: The name of the platform (e.g., "Codeforces", "LeetCode", "CodeChef").
    """
    platform_name_lower = platform_name.lower()
    contests = []

    if platform_name_lower == "codeforces":
        contests = await fetch_codeforces_contests()
    elif platform_name_lower == "leetcode":
        contests = await fetch_leetcode_contests()
    elif platform_name_lower == "codechef":
        contests = await fetch_codechef_contests()
    else:
        raise HTTPException(status_code=404, detail="Platform not found. Supported platforms are: Codeforces, LeetCode, CodeChef.")

    return contests

# Root endpoint for basic health check
@app.get(
    "/",
    summary="API Root",
    description="Basic health check endpoint."
)
async def read_root():
    return {"message": "Welcome to the Upcoming Contest API! Visit /docs for API documentation."}