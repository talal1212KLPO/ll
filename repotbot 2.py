import subprocess
import sys

# قائمة بالمكتبات المطلوبة
required_packages = [
    "pyTelegramBotAPI",
    "requests",
    "rich"
]

# دالة لتثبيت أي مكتبة غير موجودة
def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

# فحص وتثبيت المكتبات
for package in required_packages:
    try:
        __import__(package.replace("-", "_"))
    except ImportError:
        print(f"[+] Installing {package} ...")
        install(package)


# الآن يمكنك استدعاء المكتبات بدون مشاكل
import telebot
from telebot import types
import os
import time
import threading
import requests
from requests import post, get
from rich.console import Console
import concurrent.futures
import json
import random
import sys
import re

BOT_TOKEN = "8629935420:AAGjh2azGgXuYoFKe39qyq7Ciuc7ozXlj_k"
bot = telebot.TeleBot(BOT_TOKEN)
console = Console()

user_states = {}
user_data = {}
session_cache = {}
active_reports = {}

class UserState:
    IDLE = 'idle'
    AWAITING_TARGET_ID = 'awaiting_target_id'
    AWAITING_REPORT_TYPE = 'awaiting_report_type'
    AWAITING_REPORTS_PER_SESSION = 'awaiting_reports_per_session'
    AWAITING_SLEEP_TIME = 'awaiting_sleep_time'
    REPORTING = 'reporting'
    AWAITING_SESSIONS_INPUT = 'awaiting_sessions_input'   
    AWAITING_TARGET_IDS_ALL = 'awaiting_target_ids_all'
    AWAITING_REPORT_TYPE_FOR_MULTI_TARGET = 'awaiting_report_type_for_multi_target'
    AWAITING_NEW_REPORT_TYPE_DURING_PROCESS = 'awaiting_new_report_type_during_process'
    AWAITING_REPORT_COUNT_FOR_SELECT = 'awaiting_report_count_for_select'
    AWAITING_MULTIPLE_REPORT_TYPES_SELECTION = 'awaiting_multiple_report_types_selection'
    AWAITING_MULTI_TARGET_REPORT_TYPE_CHANGE = 'awaiting_multi_target_report_type_change'
    AWAITING_MULTI_REPORT_TYPES_CHANGE = 'awaiting_multi_report_types_change'

report_options = {
    1: ("Spam", "Report spam content or behavior"),
    2: ("Self", "Report self-harm content"),
    3: ("Drugs", "Report drug-related content"),
    4: ("Nudity", "Report nudity content"),
    5: ("Violence", "Report violent content"),
    6: ("Hate", "Report hate speech"),
    7: ("Harassment", "Report harassment"),
    8: ("Impersonation", "Report impersonation"),
    11: ("Underage", "User is under 13"),
    12: ("GunSelling", "Selling firearms or weapons"),
}

reason_ids = {
    "Spam": "ig_spam_v3",
    "Self": "suicide_or_self_harm_concern-suicide_or_self_injury",
    "Drugs": "selling_or_promoting_restricted_items-drugs",
    "Nudity": "adult_content-nudity_or_sexual_activity",
    "Violence": "violent_hateful_or_disturbing-violence",
    "Hate": "violent_hateful_or_disturbing-promotes_hate-hate_speech_or_symbols",
    "Harassment": "harrassment_or_abuse-harassment-me-u18-yes",
    "Impersonation": "ig_user_impersonation",
    "Underage": "ig_its_inappropriate",
    "GunSelling": "selling_or_promoting_restricted_items",
}

def send_animated_gif(user_id, text):
    try:
        with open("reporting.gif", "rb") as gif_file:
            msg = bot.send_animation(
                user_id,
                gif_file,
                caption=f" {text}",
                parse_mode="HTML"
            )
            return msg.message_id
    except Exception as e:
        console.print(f"[red]Error sending GIF: {e}[/red]")
        return None

def delete_previous_message(user_id, message_id):
    try:
        bot.delete_message(user_id, message_id)
    except Exception as e:
        console.print(f"[red]Error deleting message: {e}[/red]")

def log_user_to_file(user_id, username):
    try:
        with open("users.txt", "a", encoding="utf-8") as f:
            f.write(f"{user_id} - {username}\n")
    except Exception as e:
        console.print(f"[red]Error logging user to file: {str(e)}[/red]")

