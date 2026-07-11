console.log("SmartFeed AI: Content script active. Initializing observer...");

let processTimer = null;
const DEBOUNCE_DELAY = 1000;
const AI_CARD_STYLE_ID = "smartfeed-ai-card-style";

injectSmartFeedStyles();


// ============================================================
// EXTRACT VIDEOS FROM YOUTUBE
// ============================================================

function extractAndProcessVideos() {

    const videoElements = document.querySelectorAll(
        'ytd-rich-item-renderer:not([data-ai-processed="true"])'
    );

    if (videoElements.length === 0) return;

    console.log(
        `Found ${videoElements.length} new video cards.`
    );

    const videoBatch = [];
    const elementMap = new Map();


    videoElements.forEach((element) => {

        try {

            // ====================================================
            // 1. FIND THE REAL VIDEO TITLE LINK
            // ====================================================

            /*
                YouTube's new homepage DOM uses:

                a.ytLockupMetadataViewModelTitle

                for the actual video title.

                Previously we were finding the first /watch?v=
                link, which was sometimes the thumbnail link.

                That caused us to extract:

                Mix
                LIVE
                12:55

                instead of the real video title.
            */

            const titleLink = element.querySelector(
                'a.ytLockupMetadataViewModelTitle[href*="/watch?v="]'
            );


            // If we cannot find a title link,
            // this might be an ad, post, short, etc.

            if (!titleLink) {

                console.warn(
                    "Skipped card: Real title link not found."
                );

                return;
            }



            // ====================================================
            // 2. EXTRACT VIDEO ID
            // ====================================================

            const url = new URL(titleLink.href);

            const videoId = url.searchParams.get("v");


            if (!videoId) {

                console.warn(
                    "Skipped card: Video ID not found."
                );

                return;
            }



            // ====================================================
            // 3. EXTRACT REAL VIDEO TITLE
            // ====================================================

            const title = titleLink.textContent.trim();


            if (!title) {

                console.warn(
                    "Skipped card: Video title is empty."
                );

                return;
            }



            // ====================================================
            // 4. EXTRACT CHANNEL / METADATA
            // ====================================================

            const metadataRows = element.querySelectorAll(
                ".ytContentMetadataViewModelMetadataRow"
            );


            let channel = "Unknown Channel";


            if (metadataRows.length > 0) {

                channel =
                    metadataRows[0].textContent.trim();

            }



            // ====================================================
            // 5. DEBUG LOG
            // ====================================================

            console.log(
                "EXTRACTED VIDEO:",
                {
                    videoId,
                    title,
                    channel
                }
            );



            // ====================================================
            // 6. ADD VIDEO TO BATCH
            // ====================================================

            videoBatch.push({

                video_id: videoId,

                title: title,

                channel: channel,

                description: ""

            });



            // ====================================================
            // 7. CONNECT VIDEO ID TO YOUTUBE HTML ELEMENT
            // ====================================================

            /*
                Example:

                abc123
                    ↓
                YouTube Video Card HTML


                Later when Python returns:

                {
                    video_id: "abc123",
                    action: "Hide"
                }

                We can find the correct HTML element.
            */

            elementMap.set(
                videoId,
                element
            );



            // ====================================================
            // 8. MARK VIDEO AS PROCESSED
            // ====================================================

            /*
                IMPORTANT:

                We only mark it AFTER successful extraction.

                Otherwise failed videos would never be
                processed again.
            */

            element.setAttribute(
                "data-ai-processed",
                "true"
            );


        } catch (error) {

            console.error(
                "Video extraction error:",
                error
            );

        }

    });



    console.log(
        `Successfully extracted ${videoBatch.length} videos. Sending to AI...`
    );



    if (videoBatch.length > 0) {

        sendToAIBackend(
            videoBatch,
            elementMap
        );

    }

}



// ============================================================
// SEND VIDEOS TO BACKGROUND SERVICE WORKER
// ============================================================

function sendToAIBackend(
    videos,
    elementMap
) {

    chrome.storage.local.get(
        ["userInterests"],
        (result) => {

            const interests =
                result.userInterests;



            // Check if user has saved interests

            if (
                !interests ||
                Object.keys(interests).length === 0
            ) {

                console.warn(
                    "No interests saved. Open the extension and save your interests."
                );

                return;
            }



            console.log(
                "Sending videos to background...",
                {
                    interests,
                    videoCount: videos.length
                }
            );



            // Send message to background.js

            chrome.runtime.sendMessage(

                {

                    action: "analyzeFeed",

                    interests: interests,

                    videos: videos

                },


                (response) => {


                    // ============================================
                    // CHECK CHROME COMMUNICATION ERROR
                    // ============================================

                    if (chrome.runtime.lastError) {

                        console.error(
                            "Communication error:",
                            chrome.runtime.lastError
                        );

                        return;
                    }



                    // ============================================
                    // SUCCESSFUL AI RESPONSE
                    // ============================================

                    if (response?.success) {

                        console.log(
                            `Received AI rankings for ${response.data.length} videos.`
                        );


                        applyFiltersToDOM(
                            response.data,
                            elementMap
                        );

                    }


                    // ============================================
                    // BACKEND ERROR
                    // ============================================

                    else {

                        console.error(
                            "Backend error:",
                            response
                        );

                    }

                }

            );

        }

    );

}



