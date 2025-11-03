import os
import random
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# env variables
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER") 
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD") 

otp_store = {}
TEST_EMAIL = "test@example.com"
TEST_OTP = "1000"

def generate_otp(length=4) -> str:
    return ''.join(random.choices('0123456789', k=length))


# send email and otp functions
def send_email(to_email: str, subject: str, message: str) -> bool:
    try:
        msg = MIMEMultipart()
        msg["From"] = SMTP_USER
        msg["To"] = to_email
        msg["Subject"] = subject

        msg.attach(MIMEText(message, "plain"))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)

        print(f"[INFO] OTP email sent to {to_email}")
        return True

    except Exception as e:
        print(f"[ERROR] Failed to send email: {e}")
        return False


def send_otp(email: str) -> bool:
    if email == TEST_EMAIL:
        otp_store[email] = {"otp": TEST_OTP, "timestamp": time.time()}
        print(f"[INFO] Test OTP '{TEST_OTP}' stored for {email}")
        return True

    otp = generate_otp()
    subject = "Your Verification Code"
    message = f"Your OTP for verification is: {otp}\n\nThis code will expire in 5 minutes."

    sent = send_email(email, subject, message)
    if sent:
        otp_store[email] = {"otp": otp, "timestamp": time.time()}
        print(f"[INFO] OTP '{otp}' stored for {email}")
        return True
    else:
        print(f"[ERROR] Could not send OTP to {email}")
        return False


def verify_otp(email: str, user_input_otp: str) -> bool:
    if email == TEST_EMAIL and user_input_otp == TEST_OTP:
        print(f"[INFO] Test OTP verified for {email}")
        return True

    record = otp_store.get(email)
    if not record:
        print(f"[WARN] No OTP found for {email}")
        return False

    if time.time() - record['timestamp'] > 300:
        print(f"[WARN] OTP expired for {email}")
        del otp_store[email]
        return False

    if record['otp'] == user_input_otp:
        print(f"[INFO] OTP verified for {email}")
        del otp_store[email]
        return True
    else:
        print(f"[WARN] Invalid OTP for {email}")
        return False
