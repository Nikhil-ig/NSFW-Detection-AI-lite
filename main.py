# import os
# import logging
# import uuid
# import json
# import cv2
# from PIL import Image, ImageSequence
# from nudenet import NudeDetector
# from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
# from telegram.ext import (ApplicationBuilder, MessageHandler, ContextTypes,
#                           filters, CommandHandler, CallbackQueryHandler)
# from flask import Flask, Response
# import threading

# # Initialize Flask server for uptime monitoring
# server = Flask(__name__)


# @server.route('/')
# def home():
#     return Response("🤖 NSFW Detection Bot is running", status=200)


# def run_flask():
#     server.run(host='0.0.0.0', port=8080)


# # Enhanced logging configuration
# logging.basicConfig(
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
#     level=logging.INFO,
#     handlers=[logging.StreamHandler()])
# logger = logging.getLogger(__name__)

# # Configuration
# DOWNLOAD_DIR = "downloads"
# os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# # Default configuration
# DEFAULT_CONFIG = {
#     "NSFW_THRESHOLD": 0.45,
#     "SAFE_THRESHOLD": 0.25,
#     "FRAME_ANALYSIS_COUNT": 3,
#     "MIN_DETECTION_CONFIDENCE": 0.25,
#     "IGNORE_ADMINS": True,
#     "MODEL_SELECTION": "nudenet"  # Only using NudeNet now
# }

# # NSFW classes with strict filtering
# STRICT_NSFW_CLASSES = {
#     'FEMALE_GENITALIA_EXPOSED', 'MALE_GENITALIA_EXPOSED', 'ANUS_EXPOSED',
#     'PUBIC_HAIR_EXPOSED', 'AREOLA_EXPOSED', 'NIPPLE_EXPOSED',
#     'BUTTOCKS_EXPOSED', 'FEMALE_BREAST_EXPOSED', 'UNDERWEAR_VISIBLE_EXPLICIT',
#     'CLOTHING_SEE_THROUGH', 'WET_CLOTHING_EXPLICIT', 'EXPOSED_CHEST_MALE',
#     'EXPOSED_CHEST_FEMALE', 'EXPOSED_THIGHS_EXPLICIT', 'EXPOSED_BACK_EXPLICIT',
#     'EXPOSED_STOMACH_EXPLICIT', 'EXPOSED_LEGS_EXPLICIT', 'NAKED_BODY_EXPLICIT',
#     'EXPOSED_ARMPIT_EXPLICIT', 'EXPOSED_FEET_FETISH',
#     'CLOTHING_RIPPED_EXPLICIT', 'TOPLESS_EXPLICIT', 'BOTTOMLESS_EXPLICIT',
#     'EXPOSED_BUTTOCKS_CLEAVAGE', 'EXPOSED_BREAST_CLEAVAGE',
#     'EXPOSED_UPPER_BODY_EXPLICIT', 'EXPOSED_LOWER_BODY_EXPLICIT',
#     'PARTIAL_NUDITY_EXPLICIT', 'SEXUAL_INTERCOURSE', 'ORAL_SEX_ACTIVE',
#     'ANAL_SEX_ACTIVE', 'MASTURBATION_EXPLICIT', 'SEX_TOYS_VISIBLE',
#     'PORNOGRAPHIC_POSES', 'GROUP_SEX_ACTIVITY', 'BDSM_EQUIPMENT',
#     'FETISH_ACTIVITY_EXPLICIT', 'DOMINATION_ACT', 'SUBMISSION_ACT',
#     'BONDAGE_ACT'
# }

# # Safe content indicators
# SAFE_CONTENT_INDICATORS = {
#     'FAMILY_GATHERING', 'CHILDREN_PLAYING', 'BABY_CARE', 'SCHOOL_ACTIVITY',
#     'DANCE_PERFORMANCE', 'SPORTS_EVENT', 'GYM_WORKOUT', 'YOGA_PRACTICE',
#     'SWIMMING_COMPETITION', 'BEACH_ACTIVITIES', 'MEDICAL_EXAM',
#     'BREASTFEEDING', 'FULLY_COVERED_BODY', 'PROFESSIONAL_UNIFORM',
#     'SPORTS_UNIFORM', 'SWIMSUIT_NON_SEXUAL', 'UNDERWEAR_NON_EXPLICIT',
#     'CULTURAL_ATTIRE'
# }

# # Initialize NudeNet detector
# logger.info("⚙️ Loading NudeNet detection model...")
# nude_detector = NudeDetector()


# # Configuration management
# def load_group_config(chat_id: int) -> dict:
#     """Load configuration for a specific group"""
#     config_file = f"config_{chat_id}.json"
#     try:
#         with open(config_file, 'r') as f:
#             return json.load(f)
#     except (FileNotFoundError, json.JSONDecodeError):
#         config = DEFAULT_CONFIG.copy()
#         config['chat_id'] = chat_id
#         return config