// ============================================================
// APPLY AI RESULTS TO YOUTUBE
// ============================================================

function applyFiltersToDOM(
    rankedVideos,
    elementMap
) {

    console.log(
        "Applying AI filtering..."
    );


    rankedVideos.forEach((video) => {


        // Find actual YouTube HTML card

        const element =
            elementMap.get(video.video_id);


        if (!element) return;



        // Remove previous styling

        element.classList.remove(
            "smartfeed-ai-match",
            "smartfeed-ai-hide"
        );


        const oldBadge =
            element.querySelector(
                ".smartfeed-ai-badge"
            );


        if (oldBadge) {

            oldBadge.remove();

        }



        // ====================================================
        // HIDE VIDEO
        // ====================================================

        if (video.action === "Hide") {

            element.classList.add(
                "smartfeed-ai-hide"
            );


            element.style.opacity =
                "0.16";


            element.style.pointerEvents =
                "none";


            element.title =
                "Filtered out by SmartFeed AI";


            return;

        }



        // ====================================================
        // SHOW VIDEO
        // ====================================================

        const confidence =
            (video.confidence * 100)
                .toFixed(1);



        // Create AI Match Badge

        const badge =
            document.createElement("div");


        badge.className =
            "smartfeed-ai-badge";


        badge.textContent =
            `${video.topic} match ${confidence}%`;



        // Add match styling

        element.classList.add(
            "smartfeed-ai-match"
        );


        element.style.opacity =
            "1";


        element.style.pointerEvents =
            "auto";


        element.title =
            `AI Match: ${video.topic} (${confidence}%)`;



        // Add badge to video card

        element.prepend(
            badge
        );

    });

}



// ============================================================
// ADD SMARTFEED CSS
// ============================================================

function injectSmartFeedStyles() {


    // Don't inject styles multiple times

    if (
        document.getElementById(
            AI_CARD_STYLE_ID
        )
    ) {

        return;

    }



    const style =
        document.createElement("style");


    style.id =
        AI_CARD_STYLE_ID;



    style.textContent = `


        /* ================================================
           AI MATCHED VIDEO
        ================================================= */


        ytd-rich-item-renderer.smartfeed-ai-match {

            position: relative;

            border-radius: 18px;

            box-shadow:
                0 18px 40px
                rgba(14, 165, 233, 0.16);

            outline:
                2px solid
                rgba(103, 232, 249, 0.7);

            outline-offset: 3px;

            background:
                linear-gradient(
                    180deg,
                    rgba(103, 232, 249, 0.08),
                    rgba(15, 23, 42, 0.02)
                );

            transition:
                opacity 180ms ease,
                transform 180ms ease,
                box-shadow 180ms ease;

        }



        ytd-rich-item-renderer.smartfeed-ai-match:hover {

            transform:
                translateY(-2px);

            box-shadow:
                0 24px 44px
                rgba(14, 165, 233, 0.22);

        }



        /* ================================================
           AI HIDDEN VIDEO
        ================================================= */


        ytd-rich-item-renderer.smartfeed-ai-hide {

            filter:
                grayscale(0.85);

            transition:
                opacity 180ms ease,
                filter 180ms ease;

        }



        /* ================================================
           AI MATCH BADGE
        ================================================= */


        .smartfeed-ai-badge {

            margin:
                0 0 10px;

            display:
                inline-flex;

            align-items:
                center;

            padding:
                7px 12px;

            border-radius:
                999px;

            font-size:
                11px;

            font-weight:
                700;

            letter-spacing:
                0.04em;

            text-transform:
                uppercase;

            color:
                #dffbff;

            background:
                linear-gradient(
                    135deg,
                    rgba(8, 145, 178, 0.92),
                    rgba(14, 116, 144, 0.92)
                );

            box-shadow:
                0 10px 24px
                rgba(8, 145, 178, 0.28);

            width:
                fit-content;

        }


    `;



    document.head.appendChild(
        style
    );

}



// ============================================================
// WATCH YOUTUBE FOR NEW VIDEOS
// ============================================================

const observer =
    new MutationObserver(() => {


        // Cancel previous timer

        clearTimeout(
            processTimer
        );



        // Wait until YouTube stops changing DOM

        processTimer =
            setTimeout(() => {


                // Only process YouTube homepage

                if (
                    window.location.pathname === "/"
                ) {

                    extractAndProcessVideos();

                }


            }, DEBOUNCE_DELAY);

    });



// Start watching YouTube page

observer.observe(
    document.body,
    {

        childList: true,

        subtree: true

    }
);



// ============================================================
// INITIAL SCAN
// ============================================================

setTimeout(
    extractAndProcessVideos,
    2000
);