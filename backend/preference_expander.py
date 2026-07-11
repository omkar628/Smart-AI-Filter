import os
import json
import time

from dotenv import load_dotenv
from groq import Groq


load_dotenv()


class PreferenceExpander:

    def __init__(self):

        api_key = os.getenv("GROQ_API_KEY")

        if not api_key:
            raise ValueError(
                "GROQ_API_KEY was not found in the .env file."
            )

        self.client = Groq(api_key=api_key)

        print("Groq Preference Expander initialized.")


    def expand_preference(self, preference):

        prompt = f"""
You are helping build a semantic YouTube recommendation filter.

The user's interest is:

{preference}

Generate exactly 30 closely related topics, subtopics, concepts,
and terminology that would help identify YouTube videos related
to this interest.

Rules:

- Include only directly related concepts.
- Avoid vague or overly broad concepts.
- Each concept should be meaningful on its own.
- Include the original preference.
- Return ONLY a valid JSON array of strings.
- Do not use markdown.
- Do not add explanations.

Example input:

DSA

Example output:

[
    "DSA",
    "Data Structures and Algorithms",
    "Coding Interviews",
    "Competitive Programming",
    "LeetCode",
    "Algorithm Analysis",
    "Time Complexity",
    "Space Complexity",
    "Arrays",
    "Linked Lists",
    "Stacks",
    "Queues",
    "Hash Tables",
    "Trees",
    "Binary Trees",
    "Binary Search Trees",
    "Heaps",
    "Graphs",
    "Graph Algorithms",
    "Breadth-First Search",
    "Depth-First Search",
    "Dynamic Programming",
    "Greedy Algorithms",
    "Recursion",
    "Backtracking",
    "Divide and Conquer",
    "Sorting Algorithms",
    "Searching Algorithms",
    "Sliding Window",
    "Two Pointers"
]

Now generate concepts for:

{preference}
"""

        max_retries = 3


        for attempt in range(max_retries):

            try:

                print(
                    f"Calling Groq for '{preference}' "
                    f"(Attempt {attempt + 1}/{max_retries})"
                )


                response = self.client.chat.completions.create(

                    model="llama-3.3-70b-versatile",

                    messages=[

                        {
                            "role": "system",
                            "content": (
                                "You generate semantic concepts for "
                                "a YouTube recommendation system. "
                                "Always return only valid JSON."
                            )
                        },

                        {
                            "role": "user",
                            "content": prompt
                        }

                    ],

                    temperature=0.2

                )


                raw_text = (
                    response
                    .choices[0]
                    .message
                    .content
                    .strip()
                )


                # Remove possible markdown formatting.

                raw_text = raw_text.replace(
                    "```json",
                    ""
                )

                raw_text = raw_text.replace(
                    "```",
                    ""
                )

                raw_text = raw_text.strip()


                # Convert JSON text into Python list.

                try:

                    concepts = json.loads(raw_text)

                except json.JSONDecodeError:

                    print(
                        "Groq returned invalid JSON:"
                    )

                    print(raw_text)

                    return [preference]


                # Make sure result is actually a list.

                if not isinstance(concepts, list):

                    print(
                        "Groq response was not a list."
                    )

                    return [preference]


                # Clean the concepts.

                cleaned_concepts = []


                for concept in concepts:

                    if isinstance(concept, str):

                        concept = concept.strip()

                        if concept:

                            cleaned_concepts.append(
                                concept
                            )


                # Make sure original preference exists.

                preference_exists = any(

                    concept.lower()
                    == preference.lower()

                    for concept in cleaned_concepts

                )


                if not preference_exists:

                    cleaned_concepts.insert(
                        0,
                        preference
                    )


                print(
                    f"Successfully expanded "
                    f"'{preference}' into "
                    f"{len(cleaned_concepts)} concepts."
                )


                return cleaned_concepts


            except Exception as error:

                print(
                    f"Groq API error on attempt "
                    f"{attempt + 1}: {error}"
                )


                if attempt < max_retries - 1:

                    wait_time = 2 ** attempt

                    print(
                        f"Waiting {wait_time} seconds "
                        f"before retry..."
                    )

                    time.sleep(wait_time)


        # ========================================================
        # FALLBACK
        # ========================================================

        print(
            f"Groq failed after {max_retries} attempts."
        )

        print(
            f"Using original preference as fallback: "
            f"{preference}"
        )


        return [preference]