# def save_group_config(chat_id: int, config: dict):
#     """Save configuration for a specific group"""
#     config_file = f"config_{chat_id}.json"
#     with open(config_file, 'w') as f:
#         json.dump(config, f, indent=4)


# # Admin verification
# async def is_group_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     user = update.effective_user
#     chat = update.effective_chat
#     if chat.type == 'private':
#         return False
#     try:
#         admins = await context.bot.get_chat_administrators(chat.id)
#         return any(admin.user.id == user.id for admin in admins)
#     except:
#         return False


# # Detection functions
# def detect_nsfw_nudenet(image_path: str, chat_id: int) -> tuple[bool, float]:
#     config = load_group_config(chat_id)
#     try:
#         detections = nude_detector.detect(image_path)
#         valid_detections = [
#             det for det in detections if det['class'] in STRICT_NSFW_CLASSES
#             and det['score'] >= config['MIN_DETECTION_CONFIDENCE']
#         ]

#         if not valid_detections:
#             return False, 0.0

#         max_detection = max(valid_detections, key=lambda x: x['score'])
#         confidence = max_detection['score']

#         if max_detection['class'] in {
#                 'FEMALE_BREAST_EXPOSED', 'BUTTOCKS_EXPOSED'
#         }:
#             if confidence < 0.65:
#                 return False, confidence * 0.5

#         return confidence > config['NSFW_THRESHOLD'], confidence
#     except Exception as e:
#         logger.error(f"🔞 NudeNet detection failed: {str(e)}")
#         return False, 0.0


# def detect_safe_content(image_path: str) -> bool:
#     try:
#         detections = nude_detector.detect(image_path)
#         safe_detections = [
#             det for det in detections
#             if det['class'] in SAFE_CONTENT_INDICATORS and det['score'] >= 0.4
#         ]
#         return len(safe_detections) > 0
#     except Exception as e:
#         logger.error(f"🌿 Safe content detection failed: {str(e)}")
#         return False


# def analyze_frames(file_path: str, chat_id: int) -> float:
#     config = load_group_config(chat_id)
#     max_confidence = 0.0
#     frame_count = 0

#     try:
#         if file_path.endswith(('.webm', '.mp4')):
#             vid = cv2.VideoCapture(file_path)
#             total_frames = int(vid.get(cv2.CAP_PROP_FRAME_COUNT))
#             frame_step = max(1, total_frames // config['FRAME_ANALYSIS_COUNT'])

#             for i in range(config['FRAME_ANALYSIS_COUNT']):
#                 vid.set(cv2.CAP_PROP_POS_FRAMES, i * frame_step)
#                 success, frame = vid.read()
#                 if success:
#                     frame_path = f"{file_path}_frame_{i}.jpg"
#                     cv2.imwrite(frame_path, frame)

#                     if detect_safe_content(frame_path):
#                         os.remove(frame_path)
#                         continue

#                     _, confidence = detect_nsfw_nudenet(frame_path, chat_id)
#                     max_confidence = max(max_confidence, confidence)
#                     os.remove(frame_path)
#                     frame_count += 1

#                     if max_confidence > 0.95:
#                         break
#             vid.release()

#         elif file_path.endswith('.gif'):
#             with Image.open(file_path) as img:
#                 total_frames = img.n_frames
#                 frame_step = max(
#                     1, total_frames // config['FRAME_ANALYSIS_COUNT'])

#                 for i in range(config['FRAME_ANALYSIS_COUNT']):
#                     img.seek(i * frame_step)
#                     frame_path = f"{file_path}_frame_{i}.jpg"
#                     img.convert('RGB').save(frame_path)

#                     if detect_safe_content(frame_path):
#                         os.remove(frame_path)
#                         continue

#                     _, confidence = detect_nsfw_nudenet(frame_path, chat_id)
#                     max_confidence = max(max_confidence, confidence)
#                     os.remove(frame_path)
#                     frame_count += 1

#                     if max_confidence > 0.95:
#                         break

#         if frame_count > 0 and max_confidence < config['NSFW_THRESHOLD']:
#             safe_frame_ratio = (config['FRAME_ANALYSIS_COUNT'] -
#                                 frame_count) / config['FRAME_ANALYSIS_COUNT']
#             if safe_frame_ratio > 0.7:
#                 max_confidence *= 0.7

#         return max_confidence
#     except Exception as e:
#         logger.error(f"🎞 Frame analysis failed: {str(e)}")
#         return 0.0


# # Command handlers
# async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     await update.message.reply_text(
#         "🚀 NSFW Detection Bot is running!\n"
#         "I automatically analyze photos, videos, GIFs and stickers for explicit content.\n\n"
#         "Commands:\n"
#         "/settings - Configure group settings (admins only)\n"
#         "/help - Show help information")


