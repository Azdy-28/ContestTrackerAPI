from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import asyncio
import re
import pytz
import os

# Initialize FastAPI app
app = FastAPI(
    title="Upcoming Contest API",
    description="API to fetch upcoming coding contests from Codeforces, LeetCode, and CodeChef.",
    version="1.0.0",
)

# Mount the 'static' directory to serve frontend files
app.mount("/static", StaticFiles(directory="static"), name="static")

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
        response.raise_for_status()
        data = response.json()

        if data['status'] == 'OK':
            contests = []
            for contest in data['result']:
                if contest['phase'] == 'BEFORE':
                    start_time_ts = contest['startTimeSeconds']
                    duration_seconds = contest['durationSeconds']
                    start_time_utc = datetime.fromtimestamp(start_time_ts, tz=pytz.utc)
                    contests.append(Contest(
                        name=contest['name'],
                        platform="Codeforces",
                        start_time=start_time_utc,
                        duration_seconds=duration_seconds,
                        url=f"https://codeforces.com/contest/{contest['id']}"
                    ))
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
    # Use a more specific and current User-Agent string from a real browser
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        contests = []

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

                try:
                    dt_obj = datetime.strptime(time_str.replace("PDT", "").replace("PST", "").strip(), "%b %d, %Y %I:%M %p")
                    start_time_local = pytz.timezone('America/Los_Angeles').localize(dt_obj)
                    start_time_utc = start_time_local.astimezone(pytz.utc)

                except ValueError:
                    print(f"Could not parse LeetCode time: {time_str}")
                    continue

                duration_seconds = 0
                if 'h' in duration_str:
                    hours_match = re.search(r'(\d+)\s*h', duration_str)
                    if hours_match:
                        duration_seconds += int(hours_match.group(1)) * 3600
                if 'm' in duration_str:
                    minutes_match = re.search(r'(\d+)\s*m', duration_str)
                    if minutes_match:
                        duration_seconds += int(minutes_match.group(1)) * 60
                if 'd' in duration_str:
                    days_match = re.search(r'(\d+)\s*d', duration_str)
                    if days_match:
                        duration_seconds += int(days_match.group(1)) * 24 * 3600

                if start_time_utc > datetime.now(pytz.utc) - timedelta(minutes=5):
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
        upcoming_contests_div = soup.find('div', class_='contest-table')
        if upcoming_contests_div:
            table = upcoming_contests_div.find('table', class_='table')
            if table:
                rows = table.find_all('tr')
                for row in rows[1:]:
                    cols = row.find_all('td')
                    if len(cols) >= 5:
                        name_tag = cols[0].find('a')
                        code_tag = cols[1]
                        start_time_str = cols[2].get_text(strip=True)
                        end_time_str = cols[3].get_text(strip=True)

                        if name_tag:
                            name = name_tag.get_text(strip=True)
                            contest_code = code_tag.get_text(strip=True)
                            contest_url = f"https://www.codechef.com/{contest_code}"

                            try:
                                start_time_local = datetime.strptime(start_time_str, "%d %b %Y %H:%M:%S")
                                end_time_local = datetime.strptime(end_time_str, "%d %b %Y %H:%M:%S")

                                ist_timezone = pytz.timezone('Asia/Kolkata')
                                start_time_ist = ist_timezone.localize(start_time_local)
                                end_time_ist = ist_timezone.localize(end_time_local)

                                start_time_utc = start_time_ist.astimezone(pytz.utc)
                                duration_seconds = int((end_time_utc - start_time_utc).total_seconds())

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
@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serves the main HTML page."""
    html_file_path = os.path.join("static", "index.html")
    if not os.path.exists(html_file_path):
        return HTMLResponse(content="<h1>Frontend not found!</h1><p>Please ensure 'static/index.html' exists.</p>", status_code=404)
    with open(html_file_path, "r") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)

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