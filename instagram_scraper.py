from apify_client import ApifyClient
from dotenv import load_dotenv
import os
import pandas as pd
import time

class InstagramScraper:
    def __init__(self):
        load_dotenv()
        self.api_token = os.getenv('APIFY_API_TOKEN')
        if not self.api_token:
            raise ValueError("APIFY_API_TOKEN not found in .env file")
        self.client = ApifyClient(self.api_token)

    def scrape_profile(self, target_username):
        """Scrape Instagram profile information including 5 recent posts with details."""
        try:
            # Get profile and posts data
            run = self.client.actor("apify/instagram-scraper").call(run_input={
                "directUrls": [f"https://www.instagram.com/{target_username}/"],
                "resultsType": "posts",
                "resultsLimit": 5,  # Get only 5 posts
                "addParentData": True,
                "searchType": "user",
                "searchLimit": 1,
                "proxy": {
                    "useApifyProxy": True,
                    "apifyProxyGroups": ["RESIDENTIAL"]
                },
                "maxRequestRetries": 5,
                "maxConcurrency": 1
            })

            # Get the dataset ID from the run
            dataset_id = run['defaultDatasetId']
            print("Fetching profile and posts data...")
            time.sleep(10)
            
            # Fetch results
            items = list(self.client.dataset(dataset_id).iterate_items())
            
            if not items:
                print(f"No data found for username: {target_username}")
                return None

            # Process posts and reels
            posts_data = []
            reels_data = []
            
            for post in items[:5]:  # Ensure we only process 5 posts
                post_info = {
                    'post_id': post.get('id', ''),
                    'shortcode': post.get('shortCode', ''),
                    'caption': post.get('caption', ''),
                    'likes_count': post.get('likesCount', 0),
                    'comments_count': post.get('commentsCount', 0),
                    'timestamp': post.get('timestamp', ''),
                    'url': post.get('url', ''),
                    'media_type': post.get('type', ''),
                    'media_url': post.get('displayUrl', ''),
                    'location': post.get('location', {}).get('name', ''),
                    'hashtags': post.get('hashtags', []),
                    'mentions': post.get('mentions', []),
                    'engagement_rate': post.get('likesCount', 0) + post.get('commentsCount', 0),
                    'top_comments': [
                        {
                            'text': comment.get('text', ''),
                            'owner': comment.get('ownerUsername', ''),
                            'timestamp': comment.get('timestamp', '')
                        } 
                        for comment in post.get('comments', [])[:10]
                    ] if post.get('comments') else []
                }
                
                if post.get('type') == 'Video':
                    post_info['video_url'] = post.get('videoUrl', '')
                    post_info['video_view_count'] = post.get('videoViewCount', 0)
                    reels_data.append(post_info)
                else:
                    # For carousel posts, get all media URLs
                    if post.get('type') == 'Carousel':
                        post_info['carousel_media'] = [
                            item.get('displayUrl', '') 
                            for item in post.get('sidecarItems', [])
                        ]
                    posts_data.append(post_info)

            # Get profile info from the first post's owner
            owner = items[0].get('owner', {}) if items else {}
            profile_info = {
                'username': owner.get('username', target_username),
                'full_name': owner.get('fullName', ''),
                'biography': owner.get('biography', ''),
                'followers_count': owner.get('followersCount', 0),
                'following_count': owner.get('followingCount', 0),
                'posts_count': owner.get('postsCount', 0),
                'is_private': owner.get('isPrivate', False),
                'is_verified': owner.get('isVerified', False),
                'profile_pic_url': owner.get('profilePicUrl', ''),
                'external_url': owner.get('externalUrl', ''),
                'posts': posts_data,
                'reels': reels_data
            }
            return profile_info

        except Exception as e:
            print(f"Error scraping profile: {str(e)}")
            return None

def extract_username(input_text):
    """Extract username from URL or return as is if it's already a username."""
    if 'instagram.com' in input_text:
        # Remove trailing slash if present
        input_text = input_text.rstrip('/')
        # Get the last part of the URL
        return input_text.split('/')[-1]
    return input_text

def save_to_csv(profile_data, username):
    """Save profile data to separate CSV files for posts and reels."""
    try:
        # Save profile info
        profile_info = {k: v for k, v in profile_data.items() if k not in ['posts', 'reels']}
        pd.DataFrame([profile_info]).to_csv(f'{username}_profile_info.csv', index=False)
        print(f"✓ Saved profile info to {username}_profile_info.csv")
        
        # Save posts with detailed information
        if profile_data['posts']:
            # First save posts without comments
            posts_df = pd.DataFrame(profile_data['posts'])
            posts_df.drop('top_comments', axis=1, inplace=True)
            posts_df.to_csv(f'{username}_posts.csv', index=False)
            print(f"✓ Saved {len(profile_data['posts'])} posts to {username}_posts.csv")
            
            # Then save comments separately
            all_comments = []
            for post in profile_data['posts']:
                post_id = post['post_id']
                for comment in post['top_comments']:
                    comment['post_id'] = post_id
                    all_comments.append(comment)
            
            if all_comments:
                comments_df = pd.DataFrame(all_comments)
                comments_df.to_csv(f'{username}_comments.csv', index=False)
                print(f"✓ Saved comments to {username}_comments.csv")
        
        # Save reels with detailed information
        if profile_data['reels']:
            reels_df = pd.DataFrame(profile_data['reels'])
            reels_df.to_csv(f'{username}_reels.csv', index=False)
            print(f"✓ Saved {len(profile_data['reels'])} reels to {username}_reels.csv")
            
    except Exception as e:
        print(f"Error saving data to CSV: {str(e)}")

def main():
    # Create .env file if it doesn't exist
    if not os.path.exists('.env'):
        with open('.env', 'w') as f:
            f.write("APIFY_API_TOKEN=your_apify_token_here\n")
        print("Created .env file. Please update it with your Apify API token.")
        return

    try:
        scraper = InstagramScraper()
        
        # Get username to scrape
        input_text = input("Enter the Instagram username or URL to scrape: ")
        target_username = extract_username(input_text)
        
        print(f"\nScraping 5 most recent posts from @{target_username}...")
        # Scrape the profile
        profile_data = scraper.scrape_profile(target_username)
        
        if profile_data:
            # Save data to CSV files
            save_to_csv(profile_data, target_username)
            
            # Print summary
            print("\nProfile Summary:")
            print(f"Username: @{profile_data['username']}")
            print(f"Full Name: {profile_data['full_name']}")
            print(f"Followers: {profile_data['followers_count']:,}")
            print(f"Following: {profile_data['following_count']:,}")
            print(f"Total Posts: {profile_data['posts_count']:,}")
            print(f"Posts Scraped: {len(profile_data['posts']):,}")
            print(f"Reels Scraped: {len(profile_data['reels']):,}")
            
            if profile_data['posts'] or profile_data['reels']:
                print("\nContent Details:")
                if profile_data['posts']:
                    total_likes = sum(post['likes_count'] for post in profile_data['posts'])
                    total_comments = sum(post['comments_count'] for post in profile_data['posts'])
                    print(f"Posts Engagement: {total_likes:,} likes, {total_comments:,} comments")
                if profile_data['reels']:
                    total_reel_likes = sum(reel['likes_count'] for reel in profile_data['reels'])
                    total_reel_comments = sum(reel['comments_count'] for reel in profile_data['reels'])
                    print(f"Reels Engagement: {total_reel_likes:,} likes, {total_reel_comments:,} comments")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main() 