const API_URLS = [
    "https://smart-ai-filter-production.up.railway.app/api/v1/rank-feed",
    "http://localhost:8000/api/v1/rank-feed"
];

async function postToBackend(payload) {
    let lastError = null;

    for (const apiUrl of API_URLS) {
        try {
            console.log(`Trying backend: ${apiUrl}`);

            const response = await fetch(apiUrl, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(payload)
            });

            console.log("HTTP Status:", response.status);

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(
                    `Request failed for ${apiUrl} with ${response.status}: ${errorText}`
                );
            }

            return await response.json();
        } catch (error) {
            console.error(`Backend attempt failed for ${apiUrl}:`, error);
            lastError = error;
        }
    }

    throw lastError || new Error("No backend endpoints are available.");
}

console.log("Background Service Worker Started");

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    console.log("Message Received:", request);

    if (request.action !== "analyzeFeed") {
        return;
    }

    postToBackend({
        interests: request.interests,
        videos: request.videos
    })
    .then((data) => {
        console.log("Backend Response:", data);
        sendResponse({
            success: true,
            data: data.ranked_videos
        });
    })
    .catch((error) => {
        console.error("Fetch Error:", error);
        sendResponse({
            success: false,
            error: error.toString()
        });
    });

    return true; // Keeps the messaging channel open asynchronously
});
