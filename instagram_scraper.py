from apify_client import ApifyClient
from dotenv import load_dotenv
import os
import pandas as pd
import time
import requests
import json
from concurrent.futures import ThreadPoolExecutor

class InstagramScraper:
    def __init__(self):
        load_dotenv()
        self.api_token = os.getenv('APIFY_API_TOKEN')
        if not self.api_token:
            raise ValueError("APIFY_API_TOKEN not found in .env file")
        self.client = ApifyClient(self.api_token)

    def scrape_profile(self, target_username):
        """Scrape Instagram profile information including 10 recent posts with details."""
        try:
            # Get profile and posts data
            run = self.client.actor("apify/instagram-scraper").call(run_input={
                "directUrls": [f"https://www.instagram.com/{target_username}/"],
                "resultsType": "posts",
                "resultsLimit": 10,  # Get 10 posts
                "addParentData": True,
                "searchType": "user",
                "searchLimit": 1,
                "proxy": {
                    "useApifyProxy": True,
                    "apifyProxyGroups": ["RESIDENTIAL"]
                },
                "maxRequestRetries": 5,
                "maxConcurrency": 1,
                "includeComments": True,  # Explicitly include comments
                "commentsLimit": 20  # Fetch comments
            })

            # Get the dataset ID from the run
            dataset_id = run['defaultDatasetId']
            print("Fetching profile and posts data...")
            time.sleep(20)
            
            # Fetch results
            items = list(self.client.dataset(dataset_id).iterate_items())
            
            if not items:
                print(f"No data found for username: {target_username}")
                return None

            # Process posts and reels
            posts_data = []
            reels_data = []
            
            for post in items[:10]:  # Process 10 posts
                # Print debug info about comments
                comment_count = len(post.get('comments', []))
                print(f"Post {post.get('shortCode')}: Found {comment_count} comments")
                
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
                            'timestamp': comment.get('timestamp', ''),
                            'likes_count': comment.get('likesCount', 0)
                        } 
                        for comment in post.get('comments', [])[:10]  # Just get first 10 comments
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

    def scrape_individual_post(self, post_url):
        """Scrape a single Instagram post including its comments."""
        try:
            print(f"Scraping individual post: {post_url}")
            
            # Run the post-specific scraper
            run = self.client.actor("apify/instagram-scraper").call(run_input={
                "directUrls": [post_url],
                "resultsType": "posts",
                "resultsLimit": 1,
                "proxy": {
                    "useApifyProxy": True,
                    "apifyProxyGroups": ["RESIDENTIAL"]
                },
                "maxRequestRetries": 5,
                "maxConcurrency": 1,
                "includeComments": True,
                "commentsLimit": 50,
                "verboseLog": True
            })
            
            # Get the dataset ID from the run
            dataset_id = run['defaultDatasetId']
            print("Waiting for post and comments data...")
            time.sleep(25)
            
            # Fetch results
            items = list(self.client.dataset(dataset_id).iterate_items())
            
            if not items:
                print(f"No data found for post: {post_url}")
                return None
                
            return items[0]
            
        except Exception as e:
            print(f"Error scraping individual post: {str(e)}")
            return None

def extract_username(input_text):
    """Extract username from URL or return as is if it's already a username."""
    if 'instagram.com' in input_text:
        # Remove trailing slash if present
        input_text = input_text.rstrip('/')
        # Get the last part of the URL
        return input_text.split('/')[-1]
    return input_text