# async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     await update.message.reply_text(
#         "ℹ️ NSFW Detection Bot Help\n\n"
#         "I analyze these media types:\n"
#         "- Photos (sent as photo or document)\n"
#         "- Videos (up to 20MB)\n"
#         "- GIFs\n"
#         "- Static and animated stickers\n\n"
#         "Admin commands:\n"
#         "/settings - Configure detection parameters\n"
#         "\n"
#         "This bot automatically detects and removes NSFW content.")


# async def group_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     if not await is_group_admin(update, context):
#         return

#     chat_id = update.effective_chat.id
#     config = load_group_config(chat_id)

#     keyboard = [
#         [
#             InlineKeyboardButton(
#                 f"🔞 NSFW Threshold ({config['NSFW_THRESHOLD']:.2f})",
#                 callback_data='set_nsfw')
#         ],
#         [
#             InlineKeyboardButton(
#                 f"✅ Safe Threshold ({config['SAFE_THRESHOLD']:.2f})",
#                 callback_data='set_safe')
#         ],
#         [
#             InlineKeyboardButton(
#                 f"🎞 Frames Analyzed ({config['FRAME_ANALYSIS_COUNT']})",
#                 callback_data='set_frames')
#         ],
#         [
#             InlineKeyboardButton(
#                 f"🎯 Min Confidence ({config['MIN_DETECTION_CONFIDENCE']:.2f})",
#                 callback_data='set_confidence')
#         ],
#         [
#             InlineKeyboardButton(
#                 f"👑 Ignore Admins ({'ON' if config['IGNORE_ADMINS'] else 'OFF'})",
#                 callback_data='toggle_ignore')
#         ], [InlineKeyboardButton("❌ Close Menu", callback_data='close_menu')]
#     ]

#     await update.message.reply_text(
#         "⚙️ Group Settings Panel ⚙️\nChoose a setting to modify:",
#         reply_markup=InlineKeyboardMarkup(keyboard))


# async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     query = update.callback_query
#     await query.answer()

#     chat_id = query.message.chat.id

#     if not await is_group_admin(update, context):
#         await query.edit_message_text("❌ Only admins can modify settings")
#         return

#     config = load_group_config(chat_id)

#     if query.data == 'close_menu':
#         await query.message.delete()
#         return

#     elif query.data == 'toggle_ignore':
#         config['IGNORE_ADMINS'] = not config['IGNORE_ADMINS']
#         save_group_config(chat_id, config)
#         await query.edit_message_text(
#             f"✅ Admin ignoring {'enabled' if config['IGNORE_ADMINS'] else 'disabled'}",
#             reply_markup=InlineKeyboardMarkup([[
#                 InlineKeyboardButton("🔙 Back to Settings",
#                                      callback_data='settings_main')
#             ]]))
#         return

#     elif query.data.startswith('set_'):
#         setting = query.data[4:]
#         context.user_data['awaiting_setting'] = {
#             'chat_id': chat_id,
#             'setting': setting,
#             'message_id': query.message.message_id
#         }

#         await query.edit_message_text(
#             f"Enter new value for {setting.replace('_', ' ')} (current: {config[setting]}):\n\n"
#             f"• For thresholds, enter value between 0.0 and 1.0\n"
#             f"• For frames, enter number between 1 and 10")


# async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     if 'awaiting_setting' not in context.user_data:
#         return

#     setting_data = context.user_data.pop('awaiting_setting')
#     chat_id = setting_data['chat_id']
#     setting = setting_data['setting']
#     message_id = setting_data['message_id']

#     try:
#         config = load_group_config(chat_id)

#         if setting == 'FRAME_ANALYSIS_COUNT':
#             value = int(update.message.text)
#             if not (1 <= value <= 10):
#                 raise ValueError("Frames must be between 1 and 10")
#         else:
#             value = float(update.message.text)
#             if not (0 <= value <= 1):
#                 raise ValueError("Threshold must be between 0.0 and 1.0")

#         config[setting] = value
#         save_group_config(chat_id, config)

#         await update.message.reply_text(
#             f"✅ {setting.replace('_', ' ')} updated to {value}")

#         # Return to settings menu
#         config = load_group_config(chat_id)
#         keyboard = [
#             [
#                 InlineKeyboardButton(
#                     f"🔞 NSFW Threshold ({config['NSFW_THRESHOLD']:.2f})",
#                     callback_data='set_nsfw')
#             ],
#             [
#                 InlineKeyboardButton(
#                     f"✅ Safe Threshold ({config['SAFE_THRESHOLD']:.2f})",
#                     callback_data='set_safe')
#             ],
#             [
#                 InlineKeyboardButton(
#                     f"🎞 Frames Analyzed ({config['FRAME_ANALYSIS_COUNT']})",
#                     callback_data='set_frames')
#             ],
#             [
#                 InlineKeyboardButton(
#                     f"🎯 Min Confidence ({config['MIN_DETECTION_CONFIDENCE']:.2f})",
#                     callback_data='set_confidence')
#             ],
#             [
#                 InlineKeyboardButton(
#                     f"👑 Ignore Admins ({'ON' if config['IGNORE_ADMINS'] else 'OFF'})",
#                     callback_data='toggle_ignore')
#             ],
#             [InlineKeyboardButton("❌ Close Menu", callback_data='close_menu')]
#         ]

