# Instagram Profile Scraper

A Python-based Instagram profile scraper that uses the Apify API to collect information from Instagram profiles.

## Features

- Scrape Instagram profile information using Apify API
- Collect detailed profile data including followers, following, posts, and more
- Fetch up to 10 most recent posts and reels with their top 10 comments
- Automatically download media (images, videos, carousels) from posts and reels
- Save data to CSV format
- Secure API token management using environment variables

## Prerequisites

- Python 3.8 or higher
- Apify API token (get one at https://apify.com)

## Installation

1. Clone this repository:

```bash
git clone <your-repository-url>
cd instagram-scrapping
```

2. Install the required packages:

```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the project root and add your Apify API token:

```
APIFY_API_TOKEN=your_apify_token_here
```

## Usage

Run the script:

```bash
python instagram_scraper.py
```

The script will:

1. Prompt you to enter an Instagram username to scrape
2. Use Apify API to fetch the profile information
3. Save the data to a CSV file named `{username}_profile_data.csv`
4. Display the scraped data in the console

## Output

The script generates the following files:

1. `{username}_profile_info.csv` - Basic profile information:
   - Username
   - Follower count
   - Following count
   - Post count
   - Full name
   - Biography
   - Private account status
   - Verification status
   - Profile picture URL
   - External URL

2. `{username}_posts_with_comments.csv` - Post data with top comments included
   - Post details (ID, shortcode, caption, likes, etc.)
   - Top 10 comments for each post stored as JSON

3. `{username}_reels_with_comments.csv` - Reel data with top comments included
   - Reel details (ID, shortcode, caption, likes, video URL, etc.)
   - Top 10 comments for each reel stored as JSON

4. `{username}_media/` - Directory containing downloaded media files:
   - Posts subfolder with images and carousel content
   - Reels subfolder with video content

## Notes

- This scraper uses the Apify Instagram Profile Scraper actor
- Make sure you have sufficient credits in your Apify account
- The API has rate limits based on your Apify plan
- Use responsibly and in accordance with Instagram's terms of service

## License

This project is licensed under the MIT License - see the LICENSE file for details.
