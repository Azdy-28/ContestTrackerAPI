async function fetchContests() {
    const response = await fetch('/contests');
    const contests = await response.json();
    const container = document.getElementById('contests-container');

    contests.forEach(contest => {
        const contestDiv = document.createElement('div');
        contestDiv.innerHTML = `<h3>${contest.name}</h3>
                                <p>Platform: ${contest.platform}</p>
                                <p>Start: ${new Date(contest.start_time).toLocaleString()}</p>`;
        container.appendChild(contestDiv);
    });
}

fetchContests();