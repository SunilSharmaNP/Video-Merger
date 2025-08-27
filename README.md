
# Video Merge Bot - Enhanced Version

A powerful Telegram bot for merging multiple videos into one, enhanced with features from AbirHasan2005's VideoMerge-Bot design.

## 🎬 Features

- **Merge Multiple Videos**: Combine 2 or more videos into a single file
- **Custom Thumbnail Support**: Set personalized thumbnails for merged videos
- **Cloud Upload**: Automatic upload to GoFile.io for large files
- **Broadcast System**: Send messages to all bot users (Admin only)
- **User Management**: Ban/unban users, view statistics
- **Smart Progress**: Real-time progress updates during merging
- **Multiple Formats**: Support for MP4, AVI, MOV, MKV, FLV, WMV
- **File Size Handling**: Up to 2GB per video file

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- FFmpeg installed on system
- Telegram Bot Token from @BotFather

### Installation

1. **Clone the repository**
git clone https://github.com/SunilSharmaNP/Video-Merger.git
cd Video-Merger

text

2. **Install dependencies**
pip install -r requirements.txt

text

3. **Set up environment variables**
cp .env.example .env

text
Edit .env with your configuration

4. **Run the bot**
python app.py

text

## 📋 Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `API_ID` | Telegram API ID | ✅ |
| `API_HASH` | Telegram API Hash | ✅ |
| `BOT_TOKEN` | Bot Token from BotFather | ✅ |
| `BOT_OWNER` | Your Telegram User ID | ✅ |
| `SUDO_USERS` | Admin user IDs (comma separated) | ❌ |
| `GOFILE_TOKEN` | GoFile.io API token | ❌ |
| `STREAMTAPE_API_USERNAME` | Streamtape username | ❌ |
| `STREAMTAPE_API_PASS` | Streamtape password | ❌ |

## 🐳 Docker Deployment

Build the image
docker build -t video-merge-bot .

Run the container
docker run -d --name video-merge-bot --env-file .env video-merge-bot

text

## 📖 Bot Commands

### User Commands
- `/start` - Start the bot and get welcome message
- `/help` - Show help information
- `/merge` - Merge uploaded videos
- `/cancel` - Cancel current operation
- `/set_thumbnail` - Set custom thumbnail
- `/del_thumbnail` - Delete custom thumbnail
- `/ping` - Test bot response

### Admin Commands
- `/broadcast` - Send message to all users
- `/ban` - Ban a user
- `/unban` - Unban a user

## 🔧 Usage

1. **Send Videos**: Upload 2 or more video files to the bot
2. **Set Thumbnail** (Optional): Reply to a photo with `/set_thumbnail`
3. **Merge**: Use `/merge` command or click the merge button
4. **Download**: Get your merged video instantly!

## 📞 Support

If you have any questions or issues, please create an issue on GitHub.

## 📄 License

This project is licensed under the MIT License.