def download_media(post_data, download_dir, content_type):
    """Download media (image, video, carousel) from Instagram post or reel."""
    try:
        post_id = post_data['post_id']
        shortcode = post_data['shortcode']
        
        # Create subfolder based on content type
        subfolder = os.path.join(download_dir, content_type)
        if not os.path.exists(subfolder):
            os.makedirs(subfolder)
            
        filename_base = f"{shortcode}"
        
        if content_type == 'reel' and 'video_url' in post_data and post_data['video_url']:
            # Download reel video
            video_url = post_data['video_url']
            filename = os.path.join(subfolder, f"{filename_base}.mp4")
            download_file(video_url, filename)
            post_data['downloaded_file'] = filename
            print(f"  ✓ Downloaded reel: {filename}")
            
        elif post_data['media_type'] == 'Carousel' and 'carousel_media' in post_data:
            # Download carousel items
            carousel_folder = os.path.join(subfolder, filename_base)
            if not os.path.exists(carousel_folder):
                os.makedirs(carousel_folder)
                
            # Download carousel items in parallel
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = []
                for i, media_url in enumerate(post_data['carousel_media']):
                    filename = os.path.join(carousel_folder, f"{i+1}.jpg")
                    futures.append(executor.submit(download_file, media_url, filename))
                
                # Wait for all downloads to complete
                for future in futures:
                    future.result()
                    
            post_data['downloaded_file'] = carousel_folder
            print(f"  ✓ Downloaded carousel: {carousel_folder}")
            
        else:
            # Download single image
            media_url = post_data['media_url']
            filename = os.path.join(subfolder, f"{filename_base}.jpg")
            download_file(media_url, filename)
            post_data['downloaded_file'] = filename
            print(f"  ✓ Downloaded image: {filename}")
            
    except Exception as e:
        print(f"  ✗ Error downloading media: {str(e)}")
        post_data['downloaded_file'] = None

def download_file(url, filename):
    """Download file from URL to specified filename."""
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        with open(filename, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
        return True
    except Exception as e:
        print(f"Error downloading {url}: {str(e)}")
        return False

def save_to_csv(profile_data, username):
    """Save profile data to separate CSV files for posts and reels."""
    try:
        # Save profile info
        profile_info = {k: v for k, v in profile_data.items() if k not in ['posts', 'reels']}
        pd.DataFrame([profile_info]).to_csv(f'{username}_profile_info.csv', index=False)
        print(f"✓ Saved profile info to {username}_profile_info.csv")
        
        # Create download directory
        download_dir = f"{username}_media"
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)
            
        # Save posts with detailed information
        if profile_data['posts']:
            # Prepare post data with comments
            posts_with_comments = []
            for post in profile_data['posts']:
                post_data = post.copy()
                # Convert top_comments to JSON string to save in same CSV
                post_data['top_comments_json'] = json.dumps(post_data['top_comments'])
                # Download the media
                download_media(post_data, download_dir, 'post')
                posts_with_comments.append(post_data)
            
            # Save posts with comments
            posts_df = pd.DataFrame(posts_with_comments)
            posts_df.drop('top_comments', axis=1, inplace=True)
            posts_df.to_csv(f'{username}_posts_with_comments.csv', index=False)
            print(f"✓ Saved {len(profile_data['posts'])} posts with comments to {username}_posts_with_comments.csv")
            
            # Print top comments for each post
            print("\nTop Comments for Posts:")
            for post in profile_data['posts']:
                print(f"\nPost: {post.get('caption', '')[:50]}...")
                if post['top_comments']:
                    for i, comment in enumerate(post['top_comments'], 1):
                        print(f"  {i}. @{comment['owner']}: {comment['text'][:100]}... ({comment['likes_count']} likes)")
                else:
                    print("  No comments found for this post")
        
        # Save reels with detailed information
        if profile_data['reels']:
            # Prepare reel data with comments
            reels_with_comments = []
            for reel in profile_data['reels']:
                reel_data = reel.copy()
                # Convert top_comments to JSON string to save in same CSV
                reel_data['top_comments_json'] = json.dumps(reel_data['top_comments'])
                # Download the media
                download_media(reel_data, download_dir, 'reel')
                reels_with_comments.append(reel_data)
            
            # Save reels with comments
            reels_df = pd.DataFrame(reels_with_comments)
            reels_df.drop('top_comments', axis=1, inplace=True)
            reels_df.to_csv(f'{username}_reels_with_comments.csv', index=False)
            print(f"✓ Saved {len(profile_data['reels'])} reels with comments to {username}_reels_with_comments.csv")
            
            # Print top comments for each reel
            print("\nTop Comments for Reels:")
            for reel in profile_data['reels']:
                print(f"\nReel: {reel.get('caption', '')[:50]}...")
                if reel['top_comments']:
                    for i, comment in enumerate(reel['top_comments'], 1):
                        print(f"  {i}. @{comment['owner']}: {comment['text'][:100]}... ({comment['likes_count']} likes)")
                else:
                    print("  No comments found for this reel")
            
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
        
        print(f"\nScraping 10 most recent posts from @{target_username}...")
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