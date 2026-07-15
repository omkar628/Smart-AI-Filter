const API_URL =
    "https://smart-ai-filter-production.up.railway.app/api/v1/rank-feed";

console.log("Background Service Worker Started");

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    console.log("Message Received:", request);

    if (request.action !== "analyzeFeed") {
        return;
    }

    fetch(API_URL, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            interests: request.interests,
            videos: request.videos
        })
    })
    .then((response) => {
        console.log("HTTP Status:", response.status);
        return response.json();
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
