async function fetchContests() {
    try {
        const response = await fetch('/contests');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const contests = await response.json();
        const container = document.getElementById('contests-container');
        container.innerHTML = ''; // Clear previous content

        if (contests.length === 0) {
            container.innerHTML = '<p>No upcoming contests found at this time.</p>';
            return;
        }

        contests.forEach(contest => {
            const card = document.createElement('div');
            card.className = 'contest-card';

            const startTime = new Date(contest.start_time);
            const durationMinutes = Math.floor(contest.duration_seconds / 60);
            const durationHours = Math.floor(durationMinutes / 60);
            const remainingMinutes = durationMinutes % 60;

            card.innerHTML = `
                <h3>${contest.name}</h3>
                <p><strong>Platform:</strong> ${contest.platform}</p>
                <p><strong>Start Time:</strong> ${startTime.toLocaleString()}</p>
                <p><strong>Duration:</strong> ${durationHours}h ${remainingMinutes}m</p>
                <p><a href="${contest.url}" target="_blank">View Contest</a></p>
            `;
            container.appendChild(card);
        });
    } catch (error) {
        console.error("Failed to fetch contests:", error);
        document.getElementById('contests-container').innerHTML = `<p style="color: red;">Error loading contests. Please try again later.</p>`;
    }
}

fetchContests();