def show_main_menu(user_id, message_id=None):
    """عرض القائمة الرئيسية بالأزرار"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    markup.add(
        types.InlineKeyboardButton("📤 إرسال السيشنات", callback_data="send_sessions"),
        types.InlineKeyboardButton("📝 إنشاء السيشنات", callback_data="create_sessions")
    )
    
    markup.add(
        types.InlineKeyboardButton("🎯 بلاغ هدف واحد", callback_data="single_report"),
        types.InlineKeyboardButton("🎯🎯 بلاغ أهداف متعددة", callback_data="multi_report")
    )
    
    markup.add(
        types.InlineKeyboardButton("🔢 أنواع متعددة للبلاغ", callback_data="select_reports"),
        types.InlineKeyboardButton("⏸️ إيقاف مؤقت", callback_data="pause_process")
    )
    
    markup.add(
        types.InlineKeyboardButton("▶️ استئناف", callback_data="resume_process"),
        types.InlineKeyboardButton("🛑 إيقاف", callback_data="stop_process")
    )
    
    markup.add(
        types.InlineKeyboardButton("📊 الحالة", callback_data="check_status"),
        types.InlineKeyboardButton("❓ المساعدة", callback_data="show_help")
    )
    
    text = "🤖 *بوت بلاغات انستغرام*\n\nاختر من القائمة:"
    
    if message_id:
        try:
            bot.edit_message_text(
                text,
                user_id,
                message_id,
                reply_markup=markup,
                parse_mode="Markdown"
            )
        except:
            bot.send_message(user_id, text, reply_markup=markup, parse_mode="Markdown")
    else:
        bot.send_message(user_id, text, reply_markup=markup, parse_mode="Markdown")

def get_csrf_token(sessionid):
    try:
        if sessionid in session_cache:
            return session_cache[sessionid]
        
        r1 = requests.get(
            "https://www.instagram.com/",
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/110.0",
            },
            cookies={"sessionid": sessionid},
            timeout=10
        )
        if "csrftoken" in r1.cookies:
            csrf_token = r1.cookies["csrftoken"]
            # استخراج user_id من السيشن
            user_id_match = re.search(r'ds_user_id=(\d+)', r1.text)
            user_id = user_id_match.group(1) if user_id_match else None
            
            # استخراج claim
            claim_match = re.search(r'"x_ig_www_claim":"([^"]+)"', r1.text)
            claim = claim_match.group(1) if claim_match else "0"
            
            session_data = {
                'csrf': csrf_token,
                'user_id': user_id,
                'claim': claim
            }
            session_cache[sessionid] = session_data
            return session_data
        else:
            return None
    except Exception as e:
        console.print(f"[red]Error getting CSRF: {e}[/red]")
        return None

def validate_session(sessionid):
    try:
        session_data = get_csrf_token(sessionid)
        if session_data:
            test_req = requests.get(
                "https://www.instagram.com/accounts/edit/",
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/110.0",
                },
                cookies={"sessionid": sessionid},
                timeout=10,
                allow_redirects=False
            )
            return test_req.status_code == 200, session_data
        return False, None
    except Exception as e:
        return False, None

def filter_sessions(sessions, user_id, callback_message_id):
    valid_sessions = []
    invalid_sessions = []
    total = len(sessions)
    
    progress_message = bot.send_message(user_id, f"🔍 جارٍ التحقق من السيشنات... ({0}/{total})")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_session = {executor.submit(validate_session, session): session for session in sessions}
        
        completed = 0
        for future in concurrent.futures.as_completed(future_to_session):
            session = future_to_session[future]
            try:
                is_valid, session_data = future.result()
                if is_valid:
                    valid_sessions.append((session, session_data))
                else:
                    invalid_sessions.append(session)
            except Exception as e:
                invalid_sessions.append(session)
            
            completed += 1
            try:
                bot.edit_message_text(
                    f"🔍 جارٍ التحقق من السيشنات... ({completed}/{total})",
                    user_id,
                    progress_message.message_id
                )
            except:
                pass
    
    result_message = f"✅ تم العثور على {len(valid_sessions)} سيشن صالح\n❌ تم استبعاد {len(invalid_sessions)} سيبشن غير صالح"
    
    try:
        bot.edit_message_text(result_message, user_id, progress_message.message_id)
    except:
        bot.send_message(user_id, result_message)
    
    return valid_sessions

def report_instagram(target_id, sessionid, session_data, reportType):
    try:
        
        csrf_token = session_data['csrf']
        user_id = session_data.get('user_id', '')
        claim = session_data.get('claim', '0')
        
        # أولاً: جلب بيانات الـ context
        url = "https://www.instagram.com/api/v1/web/reports/get_frx_prompt/"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'X-CSRFToken': csrf_token,
            'Referer': f'https://www.instagram.com/',
            'X-Instagram-AJAX': '1009616497',
            'X-IG-App-ID': '936619743392459',
            'X-ASBD-ID': '129477',
            'X-IG-WWW-Claim': claim,
            'X-Requested-With': 'XMLHttpRequest',
            'Origin': 'https://www.instagram.com',
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        
        cookies = {
            'sessionid': sessionid,
            'csrftoken': csrf_token,
            'ds_user_id': user_id
        }
        
        # تنظيف الـ cookies من القيم الفارغة
        cookies = {k: v for k, v in cookies.items() if v}
        
        # الحصول على context
        data = {
            'container_module': 'profilePage',
            'entry_point': '1',
            'location': '2',
            'object_id': target_id,
            'object_type': '5',
            'frx_prompt_request_type': '1',
        }
        
        response1 = requests.post(
            url=url,
            headers=headers,
            cookies=cookies,
            data=data,
            timeout=15
        )
        
        
        if response1.status_code != 200:
            return False
            
        try:
            context_data = response1.json()
            if 'response' not in context_data or 'context' not in context_data['response']:
                return False
                
            context = context_data['response']['context']
        except Exception as e:
            return False
        
        # ثانياً: إرسال التقرير الفعلي
        report_data = {
            'container_module': 'profilePage',
            'entry_point': '1',
            'location': '2',
            'object_id': target_id,
            'object_type': '5',
            'context': context,
            'selected_tag_types': f'["{reportType}"]',
            'frx_prompt_request_type': '2',
            'jazoest': '22445'
        }
        
        response2 = requests.post(
            url=url,
            headers=headers,
            cookies=cookies,
            data=report_data,
            timeout=15
        )
        
        
        if response2.status_code == 200:
            try:
                result = response2.json()
                if 'false' in result and result['false']:
                    return False
                else:
                    return True
            except:
                return True
        elif response2.status_code in [200,302,303]:  # تحويلات
            return True
        else:
            return False
            
    except Exception as e:
        return False

def get_random_report_type():
    report_type_id = random.choice(list(report_options.keys()))
    report_type, _ = report_options[report_type_id]
    reason_id = reason_ids[report_type]
    return report_type, reason_id

def create_sessions_list(user_id, sessions_text):
    sessions = [s.strip() for s in sessions_text.strip().split('\n') if s.strip()]
    
    if not sessions:
        bot.send_message(user_id, "❌ لم يتم تقديم سيشنات صالحة!")
        return False
    
    return sessions

def get_user_identifier(user):
    return f"{user.id} - {user.username or 'Unknown'}"

@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.from_user.id
    username = message.from_user.username or "Unknown"
    log_user_to_file(user_id, username)
    
    show_main_menu(user_id)

@bot.message_handler(commands=['menu'])
def handle_menu(message):
    user_id = message.from_user.id
    show_main_menu(user_id)

@bot.callback_query_handler(func=lambda call: call.data == "send_sessions")
def handle_send_sessions_callback(call):
    user_id = call.from_user.id
    bot.answer_callback_query(call.id, "📤 أرسل ملف sessions.txt الآن")
    bot.send_message(user_id, "📤 الرجاء إرسال ملف sessions.txt")

@bot.callback_query_handler(func=lambda call: call.data == "create_sessions")
def handle_create_sessions_callback(call):
    user_id = call.from_user.id
    bot.answer_callback_query(call.id)
    bot.send_message(
        user_id,
        "📝 *إنشاء قائمة السيشنات*\n\n"
        "أدخل سيشن واحد في كل سطر:",
        parse_mode="Markdown"
    )
    user_states[user_id] = UserState.AWAITING_SESSIONS_INPUT

@bot.callback_query_handler(func=lambda call: call.data == "single_report")
def handle_single_report_callback(call):
    user_id = call.from_user.id
    
    if user_id in user_data and 'valid_sessions' in user_data[user_id] and user_data[user_id]['valid_sessions']:
        if user_id in active_reports:
            active_reports.pop(user_id, None)
        user_data[user_id]['good_count'] = 0
        user_data[user_id]['bad_count'] = 0

        bot.answer_callback_query(call.id, "🎯 بلاغ هدف واحد")
        bot.send_message(user_id, "🎯 أدخل يوزر ايدي الهدف:")
        user_states[user_id] = UserState.AWAITING_TARGET_ID
        user_data[user_id]['multi_report_types_mode'] = False
        user_data[user_id]['multi_target_mode'] = False
    else:
        bot.answer_callback_query(call.id, "❌ يجب إرسال السيشنات أولاً!")
        show_main_menu(user_id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "multi_report")
def handle_multi_report_callback(call):
    user_id = call.from_user.id
    
    if user_id in user_data and 'valid_sessions' in user_data[user_id] and user_data[user_id]['valid_sessions']:
        if user_id in active_reports:
            active_reports.pop(user_id, None)
        user_data[user_id]['good_count'] = 0
        user_data[user_id]['bad_count'] = 0

        bot.answer_callback_query(call.id, "🎯🎯 تقرير أهداف متعددة")
        bot.send_message(user_id, "🎯🎯 أرسل قائمة معرفات الأهداف، معرف واحد في كل سطر:")
        user_states[user_id] = UserState.AWAITING_TARGET_IDS_ALL
        user_data[user_id]['multi_target_mode'] = True
        user_data[user_id]['multi_report_types_mode'] = False
    else:
        bot.answer_callback_query(call.id, "❌ يجب إرسال السيشنات أولاً!")
        show_main_menu(user_id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "select_reports")
def handle_select_reports_callback(call):
    user_id = call.from_user.id

    if user_id in user_data and 'valid_sessions' in user_data[user_id] and user_data[user_id]['valid_sessions']:
        if user_id in active_reports:
            active_reports.pop(user_id, None)
        user_data[user_id]['good_count'] = 0
        user_data[user_id]['bad_count'] = 0

        bot.answer_callback_query(call.id, "🔢 أنواع متعددة للتقرير")
        bot.send_message(user_id, "🎯 أدخل يوزر ايدي الهدف :")
        user_states[user_id] = UserState.AWAITING_TARGET_ID
        user_data[user_id]['multi_report_types_mode'] = True
        user_data[user_id]['multi_target_mode'] = False
    else:
        bot.answer_callback_query(call.id, "❌ يجب إرسال السيشنات أولاً!")
        show_main_menu(user_id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "pause_process")
def handle_pause_callback(call):
    user_id = call.from_user.id
    
    if user_id in active_reports and (active_reports[user_id]["running"] or active_reports[user_id].get("paused")):
        active_reports[user_id]["running"] = False
        active_reports[user_id]["paused"] = True
        active_reports[user_id]['pause_event'].set()
        
        if "gif_message_id" in active_reports[user_id]:
            delete_previous_message(user_id, active_reports[user_id]["gif_message_id"])
        
        bot.answer_callback_query(call.id, "⏸️ تم الإيقاف المؤقت")
        bot.send_message(user_id, "⏸️ تم إيقاف العملية مؤقتاً")
    else:
        bot.answer_callback_query(call.id, "❌ لا توجد عملية نشطة للإيقاف")

@bot.callback_query_handler(func=lambda call: call.data == "resume_process")
def handle_resume_callback(call):
    user_id = call.from_user.id
    if user_id in active_reports and active_reports[user_id].get('paused'):
        if user_id not in user_data or 'valid_sessions' not in user_data[user_id] or not user_data[user_id]['valid_sessions']:
            bot.send_message(user_id, "❌ لا يمكن الاستئناف. لم يتم العثور على بيانات السيشن أو لا توجد سيشنات صالحة. يرجى بدء عملية جديدة.")
            if user_id in active_reports:
                active_reports.pop(user_id, None)
            user_states[user_id] = UserState.IDLE
            return

        active_reports[user_id]['running'] = True
        active_reports[user_id]['paused'] = False
        active_reports[user_id]['pause_event'].set()
        
        threading.Thread(target=reporting_thread, 
                       args=(user_id, 
                            user_data[user_id]['target_ids'], 
                            user_data[user_id]['sleep_time'],
                            user_data[user_id].get('reports_per_session', float('inf')),
                            user_data[user_id]['valid_sessions'],
                            active_reports[user_id]['status_message_id'],
                            active_reports[user_id].get('is_multi_target', False),
                            active_reports[user_id].get('is_multi_report_types', False),
                            active_reports[user_id].get('selected_report_types', []))).start()
        
        bot.answer_callback_query(call.id, "▶️ تم الاستئناف")
        bot.send_message(user_id, "▶️ تم استئناف الإبلاغ")
    else:
        bot.answer_callback_query(call.id, "❌ لا توجد عملية متوقفة للاستئناف")

@bot.callback_query_handler(func=lambda call: call.data == "stop_process")
def handle_stop_callback(call):
    user_id = call.from_user.id
    
    if user_id in active_reports and (active_reports[user_id]["running"] or active_reports[user_id].get("paused")):
        active_reports[user_id]["running"] = False
        active_reports[user_id]["paused"] = False
        active_reports[user_id]['pause_event'].set()
        
        if "gif_message_id" in active_reports[user_id]:
            delete_previous_message(user_id, active_reports[user_id]["gif_message_id"])
        
        bot.answer_callback_query(call.id, "🛑 تم الإيقاف")
        bot.send_message(user_id, "🛑 جارٍ إيقاف العملية...")
    else:
        bot.answer_callback_query(call.id, "❌ لا توجد عملية نشطة للإيقاف")

@bot.callback_query_handler(func=lambda call: call.data == "check_status")
def handle_status_callback(call):
    user_id = call.from_user.id
    
    if user_id in active_reports and active_reports[user_id]['running']:
        stats = (
            f"📊 *الحالة الحالية*\n\n"
            f"✅ الناجحة: *{active_reports[user_id]['good_count']}*\n"
            f"❌ الفاشلة: *{active_reports[user_id]['bad_count']}*\n"
            f"🔄 قيد التشغيل: *نعم*\n\n"
            f"_استخدم زر الإيقاف لإلغاء العملية_"
        )
        bot.answer_callback_query(call.id)
        bot.send_message(user_id, stats, parse_mode="Markdown")
    elif user_id in active_reports and active_reports[user_id].get('paused'):
        stats = (
            f"📊 *الحالة الحالية*\n\n"
            f"✅ الناجحة: *{active_reports[user_id]['good_count']}*\n"
            f"❌ الفاشلة: *{active_reports[user_id]['bad_count']}*\n"
            f"⏸️ قيد التشغيل: *لا (متوقفة)*\n\n"
            f"_استخدم زر الاستئناف للمتابعة أو زر الإيقاف للإنهاء_"
        )
        bot.answer_callback_query(call.id)
        bot.send_message(user_id, stats, parse_mode="Markdown")
    else:
        bot.answer_callback_query(call.id, "ℹ️ لا توجد عملية نشطة")
        bot.send_message(user_id, "ℹ️ لا توجد عملية نشطة حالياً")

@bot.callback_query_handler(func=lambda call: call.data == "show_help")
def handle_help_callback(call):
    help_text = (
        "❓ *دليل المساعدة*\n\n"
        "1. أرسل ملف sessions.txt\n"
        "2. استخدم زر 'ابلاغ هدف واحد'\n"
        "3. استخدم زر 'ابلاغ أهداف متعددة'\n"
        "4. استخدم زر 'أنواع متعددة للبلاغات'\n"
        "5. أدخل يوزر ايدي الهدف (الأهداف)\n"
        "6. اختر نوع البلاغ\n"
        "7. حدد معايير الإبلاغ\n\n"
        "*أنواع البلاغات:*\n"
        "1 - البريد المزعج\n2 - إيذاء النفس\n3 - المخدرات\n"
        "4 - العري\n5 - العنف\n6 - الكراهية\n"
        "7 - المضايقة\n8 - انتحال الشخصية\n"
        "11 - قاصر\n12 - بيع الأسلحة\n\n"
        "استخدم زر الإيقاف للإلغاء في أي وقت"
    )
    bot.answer_callback_query(call.id)
    bot.send_message(call.from_user.id, help_text, parse_mode="Markdown")

@bot.message_handler(content_types=['document'])
def handle_document(message):
    user_id = message.from_user.id
    
    if message.document.file_name.lower() != 'sessions.txt':
        bot.send_message(user_id, "❌ يرجى إرسال ملف sessions.txt فقط")
        return
    
    file_info = bot.get_file(message.document.file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    sessions = downloaded_file.decode('utf-8').splitlines()
    
    if not sessions:
        bot.send_message(user_id, "❌ ملف السيشنات فارغ!")
        return
    
    if user_id not in user_data:
        user_data[user_id] = {}
    
    valid_sessions = filter_sessions(sessions, user_id, 0)
    
    if not valid_sessions:
        bot.send_message(user_id, "❌ لم يتم العثور على سيشنات صالحة!")
        return
    
    user_data[user_id]['valid_sessions'] = valid_sessions
    bot.send_message(user_id, f"✅ تم تحميل {len(valid_sessions)} سيشن صالح\nاستخدم الأزرار للبدء")

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == UserState.AWAITING_SESSIONS_INPUT)
def handle_sessions_input(message):
    user_id = message.from_user.id
    sessions = create_sessions_list(user_id, message.text)
    
    if sessions is False:
        return

    valid_sessions = filter_sessions(sessions, user_id, 0)
    
    if user_id not in user_data:
        user_data[user_id] = {}
    
    user_data[user_id]['valid_sessions'] = valid_sessions
    user_states[user_id] = UserState.IDLE
    
    if valid_sessions:
        bot.send_message(user_id, f"✅ تم تحميل {len(valid_sessions)} سيشن صالح\nاستخدم الأزرار للبدء")
    else:
        bot.send_message(user_id, "❌ لم يتم العثور على سيشنات صالحة")

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == UserState.AWAITING_TARGET_ID)
def handle_target_id_input(message):
    user_id = message.from_user.id
    target_id = message.text.strip()
    
    if not target_id.isdigit():
        bot.send_message(user_id, "❌ يوزر ايدي الهدف  غير صالح! يرجى إدخال معرف رقمي.")
        return
    
    if user_id not in user_data:
        user_data[user_id] = {}
    
    user_data[user_id]['target_ids'] = [{'id': target_id, 'report_type': None, 'reason_id': None}]
    user_data[user_id]['current_target_idx'] = 0

    if user_data[user_id].get('multi_report_types_mode', False):
        bot.send_message(user_id, "كم عدد أنواع البلاغات التي تريد تحديدها؟")
        user_states[user_id] = UserState.AWAITING_REPORT_COUNT_FOR_SELECT
    else:
        markup = types.InlineKeyboardMarkup()
        for key, (value, desc) in report_options.items():
            markup.add(types.InlineKeyboardButton(f"{key}. {value} - {desc}", callback_data=f"report_type_{key}"))
        
        markup.add(types.InlineKeyboardButton("🎲 عشوائي - أنواع بلاغات متنوعة", callback_data="report_type_random"))
        
        sent_message = bot.send_message(user_id, "اختر نوع البلاغ:", reply_markup=markup)
        user_data[user_id]['last_options_message_id'] = sent_message.message_id
        user_states[user_id] = UserState.AWAITING_REPORT_TYPE

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == UserState.AWAITING_REPORT_COUNT_FOR_SELECT)
def handle_report_count_for_select(message):
    user_id = message.from_user.id
    try:
        count = int(message.text.strip())
        if count <= 0 or count > len(report_options):
            bot.send_message(user_id, f"❌ يرجى إدخال رقم موجب حتى {len(report_options)}.")
            return
        user_data[user_id]['selected_report_types_count'] = count
        user_data[user_id]['selected_report_types'] = []
        user_data[user_id]['current_selection_idx'] = 0
        ask_for_next_report_type_selection(user_id)
    except ValueError:
        bot.send_message(user_id, "❌ إدخال غير صالح. يرجى إدخال رقم.")

def ask_for_next_report_type_selection(user_id):
    count_to_select = user_data[user_id]['selected_report_types_count']
    current_selection_idx = user_data[user_id]['current_selection_idx']

    if current_selection_idx < count_to_select:
        markup = types.InlineKeyboardMarkup()
        for key, (value, desc) in report_options.items():
            if {'report_type': value, 'reason_id': reason_ids[value]} not in user_data[user_id]['selected_report_types']:
                markup.add(types.InlineKeyboardButton(f"{key}. {value} - {desc}", callback_data=f"select_multi_report_type_{key}"))
        
        sent_message = bot.send_message(user_id, f"حدد نوع البلاغ {current_selection_idx + 1} من {count_to_select}:", reply_markup=markup)
        user_data[user_id]['last_options_message_id'] = sent_message.message_id
        user_states[user_id] = UserState.AWAITING_MULTIPLE_REPORT_TYPES_SELECTION
    else:
        bot.send_message(user_id, "أدخل التأخير بين البلاغات (بالثواني):")
        user_states[user_id] = UserState.AWAITING_SLEEP_TIME

@bot.callback_query_handler(func=lambda call: call.data.startswith('select_multi_report_type_'))
def handle_select_multi_report_type(call):
    user_id = call.from_user.id

    if user_states.get(user_id) not in [UserState.AWAITING_MULTIPLE_REPORT_TYPES_SELECTION, UserState.AWAITING_MULTI_REPORT_TYPES_CHANGE]:
        return
    
    if 'last_options_message_id' in user_data[user_id]:
        delete_previous_message(user_id, user_data[user_id]['last_options_message_id'])
        del user_data[user_id]['last_options_message_id']

    report_id = int(call.data.replace('select_multi_report_type_', ''))
    report_type, _ = report_options[report_id]
    reason_id = reason_ids[report_type]

    if user_states.get(user_id) == UserState.AWAITING_MULTI_REPORT_TYPES_CHANGE:
        if 'temp_new_selected_report_types' not in user_data[user_id]:
            user_data[user_id]['temp_new_selected_report_types'] = []
            
        user_data[user_id]['temp_new_selected_report_types'].append({'report_type': report_type, 'reason_id': reason_id})
        user_data[user_id]['current_selection_idx'] += 1
        bot.answer_callback_query(call.id, f"✅ تم التحديد: {report_type}")
        ask_for_next_report_type_selection_for_change(user_id)
    else:
        user_data[user_id]['selected_report_types'].append({'report_type': report_type, 'reason_id': reason_id})
        user_data[user_id]['current_selection_idx'] += 1
        bot.answer_callback_query(call.id, f"✅ تم التحديد: {report_type}")
        ask_for_next_report_type_selection(user_id)

def ask_for_next_report_type_selection_for_change(user_id):
    count_to_select = user_data[user_id]['selected_report_types_count']
    current_selection_idx = user_data[user_id]['current_selection_idx']

    if current_selection_idx < count_to_select:
        markup = types.InlineKeyboardMarkup()
        for key, (value, desc) in report_options.items():
            if {'report_type': value, 'reason_id': reason_ids[value]} not in user_data[user_id]['temp_new_selected_report_types']:
                markup.add(types.InlineKeyboardButton(f"{key}. {value} - {desc}", callback_data=f"select_multi_report_type_{key}"))
        
        sent_message = bot.send_message(user_id, f"حدد نوع البلاغ الجديد {current_selection_idx + 1} من {count_to_select}:", reply_markup=markup)
        user_data[user_id]['last_options_message_id'] = sent_message.message_id
        user_states[user_id] = UserState.AWAITING_MULTI_REPORT_TYPES_CHANGE
    else:
        bot.send_message(user_id, "✅ تم تحديد جميع أنواع البلاغات. جارٍ استئناف الإبلاغ...")
        
        user_data[user_id]['selected_report_types'] = user_data[user_id]['temp_new_selected_report_types']
        del user_data[user_id]['temp_new_selected_report_types']
        
        if active_reports[user_id].get('paused'):
            active_reports[user_id]['running'] = True
            active_reports[user_id]['paused'] = False
            active_reports[user_id]['pause_event'].set()
            
            threading.Thread(target=reporting_thread, 
                           args=(user_id, 
                                user_data[user_id]['target_ids'], 
                                user_data[user_id]['sleep_time'],
                                user_data[user_id].get('reports_per_session', float('inf')),
                                user_data[user_id]['valid_sessions'],
                                active_reports[user_id]['status_message_id'],
                                active_reports[user_id].get('is_multi_target', False),
                                active_reports[user_id].get('is_multi_report_types', False),
                                user_data[user_id]['selected_report_types'])).start()
        
        user_states[user_id] = UserState.REPORTING

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == UserState.AWAITING_TARGET_IDS_ALL)
def handle_target_ids_all_input(message):
    user_id = message.from_user.id
    target_ids_raw = message.text.strip().split('\n')
    
    target_ids_list = []
    for tid in target_ids_raw:
        tid = tid.strip()
        if tid.isdigit():
            target_ids_list.append({'id': tid, 'report_type': None, 'reason_id': None})
        
    if not target_ids_list:
        bot.send_message(user_id, "❌ لم يتم العثور على معرفات أهداف صالحة. يرجى إدخال معرفات رقمية، واحد في كل سطر.")
        return
    
    if user_id not in user_data:
        user_data[user_id] = {}
    
    user_data[user_id]['target_ids'] = target_ids_list
    user_data[user_id]['current_target_idx'] = 0
    user_data[user_id]['multi_target_mode'] = True

    ask_for_next_target_report_type(user_id)

def ask_for_next_target_report_type(user_id):
    current_target_idx = user_data[user_id]['current_target_idx']
    target_ids = user_data[user_id]['target_ids']

    if current_target_idx < len(target_ids):
        target_id = target_ids[current_target_idx]['id']
        markup = types.InlineKeyboardMarkup()
        for key, (value, desc) in report_options.items():
            markup.add(types.InlineKeyboardButton(f"{key}. {value} - {desc}", callback_data=f"report_type_multi_{key}_{target_id}"))
        
        markup.add(types.InlineKeyboardButton("🎲 عشوائي - أنواع بلاغات متنوعة", callback_data="report_type_multi_random"))
        
        sent_message = bot.send_message(user_id, f"اختر نوع البلاغ للمعرف: *{target_id}*", reply_markup=markup, parse_mode="Markdown")
        user_data[user_id]['last_options_message_id'] = sent_message.message_id
        user_states[user_id] = UserState.AWAITING_REPORT_TYPE_FOR_MULTI_TARGET
    else:
        if len(user_data[user_id]['valid_sessions']) > 1:
            bot.send_message(user_id, "أدخل عدد البلاغات لكل جلسة (أو 'inf' لغير محدود):")
            user_states[user_id] = UserState.AWAITING_REPORTS_PER_SESSION
        else:
            bot.send_message(user_id, "أدخل التأخير بين البلاغات (بالثواني):")
            user_states[user_id] = UserState.AWAITING_SLEEP_TIME

@bot.callback_query_handler(func=lambda call: call.data.startswith('report_type_multi_'))
def handle_report_type_multi_callback(call):
    user_id = call.from_user.id
    
    if user_states.get(user_id) != UserState.AWAITING_REPORT_TYPE_FOR_MULTI_TARGET:
        return
    
    if 'last_options_message_id' in user_data[user_id]:
        delete_previous_message(user_id, user_data[user_id]['last_options_message_id'])
        del user_data[user_id]['last_options_message_id']

    parts = call.data.split('_')
    report_type_data = parts[3]

    current_target_idx = user_data[user_id]['current_target_idx']
    target_ids_list = user_data[user_id]['target_ids']

    if report_type_data == 'random':
        report_type, reason_id = get_random_report_type()
        user_data[user_id]['target_ids'][current_target_idx]['use_random_reports'] = True
    else:
        report_id = int(report_type_data)
        report_type, _ = report_options[report_id]
        reason_id = reason_ids[report_type]
        user_data[user_id]['target_ids'][current_target_idx]['use_random_reports'] = False
    
    user_data[user_id]['target_ids'][current_target_idx]['report_type'] = report_type
    user_data[user_id]['target_ids'][current_target_idx]['reason_id'] = reason_id
    
    bot.answer_callback_query(call.id, f"✅ تم التحديد لـ {target_ids_list[current_target_idx]['id']}: {report_type}")
    
    user_data[user_id]['current_target_idx'] += 1
    ask_for_next_target_report_type(user_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('report_type_') and not call.data.startswith('report_type_multi_'))
def handle_report_type_callback(call):
    user_id = call.from_user.id
    
    if user_states.get(user_id) != UserState.AWAITING_REPORT_TYPE:
        return
    
    if 'last_options_message_id' in user_data[user_id]:
        delete_previous_message(user_id, user_data[user_id]['last_options_message_id'])
        del user_data[user_id]['last_options_message_id']

    report_type_data = call.data.replace('report_type_', '')
    
    if report_type_data == 'random':
        user_data[user_id]['target_ids'][0]['use_random_reports'] = True
        report_type, reason_id = get_random_report_type()
    else:
        report_id = int(report_type_data)
        report_type, _ = report_options[report_id]
        reason_id = reason_ids[report_type]
        user_data[user_id]['target_ids'][0]['use_random_reports'] = False
    
    user_data[user_id]['target_ids'][0]['report_type'] = report_type
    user_data[user_id]['target_ids'][0]['reason_id'] = reason_id
    
    bot.send_message(
        user_id,
        f"✅ تم التحديد: {report_type}{' (عشوائي)' if report_type_data == 'random' else ''}"
    )
    
    if len(user_data[user_id]['valid_sessions']) > 1:
        bot.send_message(user_id, "أدخل عدد البلاغات لكل جلسة (أو 'inf' لغير محدود):")
        user_states[user_id] = UserState.AWAITING_REPORTS_PER_SESSION
    else:
        bot.send_message(user_id, "أدخل التأخير بين البلاغات (بالثواني):")
        user_states[user_id] = UserState.AWAITING_SLEEP_TIME

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == UserState.AWAITING_REPORTS_PER_SESSION)
def handle_reports_per_session_input(message):
    user_id = message.from_user.id
    text = message.text.strip().lower()
    
    if text == 'inf':
        reports_per_session = float('inf')
    else:
        try:
            reports_per_session = int(text)
            if reports_per_session <= 0:
                bot.send_message(user_id, "❌ أدخل رقمًا موجبًا أو 'inf':")
                return
        except ValueError:
            bot.send_message(user_id, "❌ إدخال غير صالح. أدخل رقمًا أو 'inf':")
            return
    
    user_data[user_id]['reports_per_session'] = reports_per_session
    bot.send_message(user_id, "أدخل التأخير بين البلاغات (بالثواني):")
    user_states[user_id] = UserState.AWAITING_SLEEP_TIME

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == UserState.AWAITING_SLEEP_TIME)
def handle_sleep_time_input(message):
    user_id = message.from_user.id
    text = message.text.strip()
    
    try:
        sleep_time = float(text)
        if sleep_time < 0:
            bot.send_message(user_id, "❌ أدخل رقمًا موجبًا:")
            return
    except ValueError:
        bot.send_message(user_id, "❌ إدخال غير صالح. أدخل رقمًا:")
        return
    
    user_data[user_id]['sleep_time'] = sleep_time
    
    target_ids_info = user_data[user_id]['target_ids']
    is_multi_target = user_data[user_id].get('multi_target_mode', False)
    is_multi_report_types = user_data[user_id].get('multi_report_types_mode', False)

    target_display = ""
    report_type_display = ""

    if is_multi_target:
        target_summary_lines = []
        for target_info in target_ids_info:
            target_id = target_info['id']
            report_type = target_info['report_type']
            use_random = target_info.get('use_random_reports', False)
            target_summary_lines.append(f"  - *{target_id}*: {report_type}{' (عشوائي)' if use_random else ''}")
        target_display = f"الأهداف:\n{'\n'.join(target_summary_lines)}"
    else:
        target_id = target_ids_info[0]['id']
        target_display = f"يوزر ايدي الهدف: *{target_id}*"
        if is_multi_report_types:
            report_types_list = [rt['report_type'] for rt in user_data[user_id]['selected_report_types']]
            report_type_display = f"أنواع البلاغات: *{', '.join(report_types_list)}*"
        else:
            report_type = target_ids_info[0]['report_type']
            use_random = target_ids_info[0].get('use_random_reports', False)
            report_type_display = f"نوع البلاغ: *{report_type}{' (عشوائي)' if use_random else ''}*"

    sessions_count = len(user_data[user_id]['valid_sessions'])
    
    reports_per_session_text = ""
    if 'reports_per_session' in user_data[user_id]:
        rps = user_data[user_id]['reports_per_session']
        reports_per_session_text = f"\nالبلاغات/السيشن: *{rps if rps != float('inf') else 'غير محدود'}*"
    
    summary = (
        f"📋 *الملخص*\n\n"
        f"{target_display}\n"
        f"{report_type_display}\n"
        f"السيشنات: *{sessions_count}*{reports_per_session_text}\n"
        f"التأخير: *{sleep_time} ثانية*\n\n"
        f"بدء الإبلاغ؟"
    )
    
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✅ بدء", callback_data="confirm_report_start"),
        types.InlineKeyboardButton("❌ إلغاء", callback_data="cancel_report")
    )
    
    bot.send_message(user_id, summary, reply_markup=markup, parse_mode="Markdown")

def start_reporting_process(user_id):
    target_ids_info = user_data[user_id]['target_ids']
    sleep_time = user_data[user_id]['sleep_time']
    valid_sessions = user_data[user_id]['valid_sessions']
    reports_per_session = user_data[user_id].get('reports_per_session', float('inf'))
    is_multi_target = user_data[user_id].get('multi_target_mode', False)
    is_multi_report_types = user_data[user_id].get('multi_report_types_mode', False)
    selected_report_types = user_data[user_id].get('selected_report_types', [])

    is_resume = user_id in active_reports and active_reports[user_id].get('paused')

    if not is_resume:
        gif_message_id = send_animated_gif(user_id, f"py : @ospunys")
        status_message = bot.send_message(
            user_id, 
            "🚀 جارٍ بدء عملية الإبلاغ...", 
            parse_mode="HTML"
        )
        status_message_id = status_message.message_id
        good_count = 0
        bad_count = 0
        current_target_idx = 0
        current_multi_report_type_idx = 0
        current_session_index = 0
        current_session = ''
        invalid_sessions = []
    else:
        gif_message_id = active_reports[user_id]['gif_message_id']
        status_message_id = active_reports[user_id]['status_message_id']
        good_count = active_reports[user_id]['good_count']
        bad_count = active_reports[user_id]['bad_count']
        current_target_idx = active_reports[user_id]['current_target_idx']
        current_multi_report_type_idx = active_reports[user_id]['current_multi_report_type_idx']
        current_session_index = active_reports[user_id]['current_session_index']
        current_session = active_reports[user_id]['current_session']
        invalid_sessions = active_reports[user_id]['invalid_sessions']

    active_reports[user_id] = {
        'running': True,
        'paused': False,
        'status_message_id': status_message_id,
        'gif_message_id': gif_message_id,
        'good_count': good_count,
        'bad_count': bad_count,
        'invalid_sessions': invalid_sessions,
        'current_session_index': current_session_index,
        'current_session': current_session,
        'current_target_idx': current_target_idx,
        'is_multi_target': is_multi_target,
        'is_multi_report_types': is_multi_report_types,
        'selected_report_types': selected_report_types,
        'current_multi_report_type_idx': current_multi_report_type_idx,
        'last_report_type_change': '',
        'pause_event': threading.Event()
    }
    active_reports[user_id]['pause_event'].set()
    
    threading.Thread(target=reporting_thread, args=(user_id, target_ids_info, sleep_time, reports_per_session, valid_sessions, status_message_id, is_multi_target, is_multi_report_types, selected_report_types)).start()

def reporting_thread(user_id, target_ids_info, sleep_time, reports_per_session, valid_sessions, message_id, is_multi_target, is_multi_report_types, selected_report_types):
    report_data = active_reports[user_id]
    good_count = report_data['good_count']
    bad_count = report_data['bad_count']
    invalid_sessions = report_data['invalid_sessions']
    multiple_sessions = len(valid_sessions) > 1
    last_update_time = time.time()
    update_interval = 2
    
    try:
        while report_data['running']:
            report_data['pause_event'].wait()

            if not report_data['running']:
                break

            # إنشاء قائمة من السيشنات مع بياناتها
            current_valid_sessions = [s for s, data in valid_sessions]
            if report_data['current_session_index'] >= len(current_valid_sessions):
                report_data['current_session_index'] = 0

            for i in range(report_data['current_session_index'], len(current_valid_sessions)):
                sessionid = current_valid_sessions[i]
                session_data = valid_sessions[i][1]

                if not report_data['running']:
                    break
                    
                if sessionid in invalid_sessions:
                    continue
                
                report_data['current_session_index'] = i
                report_data['current_session'] = sessionid
                
                # التحقق من السيشن
                is_valid, _ = validate_session(sessionid)
                if not is_valid:
                    bad_count += 1
                    invalid_sessions.append(sessionid)
                    # إزالة السيشن من القائمة
                    for idx, (sess, data) in enumerate(valid_sessions):
                        if sess == sessionid:
                            valid_sessions.pop(idx)
                            break
                    
                    update_status_message(user_id, good_count, bad_count, i+1, len(valid_sessions), f"❌ السيشن {sessionid[:8]}... غير صالحة")
                    continue

                session_success = 0
                report_counter = 0
                
                targets_to_report = target_ids_info
                target_idx_in_cycle = report_data['current_target_idx']
                multi_report_type_idx = report_data['current_multi_report_type_idx']

                while (reports_per_session == float('inf') or report_counter < reports_per_session) and report_data['running']:
                    report_data['pause_event'].wait()

                    if not report_data['running']:
                        break

                    if not targets_to_report:
                        break

                    current_target_info = targets_to_report[target_idx_in_cycle % len(targets_to_report)]
                    target_id = current_target_info['id']
                    
                    current_report_type = ""
                    current_reason_id = ""
                    use_random_reports_for_target = False

                    if user_id in user_data and 'temp_new_multi_target_report_types' in user_data[user_id]:
                        new_target_report_types = user_data[user_id]['temp_new_multi_target_report_types']
                        for new_info in new_target_report_types:
                            for old_info in target_ids_info:
                                if old_info['id'] == new_info['id']:
                                    old_info.update(new_info)
                                    break
                        report_data['last_report_type_change'] = "🔄 تم تحديث أنواع البلاغات لجميع الأهداف"
                        del user_data[user_id]['temp_new_multi_target_report_types']

                    if is_multi_report_types:
                        if user_id in user_data and 'temp_new_selected_report_types' in user_data[user_id]:
                            report_data['selected_report_types'] = user_data[user_id]['temp_new_selected_report_types']
                            selected_report_types = report_data['selected_report_types']
                            report_data['last_report_type_change'] = f"🔄 تم تغيير جميع أنواع البلاغات إلى: {', '.join([rt['report_type'] for rt in selected_report_types])}"
                            del user_data[user_id]['temp_new_selected_report_types']
                            multi_report_type_idx = 0

                        selected_type_info = selected_report_types[multi_report_type_idx % len(selected_report_types)]
                        current_report_type = selected_type_info['report_type']
                        current_reason_id = selected_type_info['reason_id']
                    else:
                        use_random_reports_for_target = current_target_info.get('use_random_reports', False)
                        current_report_type = current_target_info['report_type']
                        current_reason_id = current_target_info['reason_id']

                        if user_id in user_data and 'temp_new_report_type' in user_data[user_id]:
                            new_report_type_info = user_data[user_id]['temp_new_report_type']
                            current_report_type = new_report_type_info['report_type']
                            current_reason_id = new_report_type_info['reason_id']
                            current_target_info.update(new_report_type_info)
                            current_target_info['use_random_reports'] = False
                            report_data['last_report_type_change'] = f"🔄 تم تغيير نوع البلاغ إلى: {current_report_type}"
                            del user_data[user_id]['temp_new_report_type']
                            
                        elif use_random_reports_for_target:
                            previous_report_type = current_report_type
                            current_report_type, current_reason_id = get_random_report_type()
                            report_data['last_report_type_change'] = f"🔄 تم تغيير نوع البلاغ لـ {target_id}: {previous_report_type} -> {current_report_type}"
                        else:
                            report_data['last_report_type_change'] = ''

                    report_data['current_target_idx'] = target_idx_in_cycle % len(targets_to_report)
                    report_data['current_target_id'] = target_id
                    report_data['current_report_type_display'] = current_report_type
                    report_data['current_multi_report_type_idx'] = multi_report_type_idx % len(selected_report_types) if is_multi_report_types else 0

                    console.print(f"[cyan]محاولة بلاغ للهدف {target_id} بنوع {current_reason_id}[/cyan]")
                    
                    if report_instagram(target_id, sessionid, session_data, current_reason_id):
                        good_count += 1
                        session_success += 1
                        console.print(f"[green]✓ نجح البلاغ للهدف {target_id}[/green]")
                    else:
                        bad_count += 1
                        console.print(f"[red]✗ فشل البلاغ للهدف {target_id}[/red]")
                        
                        # التحقق من صلاحية السيشن بعد الفشل
                        is_valid, _ = validate_session(sessionid)
                        if not is_valid:
                            invalid_sessions.append(sessionid)
                            # إزالة السيشن من القائمة
                            for idx, (sess, data) in enumerate(valid_sessions):
                                if sess == sessionid:
                                    valid_sessions.pop(idx)
                                    break
                            update_status_message(user_id, good_count, bad_count, i+1, len(valid_sessions), f"❌ انتهت صلاحية السيشن {sessionid[:8]}...")
                            break

                    if sleep_time > 0:
                        time.sleep(sleep_time)
                        
                    report_counter += 1
                    target_idx_in_cycle += 1
                    if is_multi_report_types:
                        multi_report_type_idx += 1
                    
                    if time.time() - last_update_time > update_interval:
                        update_status_message(user_id, good_count, bad_count, i+1, len(valid_sessions))
                        last_update_time = time.time()
                            
                if not report_data['running']:
                    break

                if reports_per_session != float('inf'):
                    update_status_message(user_id, good_count, bad_count, i+1, len(valid_sessions), f"📤 تم إرسال {session_success} تقريرًا من السيشن {i+1}/{len(valid_sessions)}")
                else:
                    update_status_message(user_id, good_count, bad_count, i+1, len(valid_sessions), f"✅ اكتمل السيشن {i+1}/{len(valid_sessions)} دورة")
                last_update_time = time.time()
            
            report_data['current_session_index'] = 0

            if not valid_sessions:
                update_status_message(user_id, good_count, bad_count, 0, 0, "❌ لم تتبقى سيشنات صالحة!")
                break
            
            if multiple_sessions and report_data['running']:
                update_status_message(
                    user_id, 
                    good_count, 
                    bad_count, 
                    1, 
                    len(valid_sessions), 
                    "🔄 بدء دورة جديدة بالسيشنات..."
                )
                time.sleep(3)
            elif report_data['running']:
                update_status_message(
                    user_id, 
                    good_count, 
                    bad_count, 
                    1, 
                    len(valid_sessions), 
                    "🔄 المتابعة بسيشن واحدة..."
                )
                time.sleep(3)

        report_data['good_count'] = good_count
        report_data['bad_count'] = bad_count
        
    except Exception as e:
        error_message = f"❌ خطأ أثناء الإبلاغ: {str(e)}"
        console.print(f"[red]{error_message}[/red]")
        try:
            bot.edit_message_text(
                error_message,
                user_id,
                message_id
            )
        except:
            bot.send_message(user_id, error_message)
    
    finally:
        if user_id in active_reports and not active_reports[user_id].get('paused'):
            final_target_display = ""
            final_report_type_display = ""

            if is_multi_target:
                final_target_display = "الأهداف:\n"
                for target_info in target_ids_info:
                    final_target_display += f"  - {target_info['id']} ({target_info['report_type']})\n"
            else:
                final_target_display = f"يوزر ايدي الهدف : {target_ids_info[0]['id']}"
                if is_multi_report_types:
                    report_types_list = [rt['report_type'] for rt in selected_report_types]
                    final_report_type_display = f"أنواع البلاغات: {', '.join(report_types_list)}"
                else:
                    final_report_type_display = f"نوع البلاغ: {target_ids_info[0]['report_type']}"

            final_message = (
                f"📋 *البلاغ النهائي*\n\n"
                f"✅ البلاغات الناجحة: *{good_count}*\n"
                f"❌ البلاغات الفاشلة: *{bad_count}*\n"
                f"⏱️ وقت الانتظار: *{sleep_time} ثانية*\n"
                f"{final_target_display}\n"
                f"{final_report_type_display}\n\n"
                f"🎉 *اكتملت العملية!*"
            )
            
            try:
                bot.edit_message_text(
                    final_message,
                    user_id,
                    message_id,
                    parse_mode="Markdown"
                )
            except:
                bot.send_message(user_id, final_message, parse_mode="Markdown")
            
            user_states[user_id] = UserState.IDLE
            active_reports.pop(user_id, None)
            if user_id in user_data and 'valid_sessions' in user_data[user_id]:
                del user_data[user_id]['valid_sessions']

def update_status_message(user_id, good_count, bad_count, current_session_idx, total_sessions, additional_info=None):
    if user_id not in active_reports:
        return
    
    report_data = active_reports[user_id]
    current_session = report_data.get('current_session', '')
    session_display = current_session[:8] + "......" if current_session else "لا شيء"
    
    is_multi_target = report_data.get('is_multi_target', False)
    is_multi_report_types = report_data.get('is_multi_report_types', False)
    current_target_id = report_data.get('current_target_id', 'غير معروف')
    current_report_type_display = report_data.get('current_report_type_display', 'غير معروف')
    report_type_change = report_data.get('last_report_type_change', '')

    target_info_line = ""
    if is_multi_target:
        target_info_line = f"الهدف الحالي: *{current_target_id}*\nنوع البلاغ: *{current_report_type_display}*\n"
    elif is_multi_report_types:
        target_info_line = f"يوزر ايدي الهدف : *{current_target_id}*\nنوع البلاغ: *{current_report_type_display}*\n"
    else:
        target_info_line = f"يوزر ايدي الهدف : *{current_target_id}*\nنوع البلاغ: *{current_report_type_display}*\n"

    status_text = (
        f"📊 *حالة الإبلاغ*\n\n"
        f"✅ الناجحة: *{good_count}*\n"
        f"❌ الفاشلة: *{bad_count}*\n"
        f"السيشن الحالية: *{session_display}*\n"
        f"{target_info_line}"
    )
    
    if total_sessions > 0:
        status_text += f"تقدم السيشن: *{current_session_idx}/{total_sessions}*\n"
    
    if report_type_change:
        status_text += f"_{report_type_change}_\n"
    
    if additional_info:
        status_text += f"\n_{additional_info}_\n"
    
    markup = types.InlineKeyboardMarkup()
    if report_data['running']:
        markup.add(types.InlineKeyboardButton("⏸️ إيقاف مؤقت", callback_data="pause_reporting"))
        markup.add(types.InlineKeyboardButton("🔄 تغيير نوع البلاغ", callback_data="change_report_type_mid_process"))
    elif report_data.get('paused'):
        markup.add(types.InlineKeyboardButton("▶️ استئناف", callback_data="resume_reporting"))
        markup.add(types.InlineKeyboardButton("🔄 تغيير نوع البلاغ", callback_data="change_report_type_mid_process"))

    status_text += "\n_يمكنك الإيقاف بزر الإيقاف_"
    
    try:
        bot.edit_message_text(
            status_text,
            user_id,
            report_data['status_message_id'],
            reply_markup=markup,
            parse_mode="Markdown"
        )
    except Exception as e:
        console.print(f"[red]Error editing status message: {e}[/red]")

@bot.callback_query_handler(func=lambda call: call.data == "confirm_report_start")
def handle_confirm_report_start(call):
    user_id = call.from_user.id
    delete_previous_message(user_id, call.message.message_id) 
    user_states[user_id] = UserState.REPORTING
    start_reporting_process(user_id)

@bot.callback_query_handler(func=lambda call: call.data == "cancel_report")
def handle_cancel_report(call):
    user_id = call.from_user.id
    delete_previous_message(user_id, call.message.message_id) 
    bot.send_message(user_id, "❌ تم الإلغاء")
    user_states[user_id] = UserState.IDLE
    if user_id in active_reports:
        active_reports.pop(user_id, None)
        if user_id in user_data and 'valid_sessions' in user_data[user_id]:
            del user_data[user_id]['valid_sessions']

@bot.callback_query_handler(func=lambda call: call.data == "pause_reporting")
def handle_pause_reporting(call):
    user_id = call.from_user.id
    if user_id in active_reports and active_reports[user_id]['running']:
        active_reports[user_id]['running'] = False
        active_reports[user_id]['paused'] = True
        active_reports[user_id]['pause_event'].clear()
        bot.answer_callback_query(call.id, "⏸️ تم الإيقاف المؤقت")
        update_status_message(user_id, active_reports[user_id]['good_count'], active_reports[user_id]['bad_count'], 
                               active_reports[user_id]['current_session_index'], 
                               len(user_data[user_id]['valid_sessions']), "⏸️ العملية متوقفة")
    else:
        bot.answer_callback_query(call.id, "❌ لا توجد عملية نشطة للإيقاف")

@bot.callback_query_handler(func=lambda call: call.data == "resume_reporting")
def handle_resume_reporting(call):
    user_id = call.from_user.id
    if user_id in active_reports and active_reports[user_id].get('paused'):
        if user_id not in user_data or 'valid_sessions' not in user_data[user_id] or not user_data[user_id]['valid_sessions']:
            bot.send_message(user_id, "❌ لا يمكن الاستئناف. لم يتم العثور على بيانات السيشن أو لا توجد سيشنات صالحة. يرجى بدء عملية جديدة.")
            if user_id in active_reports:
                active_reports.pop(user_id, None)
            user_states[user_id] = UserState.IDLE
            return

        active_reports[user_id]['running'] = True
        active_reports[user_id]['paused'] = False
        active_reports[user_id]['pause_event'].set()
        
        threading.Thread(target=reporting_thread, 
                       args=(user_id, 
                            user_data[user_id]['target_ids'], 
                            user_data[user_id]['sleep_time'],
                            user_data[user_id].get('reports_per_session', float('inf')),
                            user_data[user_id]['valid_sessions'],
                            active_reports[user_id]['status_message_id'],
                            active_reports[user_id].get('is_multi_target', False),
                            active_reports[user_id].get('is_multi_report_types', False),
                            active_reports[user_id].get('selected_report_types', []))).start()
        
        bot.answer_callback_query(call.id, "▶️ تم الاستئناف")
        update_status_message(user_id, 
                            active_reports[user_id]['good_count'], 
                            active_reports[user_id]['bad_count'], 
                            active_reports[user_id]['current_session_index'], 
                            len(user_data[user_id]['valid_sessions']), 
                            "▶️ تم استئناف العملية")
    else:
        bot.answer_callback_query(call.id, "❌ لا توجد عملية متوقفة للاستئناف")

@bot.callback_query_handler(func=lambda call: call.data == "change_report_type_mid_process")
def handle_change_report_type_mid_process(call):
    user_id = call.from_user.id
    if user_id in active_reports and (active_reports[user_id]['running'] or active_reports[user_id].get('paused')):
        if user_id not in user_data:
            user_data[user_id] = {}
        
        if active_reports[user_id].get('is_multi_target', False):
            user_data[user_id]['current_target_idx_for_change'] = 0
            user_data[user_id]['temp_new_multi_target_report_types'] = []
            
            target_ids = user_data[user_id]['target_ids']
            if user_data[user_id]['current_target_idx_for_change'] < len(target_ids):
                target_id = target_ids[user_data[user_id]['current_target_idx_for_change']]['id']
                
                markup = types.InlineKeyboardMarkup()
                for key, (value, desc) in report_options.items():
                    markup.add(types.InlineKeyboardButton(f"{key}. {value} - {desc}", 
                            callback_data=f"set_new_report_type_multi_{key}"))
                
                markup.add(types.InlineKeyboardButton("🎲 عشوائي - أنواع بلاغات متنوعة", 
                        callback_data="set_new_report_type_multi_random"))
                
                sent_message = bot.send_message(user_id, 
                    f"اختر نوع البلاغ الجديد للمعرف: *{target_id}*", 
                    reply_markup=markup, 
                    parse_mode="Markdown")
                user_data[user_id]['last_options_message_id'] = sent_message.message_id
                
                user_states[user_id] = UserState.AWAITING_MULTI_TARGET_REPORT_TYPE_CHANGE
        elif active_reports[user_id].get('is_multi_report_types', False):
            user_data[user_id]['current_selection_idx'] = 0
            user_data[user_id]['temp_new_selected_report_types'] = []
            user_data[user_id]['selected_report_types_count'] = len(active_reports[user_id]['selected_report_types'])
            
            markup = types.InlineKeyboardMarkup()
            for key, (value, desc) in report_options.items():
                markup.add(types.InlineKeyboardButton(f"{key}. {value} - {desc}", 
                        callback_data=f"select_multi_report_type_{key}"))
            
            sent_message = bot.send_message(user_id, 
                f"حدد نوع البلاغ الجديد 1 من {user_data[user_id]['selected_report_types_count']}:", 
                reply_markup=markup)
            user_data[user_id]['last_options_message_id'] = sent_message.message_id
            
            user_states[user_id] = UserState.AWAITING_MULTI_REPORT_TYPES_CHANGE
        else:
            markup = types.InlineKeyboardMarkup()
            for key, (value, desc) in report_options.items():
                markup.add(types.InlineKeyboardButton(f"{key}. {value} - {desc}", 
                        callback_data=f"set_new_report_type_{key}"))
            
            markup.add(types.InlineKeyboardButton("🎲 عشوائي - أنواع بلاغات متنوعة", 
                    callback_data="set_new_report_type_random"))
            
            sent_message = bot.send_message(user_id, "اختر نوع البلاغ الجديد:", reply_markup=markup)
            user_data[user_id]['last_options_message_id'] = sent_message.message_id
            user_states[user_id] = UserState.AWAITING_NEW_REPORT_TYPE_DURING_PROCESS
    else:
        bot.answer_callback_query(call.id, "❌ لا توجد عملية نشطة أو متوقفة لتغيير نوع البلاغ")

@bot.callback_query_handler(func=lambda call: call.data.startswith('set_new_report_type_multi_'))
def handle_set_new_report_type_multi(call):
    user_id = call.from_user.id
    if user_states.get(user_id) != UserState.AWAITING_MULTI_TARGET_REPORT_TYPE_CHANGE:
        return
    
    if 'last_options_message_id' in user_data[user_id]:
        delete_previous_message(user_id, user_data[user_id]['last_options_message_id'])
        del user_data[user_id]['last_options_message_id']

    if 'temp_new_multi_target_report_types' not in user_data[user_id]:
        user_data[user_id]['temp_new_multi_target_report_types'] = []
    
    parts = call.data.split('_')
    report_type_data = parts[-1]
    
    current_idx = user_data[user_id]['current_target_idx_for_change']
    target_ids = user_data[user_id]['target_ids']
    
    if current_idx >= len(target_ids):
        bot.answer_callback_query(call.id, "❌ فهرس الهدف غير صالح")
        return
    
    if report_type_data == 'random':
        report_type, reason_id = get_random_report_type()
        use_random = True
    else:
        report_id = int(report_type_data)
        report_type, _ = report_options[report_id]
        reason_id = reason_ids[report_type]
        use_random = False
    
    target_ids[current_idx]['report_type'] = report_type
    target_ids[current_idx]['reason_id'] = reason_id
    target_ids[current_idx]['use_random_reports'] = use_random
    
    user_data[user_id]['temp_new_multi_target_report_types'].append({
        'id': target_ids[current_idx]['id'],
        'report_type': report_type,
        'reason_id': reason_id,
        'use_random_reports': use_random
    })
    
    user_data[user_id]['current_target_idx_for_change'] += 1
    
    if user_data[user_id]['current_target_idx_for_change'] < len(target_ids):
        next_target_id = target_ids[user_data[user_id]['current_target_idx_for_change']]['id']
        
        markup = types.InlineKeyboardMarkup()
        for key, (value, desc) in report_options.items():
            markup.add(types.InlineKeyboardButton(f"{key}. {value} - {desc}", 
                    callback_data=f"set_new_report_type_multi_{key}"))
        
        markup.add(types.InlineKeyboardButton("🎲 عشوائي - أنواع بلاغات متنوعة", 
                callback_data="set_new_report_type_multi_random"))
        
        sent_message = bot.send_message(user_id, 
            f"اختر نوع البلاغ الجديد للمعرف: *{next_target_id}*", 
            reply_markup=markup, 
            parse_mode="Markdown")
        user_data[user_id]['last_options_message_id'] = sent_message.message_id
    else:
        bot.send_message(user_id, "✅ تم تحديث جميع الأهداف. جارٍ استئناف الإبلاغ...")
        
        active_reports[user_id]['last_report_type_change'] = "🔄 تم تحديث أنواع بلاغات جميع الأهداف"
        
        if active_reports[user_id].get('paused'):
            active_reports[user_id]['running'] = True
            active_reports[user_id]['paused'] = False
            active_reports[user_id]['pause_event'].set()
            
            threading.Thread(target=reporting_thread, 
                           args=(user_id, 
                                user_data[user_id]['target_ids'], 
                                user_data[user_id]['sleep_time'],
                                user_data[user_id].get('reports_per_session', float('inf')),
                                user_data[user_id]['valid_sessions'],
                                active_reports[user_id]['status_message_id'],
                                active_reports[user_id].get('is_multi_target', False),
                                active_reports[user_id].get('is_multi_report_types', False),
                                active_reports[user_id].get('selected_report_types', []))).start()
        
        user_states[user_id] = UserState.REPORTING

@bot.callback_query_handler(func=lambda call: call.data.startswith('set_new_report_type_') and not call.data.startswith('set_new_report_type_multi_'))
def handle_set_new_report_type(call):
    user_id = call.from_user.id
    if user_states.get(user_id) != UserState.AWAITING_NEW_REPORT_TYPE_DURING_PROCESS:
        return
    
    if 'last_options_message_id' in user_data[user_id]:
        delete_previous_message(user_id, user_data[user_id]['last_options_message_id'])
        del user_data[user_id]['last_options_message_id']

    report_type_data = call.data.replace('set_new_report_type_', '')
    
    if report_type_data == 'random':
        report_type, reason_id = get_random_report_type()
        use_random = True
    else:
        report_id = int(report_type_data)
        report_type, _ = report_options[report_id]
        reason_id = reason_ids[report_type]
        use_random = False
    
    if user_data[user_id]['target_ids']:
        user_data[user_id]['target_ids'][0]['report_type'] = report_type
        user_data[user_id]['target_ids'][0]['reason_id'] = reason_id
        user_data[user_id]['target_ids'][0]['use_random_reports'] = use_random
    
    bot.send_message(
        user_id,
        f"🔄 تم تغيير نوع البلاغ إلى: {report_type}\nجارٍ استئناف الإبلاغ..."
    )
    
    active_reports[user_id]['last_report_type_change'] = f"🔄 تم تغيير نوع البلاغ إلى: {report_type}"
    
    if active_reports[user_id].get('paused'):
        active_reports[user_id]['running'] = True
        active_reports[user_id]['paused'] = False
        active_reports[user_id]['pause_event'].set()
        
        threading.Thread(target=reporting_thread, 
                       args=(user_id, 
                            user_data[user_id]['target_ids'], 
                            user_data[user_id]['sleep_time'],
                            user_data[user_id].get('reports_per_session', float('inf')),
                            user_data[user_id]['valid_sessions'],
                            active_reports[user_id]['status_message_id'],
                            active_reports[user_id].get('is_multi_target', False),
                            active_reports[user_id].get('is_multi_report_types', False),
                            active_reports[user_id].get('selected_report_types', []))).start()
    
    user_states[user_id] = UserState.REPORTING

@bot.message_handler(func=lambda message: True)
def handle_messages(message):
    user_id = message.from_user.id
    if user_id not in user_states:
        user_states[user_id] = UserState.IDLE
    
    if user_states[user_id] == UserState.IDLE:
        show_main_menu(user_id)

if __name__ == "__main__":
    console.print("[green]🤖 تم تشغيل البوت![/green]")
    bot.polling(none_stop=True)