#         await context.bot.send_message(
#             chat_id=chat_id,
#             text="⚙️ Group Settings Panel ⚙️\nChoose a setting to modify:",
#             reply_markup=InlineKeyboardMarkup(keyboard))

#     except ValueError as e:
#         await update.message.reply_text(f"❌ Invalid value: {str(e)}")
#         context.user_data['awaiting_setting'] = setting_data
#     except Exception as e:
#         await update.message.reply_text(
#             "❌ Failed to update setting. Please try again.")
#         logger.error(f"Error updating setting: {str(e)}")


# async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     try:
#         message = update.effective_message
#         chat_id = message.chat.id
#         config = load_group_config(chat_id)

#         if config['IGNORE_ADMINS'] and await is_group_admin(update, context):
#             logger.info("👑 Admin content ignored")
#             return

#         file = None
#         is_video = False
#         media_type = "unknown"

#         if message.photo:
#             file = await message.photo[-1].get_file()
#             media_type = "photo"
#         elif message.sticker:
#             if message.sticker.is_animated:
#                 logger.info("⚠️ Analyzing animated sticker frames")
#                 file = await message.sticker.get_file()
#                 media_type = "animated_sticker"
#                 is_video = True
#             else:
#                 file = await message.sticker.get_file()
#                 media_type = "sticker"
#         elif message.animation:
#             file = await message.animation.get_file()
#             media_type = "animation"
#             is_video = True
#         elif message.document:
#             if message.document.mime_type.startswith('image/'):
#                 file = await message.document.get_file()
#                 media_type = "image_document"
#             elif message.document.mime_type.startswith('video/'):
#                 file = await message.document.get_file()
#                 media_type = "video_document"
#                 is_video = True
#             else:
#                 logger.info(
#                     f"⚠️ Unsupported document type: {message.document.mime_type}"
#                 )
#                 return

#         if not file:
#             logger.warning("⚠️ No file found in message")
#             return

#         file_ext = os.path.splitext(
#             file.file_path)[1] if file.file_path else '.jpg'
#         file_id = str(uuid.uuid4())
#         file_path = os.path.join(DOWNLOAD_DIR, f"{file_id}{file_ext}")

#         logger.info(
#             f"⬇️ Downloading {media_type} (size: {file.file_size or 'unknown'} bytes)"
#         )
#         await file.download_to_drive(custom_path=file_path)

#         analysis_msg = await message.reply_text(
#             f"🔍 Analyzing {media_type}..." if not is_video else
#             f"🎬 Analyzing {config['FRAME_ANALYSIS_COUNT']} frames from {media_type}..."
#         )

#         try:
#             if is_video or file_ext in ['.gif', '.webm', '.mp4']:
#                 confidence = analyze_frames(file_path, chat_id)
#                 is_nsfw_content = confidence > config['NSFW_THRESHOLD']
#             else:
#                 is_nsfw_content, confidence = detect_nsfw_nudenet(
#                     file_path, chat_id)

#             if is_nsfw_content and confidence > config['NSFW_THRESHOLD']:
#                 await message.delete()
#                 logger.info(
#                     f"🚫 Deleted NSFW content (Confidence: {confidence:.2%})")

#                 warning_msg = (f"⚠️ Removed explicit content\n"
#                                f"Confidence: {confidence:.2%}\n"
#                                f"Media type: {media_type}\n\n"
#                                f"*This action was performed automatically*")

#                 await message.chat.send_message(
#                     warning_msg,
#                     reply_to_message_id=message.message_id
#                     if message.chat.type != 'private' else None)
#             else:
#                 logger.info(f"✅ Safe content (Confidence: {confidence:.2%})")
#                 await analysis_msg.edit_text(f"✅ Content approved\n"
#                                              f"Confidence: {confidence:.2%}")

#         except Exception as e:
#             logger.error(f"❌ Analysis failed: {str(e)}")
#             await analysis_msg.edit_text("❌ Analysis failed. Please try again."
#                                          )

#         finally:
#             if os.path.exists(file_path):
#                 os.remove(file_path)

#     except Exception as e:
#         logger.error(f"🔥 Critical error in media handler: {str(e)}")
#         if 'analysis_msg' in locals():
#             await analysis_msg.edit_text(
#                 "❌ An error occurred during processing")


# def main():
#     try:
#         bot_token = "7803429144:AAFXixTN0-Gb2eX1GE2KJnlTHdvfJBLrlnM" #os.environ.get("BOT_TOKEN")

#         # Start Flask server in a thread
#         threading.Thread(target=run_flask, daemon=True).start()

#         app = ApplicationBuilder() \
#             .token(bot_token) \
#             .build()

