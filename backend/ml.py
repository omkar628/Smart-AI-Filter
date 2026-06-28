from sentence_transformers import SentenceTransformer, util
import torch

class AIRanker:
    def __init__(self):
        # We load the model here so it only loads into memory ONCE on startup.
        print("Loading AI Model...")
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.threshold = 0.35  # Minimum confidence score to accept a categorization

    def rank_videos(self, videos, interests):
        if not videos:
            return []

        # 1. Prepare Text & Topics
        # Concatenate title and description for better context
        video_texts = [f"{v['title']} {v.get('description', '')}" for v in videos]
        interest_topics = list(interests.keys())
        
        # 2. Generate Embeddings (Dense Vectors)
        video_embeddings = self.model.encode(video_texts, convert_to_tensor=True)
        topic_embeddings = self.model.encode(interest_topics, convert_to_tensor=True)
        
        # 3. Calculate Cosine Similarity Matrix
        # Creates a grid of scores: (num_videos x num_topics)
        cosine_scores = util.cos_sim(video_embeddings, topic_embeddings)
        
        # Initialize buckets for sorting
        categorized_videos = {topic: [] for topic in interest_topics}
        categorized_videos["Unknown"] = []
        
        # 4. Categorize each video based on its highest similarity score
        for i, video in enumerate(videos):
            scores = cosine_scores[i]
            max_score_idx = torch.argmax(scores).item()
            max_score = scores[max_score_idx].item()
            
            if max_score >= self.threshold:
                topic = interest_topics[max_score_idx]
                video_data = {**video, "topic": topic, "confidence": round(max_score, 3)}
                categorized_videos[topic].append(video_data)
            else:
                video_data = {**video, "topic": "Unknown", "confidence": round(max_score, 3)}
                categorized_videos["Unknown"].append(video_data)
                
        # 5. Apply User's Percentage Distribution
        total_visible = len(videos)
        final_feed = []
        
        for topic, percentage in interests.items():
            # Calculate how many videos this topic is allowed to have
            target_count = int(total_visible * (percentage / 100.0))
            
            # Sort videos in this topic by confidence (Highest first)
            topic_vids = sorted(categorized_videos[topic], key=lambda x: x['confidence'], reverse=True)
            
            # Keep top scoring videos up to the target count
            accepted = topic_vids[:target_count]
            for v in accepted:
                v['action'] = 'Show'
                final_feed.append(v)
                
            # Hide the overflow
            rejected = topic_vids[target_count:]
            for v in rejected:
                v['action'] = 'Hide'
                final_feed.append(v)
                
        # 6. Hide all noise/unknown videos
        for v in categorized_videos["Unknown"]:
            v['action'] = 'Hide'
            final_feed.append(v)
            
        return final_feed