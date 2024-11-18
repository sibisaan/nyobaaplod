import hashlib
import requests
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, CallbackContext

# Konstanta
API_URL_LOGIN = "https://mtacc.mobilelegends.com/v2.1/inapp/login"
API_URL_CHANGE_EMAIL = "https://mtacc.mobilelegends.com/v2.1/inapp/changebindemail"
BOT_TOKEN = "YOUR_BOT_TOKEN"  # Ganti dengan token bot Anda

# Menyimpan data sementara
user_data = {}

# Fungsi untuk mengonversi password menjadi MD5
def convert_password_to_md5(password):
    md5_hash = hashlib.md5()
    md5_hash.update(password.encode('utf-8'))
    return md5_hash.hexdigest()

# Fungsi untuk login ke Mobile Legends dan mendapatkan data yang diperlukan
def login(account, password, verification_code):
    md5pwd = convert_password_to_md5(password)
    login_data = {
        "op": "login",
        "sign": "ca62428dca478c20b860f65cf000201f",  # Sign dapat diperoleh dari header atau dihasilkan dari data tertentu
        "params": {
            "account": account,
            "md5pwd": md5pwd,
            "game_token": "",
            "recaptcha_token": verification_code,  # Gunakan kode verifikasi di sini
            "country": ""
        },
        "lang": "id"
    }

    response = requests.post(API_URL_LOGIN, json=login_data)
    if response.status_code == 200:
        login_response = response.json()
        game_token = login_response.get("data").get("game_token")
        guid = login_response.get("data").get("guid")
        token = login_response.get("data").get("token")
        return game_token, guid, token
    return None, None, None

# Fungsi untuk mengganti email
def change_email(game_token, guid, token, new_email, verification_code_new_email):
    change_email_data = {
        "op": "changebindemail",
        "params": {
            "email": new_email,
            "guid": guid,
            "game_token": game_token,
            "token": token,
            "verification_code": verification_code_new_email  # Kode verifikasi dari email baru
        },
        "lang": "id"
    }

    response = requests.post(API_URL_CHANGE_EMAIL, json=change_email_data)
    if response.status_code == 200:
        change_email_response = response.json()
        if change_email_response.get("status") == "success":
            return "Email berhasil diganti."
        else:
            return f"Gagal mengganti email: {change_email_response.get('message')}"
    return "Permintaan gagal."

# Fungsi untuk menangani /start command
def start(update: Update, context: CallbackContext):
    update.message.reply_text("Selamat datang! Kirimkan email yang ingin diganti terlebih dahulu.")
    return "WAITING_FOR_OLD_EMAIL"

# Fungsi untuk menangani email yang akan diganti
def receive_old_email(update: Update, context: CallbackContext):
    old_email = update.message.text
    user_data[update.message.chat_id] = {"old_email": old_email}
    update.message.reply_text("Sekarang, kirimkan password Moonton Anda.")
    return "WAITING_FOR_PASSWORD"

# Fungsi untuk menangani password
def receive_password(update: Update, context: CallbackContext):
    password = update.message.text
    user_data[update.message.chat_id]["password"] = password
    update.message.reply_text("Sekarang, kirimkan kode verifikasi Moonton (dikirim ke email lama).")
    return "WAITING_FOR_MOONTON_VERIFICATION_CODE"

# Fungsi untuk menangani kode verifikasi Moonton
def receive_moonton_verification_code(update: Update, context: CallbackContext):
    verification_code = update.message.text
    user_data[update.message.chat_id]["verification_code"] = verification_code
    update.message.reply_text("Sekarang, kirimkan email baru yang ingin Anda kaitkan.")
    return "WAITING_FOR_NEW_EMAIL"

# Fungsi untuk menangani email baru
def receive_new_email(update: Update, context: CallbackContext):
    new_email = update.message.text
    user_data[update.message.chat_id]["new_email"] = new_email
    update.message.reply_text("Terakhir, kirimkan kode verifikasi dari email baru.")
    return "WAITING_FOR_NEW_EMAIL_VERIFICATION_CODE"

# Fungsi untuk menangani kode verifikasi email baru
def receive_new_email_verification_code(update: Update, context: CallbackContext):
    new_email_verification_code = update.message.text
    user_data[update.message.chat_id]["new_email_verification_code"] = new_email_verification_code

    # Ambil data yang diperlukan untuk login
    old_email = user_data[update.message.chat_id]["old_email"]
    password = user_data[update.message.chat_id]["password"]
    verification_code = user_data[update.message.chat_id]["verification_code"]
    new_email = user_data[update.message.chat_id]["new_email"]
    new_email_verification_code = user_data[update.message.chat_id]["new_email_verification_code"]

    # Login ke Mobile Legends
    game_token, guid, token = login(old_email, password, verification_code)

    if game_token and guid and token:
        # Ganti email
        result = change_email(game_token, guid, token, new_email, new_email_verification_code)
        update.message.reply_text(result)
    else:
        update.message.reply_text("Login gagal. Cek kembali email, password, atau kode verifikasi Anda.")

    # Reset data untuk pengguna
    del user_data[update.message.chat_id]

    return ConversationHandler.END

# Fungsi utama untuk menjalankan bot
def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    # Definisikan langkah-langkah percakapan
    conversation_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            "WAITING_FOR_OLD_EMAIL": [MessageHandler(Filters.text & ~Filters.command, receive_old_email)],
            "WAITING_FOR_PASSWORD": [MessageHandler(Filters.text & ~Filters.command, receive_password)],
            "WAITING_FOR_MOONTON_VERIFICATION_CODE": [MessageHandler(Filters.text & ~Filters.command, receive_moonton_verification_code)],
            "WAITING_FOR_NEW_EMAIL": [MessageHandler(Filters.text & ~Filters.command, receive_new_email)],
            "WAITING_FOR_NEW_EMAIL_VERIFICATION_CODE": [MessageHandler(Filters.text & ~Filters.command, receive_new_email_verification_code)],
        },
        fallbacks=[],
    )

    # Menambahkan handler percakapan ke dispatcher
    dispatcher.add_handler(conversation_handler)

    # Mulai bot
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()