#         # Command handlers
#         app.add_handler(CommandHandler("start", start))
#         app.add_handler(CommandHandler("help", help_command))
#         app.add_handler(CommandHandler("settings", group_settings))

#         # Button handler
#         app.add_handler(CallbackQueryHandler(handle_button))

#         # Message handlers
#         app.add_handler(
#             MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

#         # Media handler
#         media_filter = (filters.PHOTO | filters.Document.IMAGE
#                         | filters.Document.VIDEO | filters.Sticker.ALL
#                         | filters.ANIMATION)
#         app.add_handler(MessageHandler(media_filter, handle_media))

#         logger.info("🤖 Starting Lite NSFW Detection Bot...")
#         logger.info("📸 Monitoring: Photos | Videos | GIFs | Stickers")

#         app.run_polling(poll_interval=1.0,
#                         timeout=30,
#                         drop_pending_updates=True)

#     except Exception as e:
#         logger.critical(f"💥 Fatal error during startup: {str(e)}")
#         raise


# if __name__ == "__main__":
#     try:
#         import asyncio
#         os.makedirs(DOWNLOAD_DIR, exist_ok=True)
#         asyncio.run(main())
#     except KeyboardInterrupt:
#         logger.info("🛑 Bot stopped by user")
#     except Exception as e:
#         logger.critical(f"💥 Critical error: {str(e)}")







import os
import logging
import uuid
import json
import cv2
from PIL import Image, ImageSequence
from nudenet import NudeDetector
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (ApplicationBuilder, MessageHandler, ContextTypes,
                          filters, CommandHandler, CallbackQueryHandler)
from flask import Flask, Response
import threading

# Initialize Flask server for uptime monitoring
app = Flask(__name__)

@app.route('/')
def home():
    return Response("🤖 NSFW Detection Bot is running", status=200)

def run_flask():
    app.run(host='0.0.0.0', port=10000)  # Changed port to 10000 for Render compatibility

# Enhanced logging configuration
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[logging.StreamHandler()])
logger = logging.getLogger(__name__)

# Configuration - using environment variables for Render
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Default configuration
DEFAULT_CONFIG = {
    "NSFW_THRESHOLD": 0.45,
    "SAFE_THRESHOLD": 0.25,
    "FRAME_ANALYSIS_COUNT": 3,
    "MIN_DETECTION_CONFIDENCE": 0.25,
    "IGNORE_ADMINS": True,
    "MODEL_SELECTION": "nudenet"
}

# NSFW classes with strict filtering
STRICT_NSFW_CLASSES = {
    'FEMALE_GENITALIA_EXPOSED', 'MALE_GENITALIA_EXPOSED', 'ANUS_EXPOSED',
    'PUBIC_HAIR_EXPOSED', 'AREOLA_EXPOSED', 'NIPPLE_EXPOSED',
    'BUTTOCKS_EXPOSED', 'FEMALE_BREAST_EXPOSED', 'UNDERWEAR_VISIBLE_EXPLICIT',
    'CLOTHING_SEE_THROUGH', 'WET_CLOTHING_EXPLICIT', 'EXPOSED_CHEST_MALE',
    'EXPOSED_CHEST_FEMALE', 'EXPOSED_THIGHS_EXPLICIT', 'EXPOSED_BACK_EXPLICIT',
    'EXPOSED_STOMACH_EXPLICIT', 'EXPOSED_LEGS_EXPLICIT', 'NAKED_BODY_EXPLICIT',
    'EXPOSED_ARMPIT_EXPLICIT', 'EXPOSED_FEET_FETISH',
    'CLOTHING_RIPPED_EXPLICIT', 'TOPLESS_EXPLICIT', 'BOTTOMLESS_EXPLICIT',
    'EXPOSED_BUTTOCKS_CLEAVAGE', 'EXPOSED_BREAST_CLEAVAGE',
    'EXPOSED_UPPER_BODY_EXPLICIT', 'EXPOSED_LOWER_BODY_EXPLICIT',
    'PARTIAL_NUDITY_EXPLICIT', 'SEXUAL_INTERCOURSE', 'ORAL_SEX_ACTIVE',
    'ANAL_SEX_ACTIVE', 'MASTURBATION_EXPLICIT', 'SEX_TOYS_VISIBLE',
    'PORNOGRAPHIC_POSES', 'GROUP_SEX_ACTIVITY', 'BDSM_EQUIPMENT',
    'FETISH_ACTIVITY_EXPLICIT', 'DOMINATION_ACT', 'SUBMISSION_ACT',
    'BONDAGE_ACT'
}

# Safe content indicators
SAFE_CONTENT_INDICATORS = {
    'FAMILY_GATHERING', 'CHILDREN_PLAYING', 'BABY_CARE', 'SCHOOL_ACTIVITY',
    'DANCE_PERFORMANCE', 'SPORTS_EVENT', 'GYM_WORKOUT', 'YOGA_PRACTICE',
    'SWIMMING_COMPETITION', 'BEACH_ACTIVITIES', 'MEDICAL_EXAM',
    'BREASTFEEDING', 'FULLY_COVERED_BODY', 'PROFESSIONAL_UNIFORM',
    'SPORTS_UNIFORM', 'SWIMSUIT_NON_SEXUAL', 'UNDERWEAR_NON_EXPLICIT',
    'CULTURAL_ATTIRE'
}

