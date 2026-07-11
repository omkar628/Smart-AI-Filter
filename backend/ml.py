from sentence_transformers import SentenceTransformer, CrossEncoder, util
from preference_expander import PreferenceExpander
import torch


class AIRanker:

    def __init__(self):

        print("Loading AI Models...")

        # Stage 1: Fast semantic retrieval
        self.model = SentenceTransformer(
            "BAAI/bge-base-en-v1.5"
        )

        # Stage 2: More accurate relevance checking
        self.cross_encoder = CrossEncoder(
            "cross-encoder/ms-marco-MiniLM-L6-v2"
        )

        # IMPORTANT:
        # This threshold is still ONLY being used for the BGE score.
        # We are not using the Cross-Encoder for filtering yet.
        self.threshold = 0.35

        # Number of strongest concept matches used for BGE score.
        self.top_k = 3

        self.expander = PreferenceExpander()

        # In-memory preference cache.
        self.preference_cache = {}


    # ============================================================
    # GET EXPANDED CONCEPTS
    # ============================================================

    def get_expanded_preference(self, preference):

        if preference in self.preference_cache:

            print(f"Using cached preference: {preference}")

            return self.preference_cache[preference]


        print(f"Expanding new preference: {preference}")


        concepts = self.expander.expand_preference(
            preference
        )


        self.preference_cache[preference] = concepts


        print(f"\nEXPANDED {preference}:")


        for concept in concepts:

            print(f"  - {concept}")


        print()


        return concepts


    # ============================================================
    # RANK VIDEOS
    # ============================================================

    def rank_videos(self, videos, interests):

        if not videos:

            return []


        # ========================================================
        # 1. PREPARE VIDEO TEXT
        # ========================================================

        video_texts = [

            (
                f"Title: {video['title']}. "
                f"Channel: {video['channel']}."
            )

            for video in videos

        ]


        # ========================================================
        # 2. GET USER INTEREST TOPICS
        # ========================================================

        interest_topics = list(
            interests.keys()
        )


        # ========================================================
        # 3. GENERATE VIDEO EMBEDDINGS
        # ========================================================

        video_embeddings = self.model.encode(

            video_texts,

            convert_to_tensor=True

        )


        # ========================================================
        # 4. PREPARE CONCEPT EMBEDDINGS
        # ========================================================

        topic_data = {}


        for topic in interest_topics:


            # Get expanded concepts from Groq.

            concepts = self.get_expanded_preference(
                topic
            )


            # Generate separate embedding
            # for every concept.

            concept_embeddings = self.model.encode(

                concepts,

                convert_to_tensor=True

            )


            topic_data[topic] = {

                "concepts": concepts,

                "embeddings": concept_embeddings

            }


        # ========================================================
        # 5. CREATE CATEGORY BUCKETS
        # ========================================================

        categorized_videos = {

            topic: []

            for topic in interest_topics

        }


        categorized_videos["Unknown"] = []


        # ========================================================
        # 6. ANALYZE EACH VIDEO
        # ========================================================

        for video_index, video in enumerate(videos):


            video_embedding = video_embeddings[
                video_index
            ]


            topic_scores = {}


            # ====================================================
            # COMPARE VIDEO AGAINST EVERY INTEREST
            # ====================================================

            for topic in interest_topics:


                concepts = topic_data[
                    topic
                ]["concepts"]


                concept_embeddings = topic_data[
                    topic
                ]["embeddings"]


                # BGE cosine similarity.

                similarity_scores = util.cos_sim(

                    video_embedding,

                    concept_embeddings

                )[0]


                # =================================================
                # FIND TOP-3 STRONGEST CONCEPT MATCHES
                # =================================================

                number_of_scores = len(
                    similarity_scores
                )


                actual_k = min(

                    self.top_k,

                    number_of_scores

                )


                top_values, top_indices = torch.topk(

                    similarity_scores,

                    k=actual_k

                )


                # =================================================
                # WEIGHTED TOP-3 SCORE
                # =================================================

                weights = torch.tensor(

                    [0.60, 0.25, 0.15],

                    device=top_values.device

                )


                weights = weights[:actual_k]


                weights = (

                    weights /

                    weights.sum()

                )


                final_topic_score = (

                    top_values * weights

                ).sum().item()


                # =================================================
                # SAVE STRONGEST MATCHED CONCEPTS
                # =================================================

                matched_concepts = [

                    {

                        "concept":
                            concepts[index.item()],

                        "score":
                            round(score.item(), 3)

                    }

                    for score, index in zip(

                        top_values,

                        top_indices

                    )

                ]


                topic_scores[topic] = {

                    "score":
                        final_topic_score,

                    "matched_concepts":
                        matched_concepts

                }


            # ====================================================
            # 7. FIND BEST TOPIC USING BGE
            # ====================================================

            best_topic = max(

                topic_scores,

                key=lambda topic:
                    topic_scores[topic]["score"]

            )


            best_score = topic_scores[
                best_topic
            ]["score"]


            best_concepts = topic_scores[
                best_topic
            ]["matched_concepts"]


            # ====================================================
            # 8. CROSS-ENCODER RELEVANCE CHECK
            # ====================================================

            # Get ALL expanded concepts belonging
            # to the topic selected by BGE.

            best_topic_concepts = topic_data[
                best_topic
            ]["concepts"]


            # Convert the concepts into one
            # readable topic description.

            topic_description = ", ".join(
                best_topic_concepts
            )


            # Prepare video information.

            video_text = (

                f"Title: {video['title']}. "

                f"Channel: {video['channel']}."

            )


            # Create the text pair.

            cross_encoder_pair = [

                (

                    video_text,

                    topic_description

                )

            ]


            # Get raw Cross-Encoder relevance score.

            cross_encoder_score = (

                self.cross_encoder.predict(

                    cross_encoder_pair

                )[0]

            )


            cross_encoder_score = float(
                cross_encoder_score
            )


            # ====================================================
            # 9. SHOW DEBUG INFORMATION
            # ====================================================

            print("\n" + "=" * 70)


            print(
                f"VIDEO: {video['title']}"
            )


            print(
                f"BGE BEST TOPIC: {best_topic}"
            )


            print(
                f"BGE WEIGHTED SCORE: "
                f"{best_score:.3f}"
            )


            print(
                f"CROSS-ENCODER SCORE: "
                f"{cross_encoder_score:.3f}"
            )


            print(
                "MATCHED CONCEPTS:"
            )


            for match in best_concepts:

                print(

                    f"   {match['concept']}"

                    f" → {match['score']:.3f}"

                )


            # ====================================================
            # 10. CATEGORIZE VIDEO
            # ====================================================
            #
            # IMPORTANT:
            #
            # We are STILL using the BGE score here.
            #
            # We first need to observe Cross-Encoder scores
            # before deciding its threshold.
            # ====================================================

            if best_score >= self.threshold:


                video_data = {

                    **video,

                    "topic":
                        best_topic,

                    "confidence":
                        round(best_score, 3),

                    "cross_encoder_score":
                        round(cross_encoder_score, 3),

                    "matched_concepts":
                        best_concepts

                }


                categorized_videos[
                    best_topic
                ].append(
                    video_data
                )


                print(
                    "RESULT: ACCEPTED"
                )


            else:


                video_data = {

                    **video,

                    "topic":
                        "Unknown",

                    "confidence":
                        round(best_score, 3),

                    "cross_encoder_score":
                        round(cross_encoder_score, 3),

                    "matched_concepts":
                        best_concepts

                }


                categorized_videos[
                    "Unknown"
                ].append(
                    video_data
                )


                print(
                    "RESULT: UNKNOWN"
                )


        # ========================================================
        # 11. APPLY USER PERCENTAGE DISTRIBUTION
        # ========================================================

        total_visible = len(videos)


        final_feed = []


        for topic, percentage in interests.items():


            target_count = int(

                total_visible *

                (percentage / 100.0)

            )


            # Sort by BGE score for now.

            topic_videos = sorted(

                categorized_videos[topic],

                key=lambda video:
                    video["confidence"],

                reverse=True

            )


            # Videos inside percentage limit.

            accepted = topic_videos[
                :target_count
            ]


            for video in accepted:

                video["action"] = "Show"

                final_feed.append(
                    video
                )


            # Videos exceeding percentage limit.

            rejected = topic_videos[
                target_count:
            ]


            for video in rejected:

                video["action"] = "Hide"

                final_feed.append(
                    video
                )


        # ========================================================
        # 12. HIDE UNKNOWN VIDEOS
        # ========================================================

        for video in categorized_videos[
            "Unknown"
        ]:

            video["action"] = "Hide"

            final_feed.append(
                video
            )


        return final_feed