# Initialize NudeNet detector
logger.info("⚙️ Loading NudeNet detection model...")
nude_detector = NudeDetector()

# Configuration management
def load_group_config(chat_id: int) -> dict:
    """Load configuration for a specific group"""
    config_file = f"config_{chat_id}.json"
    try:
        with open(config_file, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        config = DEFAULT_CONFIG.copy()
        config['chat_id'] = chat_id
        return config

def save_group_config(chat_id: int, config: dict):
    """Save configuration for a specific group"""
    config_file = f"config_{chat_id}.json"
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=4)

# Admin verification
async def is_group_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    if chat.type == 'private':
        return False
    try:
        admins = await context.bot.get_chat_administrators(chat.id)
        return any(admin.user.id == user.id for admin in admins)
    except:
        return False

# Detection functions
def detect_nsfw_nudenet(image_path: str, chat_id: int) -> tuple[bool, float]:
    config = load_group_config(chat_id)
    try:
        detections = nude_detector.detect(image_path)
        valid_detections = [
            det for det in detections if det['class'] in STRICT_NSFW_CLASSES
            and det['score'] >= config['MIN_DETECTION_CONFIDENCE']
        ]

        if not valid_detections:
            return False, 0.0

        max_detection = max(valid_detections, key=lambda x: x['score'])
        confidence = max_detection['score']

        if max_detection['class'] in {
                'FEMALE_BREAST_EXPOSED', 'BUTTOCKS_EXPOSED'
        }:
            if confidence < 0.65:
                return False, confidence * 0.5

        return confidence > config['NSFW_THRESHOLD'], confidence
    except Exception as e:
        logger.error(f"🔞 NudeNet detection failed: {str(e)}")
        return False, 0.0

def detect_safe_content(image_path: str) -> bool:
    try:
        detections = nude_detector.detect(image_path)
        safe_detections = [
            det for det in detections
            if det['class'] in SAFE_CONTENT_INDICATORS and det['score'] >= 0.4
        ]
        return len(safe_detections) > 0
    except Exception as e:
        logger.error(f"🌿 Safe content detection failed: {str(e)}")
        return False

def analyze_frames(file_path: str, chat_id: int) -> float:
    config = load_group_config(chat_id)
    max_confidence = 0.0
    frame_count = 0

    try:
        if file_path.endswith(('.webm', '.mp4')):
            vid = cv2.VideoCapture(file_path)
            total_frames = int(vid.get(cv2.CAP_PROP_FRAME_COUNT))
            frame_step = max(1, total_frames // config['FRAME_ANALYSIS_COUNT'])

            for i in range(config['FRAME_ANALYSIS_COUNT']):
                vid.set(cv2.CAP_PROP_POS_FRAMES, i * frame_step)
                success, frame = vid.read()
                if success:
                    frame_path = f"{file_path}_frame_{i}.jpg"
                    cv2.imwrite(frame_path, frame)

                    if detect_safe_content(frame_path):
                        os.remove(frame_path)
                        continue

                    _, confidence = detect_nsfw_nudenet(frame_path, chat_id)
                    max_confidence = max(max_confidence, confidence)
                    os.remove(frame_path)
                    frame_count += 1

                    if max_confidence > 0.95:
                        break
            vid.release()

        elif file_path.endswith('.gif'):
            with Image.open(file_path) as img:
                total_frames = img.n_frames
                frame_step = max(
                    1, total_frames // config['FRAME_ANALYSIS_COUNT'])

                for i in range(config['FRAME_ANALYSIS_COUNT']):
                    img.seek(i * frame_step)
                    frame_path = f"{file_path}_frame_{i}.jpg"
                    img.convert('RGB').save(frame_path)

                    if detect_safe_content(frame_path):
                        os.remove(frame_path)
                        continue

                    _, confidence = detect_nsfw_nudenet(frame_path, chat_id)
                    max_confidence = max(max_confidence, confidence)
                    os.remove(frame_path)
                    frame_count += 1

                    if max_confidence > 0.95:
                        break

        if frame_count > 0 and max_confidence < config['NSFW_THRESHOLD']:
            safe_frame_ratio = (config['FRAME_ANALYSIS_COUNT'] -
                                frame_count) / config['FRAME_ANALYSIS_COUNT']
            if safe_frame_ratio > 0.7:
                max_confidence *= 0.7

        return max_confidence
    except Exception as e:
        logger.error(f"🎞 Frame analysis failed: {str(e)}")
        return 0.0

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚀 NSFW Detection Bot is running!\n"
        "I automatically analyze photos, videos, GIFs and stickers for explicit content.\n\n"
        "Commands:\n"
        "/settings - Configure group settings (admins only)\n"
        "/help - Show help information")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ℹ️ NSFW Detection Bot Help\n\n"
        "I analyze these media types:\n"
        "- Photos (sent as photo or document)\n"
        "- Videos (up to 20MB)\n"
        "- GIFs\n"
        "- Static and animated stickers\n\n"
        "Admin commands:\n"
        "/settings - Configure detection parameters\n"
        "\n"
        "This bot automatically detects and removes NSFW content.")

async def group_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_group_admin(update, context):
        return

    chat_id = update.effective_chat.id
    config = load_group_config(chat_id)

    keyboard = [
        [
            InlineKeyboardButton(
                f"🔞 NSFW Threshold ({config['NSFW_THRESHOLD']:.2f})",
                callback_data='set_nsfw')
        ],
        [
            InlineKeyboardButton(
                f"✅ Safe Threshold ({config['SAFE_THRESHOLD']:.2f})",
                callback_data='set_safe')
        ],
        [
            InlineKeyboardButton(
                f"🎞 Frames Analyzed ({config['FRAME_ANALYSIS_COUNT']})",
                callback_data='set_frames')
        ],
        [
            InlineKeyboardButton(
                f"🎯 Min Confidence ({config['MIN_DETECTION_CONFIDENCE']:.2f})",
                callback_data='set_confidence')
        ],
        [
            InlineKeyboardButton(
                f"👑 Ignore Admins ({'ON' if config['IGNORE_ADMINS'] else 'OFF'})",
                callback_data='toggle_ignore')
        ], [InlineKeyboardButton("❌ Close Menu", callback_data='close_menu')]
    ]

    await update.message.reply_text(
        "⚙️ Group Settings Panel ⚙️\nChoose a setting to modify:",
        reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat.id

    if not await is_group_admin(update, context):
        await query.edit_message_text("❌ Only admins can modify settings")
        return

    config = load_group_config(chat_id)

    if query.data == 'close_menu':
        await query.message.delete()
        return

    elif query.data == 'toggle_ignore':
        config['IGNORE_ADMINS'] = not config['IGNORE_ADMINS']
        save_group_config(chat_id, config)
        await query.edit_message_text(
            f"✅ Admin ignoring {'enabled' if config['IGNORE_ADMINS'] else 'disabled'}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Back to Settings",
                                     callback_data='settings_main')
            ]]))
        return

    elif query.data.startswith('set_'):
        setting = query.data[4:]
        context.user_data['awaiting_setting'] = {
            'chat_id': chat_id,
            'setting': setting,
            'message_id': query.message.message_id
        }

        await query.edit_message_text(
            f"Enter new value for {setting.replace('_', ' ')} (current: {config[setting]}):\n\n"
            f"• For thresholds, enter value between 0.0 and 1.0\n"
            f"• For frames, enter number between 1 and 10")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'awaiting_setting' not in context.user_data:
        return

    setting_data = context.user_data.pop('awaiting_setting')
    chat_id = setting_data['chat_id']
    setting = setting_data['setting']
    message_id = setting_data['message_id']

    try:
        config = load_group_config(chat_id)

        if setting == 'FRAME_ANALYSIS_COUNT':
            value = int(update.message.text)
            if not (1 <= value <= 10):
                raise ValueError("Frames must be between 1 and 10")
        else:
            value = float(update.message.text)
            if not (0 <= value <= 1):
                raise ValueError("Threshold must be between 0.0 and 1.0")

        config[setting] = value
        save_group_config(chat_id, config)

        await update.message.reply_text(
            f"✅ {setting.replace('_', ' ')} updated to {value}")

        # Return to settings menu
        config = load_group_config(chat_id)
        keyboard = [
            [
                InlineKeyboardButton(
                    f"🔞 NSFW Threshold ({config['NSFW_THRESHOLD']:.2f})",
                    callback_data='set_nsfw')
            ],
            [
                InlineKeyboardButton(
                    f"✅ Safe Threshold ({config['SAFE_THRESHOLD']:.2f})",
                    callback_data='set_safe')
            ],
            [
                InlineKeyboardButton(
                    f"🎞 Frames Analyzed ({config['FRAME_ANALYSIS_COUNT']})",
                    callback_data='set_frames')
            ],
            [
                InlineKeyboardButton(
                    f"🎯 Min Confidence ({config['MIN_DETECTION_CONFIDENCE']:.2f})",
                    callback_data='set_confidence')
            ],
            [
                InlineKeyboardButton(
                    f"👑 Ignore Admins ({'ON' if config['IGNORE_ADMINS'] else 'OFF'})",
                    callback_data='toggle_ignore')
            ],
            [InlineKeyboardButton("❌ Close Menu", callback_data='close_menu')]
        ]

        await context.bot.send_message(
            chat_id=chat_id,
            text="⚙️ Group Settings Panel ⚙️\nChoose a setting to modify:",
            reply_markup=InlineKeyboardMarkup(keyboard))

    except ValueError as e:
        await update.message.reply_text(f"❌ Invalid value: {str(e)}")
        context.user_data['awaiting_setting'] = setting_data
    except Exception as e:
        await update.message.reply_text(
            "❌ Failed to update setting. Please try again.")
        logger.error(f"Error updating setting: {str(e)}")

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        message = update.effective_message
        chat_id = message.chat.id
        config = load_group_config(chat_id)

        if config['IGNORE_ADMINS'] and await is_group_admin(update, context):
            logger.info("👑 Admin content ignored")
            return

        file = None
        is_video = False
        media_type = "unknown"

        if message.photo:
            file = await message.photo[-1].get_file()
            media_type = "photo"
        elif message.sticker:
            if message.sticker.is_animated:
                logger.info("⚠️ Analyzing animated sticker frames")
                file = await message.sticker.get_file()
                media_type = "animated_sticker"
                is_video = True
            else:
                file = await message.sticker.get_file()
                media_type = "sticker"
        elif message.animation:
            file = await message.animation.get_file()
            media_type = "animation"
            is_video = True
        elif message.document:
            if message.document.mime_type.startswith('image/'):
                file = await message.document.get_file()
                media_type = "image_document"
            elif message.document.mime_type.startswith('video/'):
                file = await message.document.get_file()
                media_type = "video_document"
                is_video = True
            else:
                logger.info(
                    f"⚠️ Unsupported document type: {message.document.mime_type}"
                )
                return

        if not file:
            logger.warning("⚠️ No file found in message")
            return

        file_ext = os.path.splitext(
            file.file_path)[1] if file.file_path else '.jpg'
        file_id = str(uuid.uuid4())
        file_path = os.path.join(DOWNLOAD_DIR, f"{file_id}{file_ext}")

        logger.info(
            f"⬇️ Downloading {media_type} (size: {file.file_size or 'unknown'} bytes)"
        )
        await file.download_to_drive(custom_path=file_path)

        analysis_msg = await message.reply_text(
            f"🔍 Analyzing {media_type}..." if not is_video else
            f"🎬 Analyzing {config['FRAME_ANALYSIS_COUNT']} frames from {media_type}..."
        )

        try:
            if is_video or file_ext in ['.gif', '.webm', '.mp4']:
                confidence = analyze_frames(file_path, chat_id)
                is_nsfw_content = confidence > config['NSFW_THRESHOLD']
            else:
                is_nsfw_content, confidence = detect_nsfw_nudenet(
                    file_path, chat_id)

            if is_nsfw_content and confidence > config['NSFW_THRESHOLD']:
                await message.delete()
                logger.info(
                    f"🚫 Deleted NSFW content (Confidence: {confidence:.2%})")

                warning_msg = (f"⚠️ Removed explicit content\n"
                               f"Confidence: {confidence:.2%}\n"
                               f"Media type: {media_type}\n\n"
                               f"*This action was performed automatically*")

                await message.chat.send_message(
                    warning_msg,
                    reply_to_message_id=message.message_id
                    if message.chat.type != 'private' else None)
            else:
                logger.info(f"✅ Safe content (Confidence: {confidence:.2%})")
                await analysis_msg.edit_text(f"✅ Content approved\n"
                                             f"Confidence: {confidence:.2%}")

        except Exception as e:
            logger.error(f"❌ Analysis failed: {str(e)}")
            await analysis_msg.edit_text("❌ Analysis failed. Please try again."
                                         )

        finally:
            if os.path.exists(file_path):
                os.remove(file_path)

    except Exception as e:
        logger.error(f"🔥 Critical error in media handler: {str(e)}")
        if 'analysis_msg' in locals():
            await analysis_msg.edit_text(
                "❌ An error occurred during processing")

async def start_bot():
    """Start the Telegram bot and Flask server"""
    # Start Flask server in a thread
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    # Get bot token from environment variable
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set")
    
    # Create and configure bot application
    app = ApplicationBuilder().token(bot_token).build()

    # Command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("settings", group_settings))

    # Button handler
    app.add_handler(CallbackQueryHandler(handle_button))

    # Message handlers
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Media handler
    media_filter = (filters.PHOTO | filters.Document.IMAGE
                    | filters.Document.VIDEO | filters.Sticker.ALL
                    | filters.ANIMATION)
    app.add_handler(MessageHandler(media_filter, handle_media))

    logger.info("🤖 Starting Lite NSFW Detection Bot...")
    logger.info("📸 Monitoring: Photos | Videos | GIFs | Stickers")

    # Start polling
    await app.run_polling()

if __name__ == "__main__":
    # Create downloads directory if it doesn't exist
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    
    # Start the bot
    import asyncio
    try:
        asyncio.run(start_bot())
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
    except Exception as e:
        logger.critical(f"💥 Critical error: {str(e)}")
