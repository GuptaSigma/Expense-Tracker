import random
import string
import requests
from datetime import datetime, timedelta
from config import Config
from flask_mail import Message
from app import mail


def send_otp_email(email, otp, username):
    """Send OTP verification email via Apps Script or Resend API.

    Returns True when the OTP has been delivered successfully.
    """
    # Development mode - just print OTP
    if Config.OTP_DEV_MODE:
        print(f"🔐 DEV MODE - OTP for {email}: {otp}")
        return True

    normalized_email = (email or '').strip().lower()
    normalized_username = (username or '').strip()
    normalized_otp = str(otp or '').strip()

    if not normalized_email or '@' not in normalized_email:
        print(f"❌ OTP email skipped: invalid recipient '{email}'")
        return False

    if not normalized_username or not normalized_otp:
        print("❌ OTP email skipped: missing username or OTP")
        return False
    
    # Try Google Apps Script first (if configured)
    if Config.APPS_SCRIPT_URL:
        try:
            payload = {
                "email": normalized_email,
                "to": normalized_email,
                "recipient": normalized_email,
                "otp": normalized_otp,
                "username": normalized_username,
                "name": normalized_username,
            }
            response = requests.post(
                Config.APPS_SCRIPT_URL,
                json=payload,
                timeout=15
            )
            
            # Debug: Print response details
            print(f"📤 Apps Script Response Status: {response.status_code}")
            print(f"📥 Apps Script Response Text: {response.text[:200]}")  # First 200 chars
            
            if response.status_code == 200:
                try:
                    result = response.json()

                    # Accept both formats used by Apps Script handlers:
                    # {"status": "success"} and {"success": true}
                    is_success = (
                        result.get('success') is True
                        or str(result.get('status', '')).strip().lower() == 'success'
                    )

                    if is_success:
                        print(f"✅ Apps Script: OTP sent to {normalized_email}")
                        return True
                    print(f"❌ Apps Script error: {result.get('error', result)}")
                except ValueError as json_error:
                    print(f"❌ Apps Script JSON parse error: {json_error}")
                    print(f"   Raw response: {response.text}")
            else:
                print(f"❌ Apps Script HTTP error: {response.status_code}")
        except Exception as e:
            print(f"❌ Apps Script exception: {str(e)}")
    
    # Try Gmail SMTP (if configured)
    if Config.MAIL_USERNAME and Config.MAIL_PASSWORD:
        try:
            subject = "ExpenseTracker OTP Verification"
            html_body = f"""
            <html>
                <body style="font-family: 'Plus Jakarta Sans', Arial, sans-serif; background-color: #f8fafc; padding: 20px; margin: 0;">
                    <div style="max-width: 600px; margin: 0 auto; background: white; padding: 40px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                        <div style="text-align: center; margin-bottom: 30px;">
                            <h1 style="color: #0f172a; margin: 0; font-size: 28px;">💰 ExpenseTracker</h1>
                            <p style="color: #64748b; margin: 10px 0 0 0; font-size: 16px;">Verify Your Email</p>
                        </div>

                        <div style="margin-bottom: 30px;">
                            <p style="color: #334155; font-size: 16px; margin-bottom: 20px;">Hi <strong>{username}</strong>,</p>
                            <p style="color: #334155; font-size: 16px; margin-bottom: 20px;">Thank you for signing up! To complete your registration, please verify your email using the OTP below:</p>

                            <div style="background: #f1f5f9; border: 2px solid #e2e8f0; border-radius: 8px; padding: 20px; text-align: center; margin: 30px 0;">
                                <p style="color: #1e293b; font-size: 36px; font-weight: bold; margin: 0; letter-spacing: 10px; font-family: 'Courier New', monospace;">{otp}</p>
                            </div>

                            <p style="color: #94a3b8; font-size: 14px; margin-top: 20px;">⏰ This OTP will expire in <strong>10 minutes</strong>.</p>
                        </div>

                        <div style="background: #fef3c7; border-left: 4px solid #f59e0b; padding: 15px; border-radius: 4px; margin: 20px 0;">
                            <p style="color: #92400e; margin: 0; font-size: 14px;">
                                <strong>⚠️ Security Tip:</strong> Never share your OTP with anyone.
                            </p>
                        </div>

                        <div style="border-top: 1px solid #e2e8f0; padding-top: 20px; margin-top: 30px; text-align: center;">
                            <p style="color: #94a3b8; font-size: 12px; margin: 5px 0;">If you didn't sign up, please ignore this email.</p>
                            <p style="color: #94a3b8; font-size: 12px; margin: 10px 0 0 0;">© 2026 ExpenseTracker. All rights reserved.</p>
                        </div>
                    </div>
                </body>
            </html>
            """
            
            msg = Message(
                subject=subject,
                recipients=[normalized_email],
                html=html_body,
                sender=Config.MAIL_DEFAULT_SENDER
            )
            mail.send(msg)
            print(f"✅ Gmail SMTP: OTP sent to {normalized_email}")
            return True
        except BaseException as e:
            # Gunicorn may surface SMTP socket aborts as SystemExit; never let
            # OTP email transport failures crash the request worker.
            print(f"❌ Gmail SMTP error: {str(e)}")
    
    # Fallback to Resend API
    if not Config.RESEND_API_KEY:
        print(f"⚠️ No email service configured. OTP for {email}: {otp}")
        return False

    try:
        subject = "ExpenseTracker OTP Verification"
        html_body = f"""
        <html>
            <body style="font-family: 'Plus Jakarta Sans', Arial; background-color: #f8fafc; padding: 20px;">
                <div style="max-width: 600px; margin: 0 auto; background: white; padding: 40px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                    <div style="text-align: center; margin-bottom: 30px;">
                        <h1 style="color: #0f172a; margin: 0;">ExpenseTracker</h1>
                        <p style="color: #64748b; margin: 5px 0 0 0;">Verify Your Email</p>
                    </div>

                    <div style="margin-bottom: 30px;">
                        <p style="color: #334155; font-size: 16px; margin-bottom: 20px;">Hi <strong>{username}</strong>,</p>
                        <p style="color: #334155; font-size: 16px; margin-bottom: 20px;">Thank you for signing up! To complete your registration, please verify your email using the OTP below:</p>

                        <div style="background: #f1f5f9; border: 2px solid #e2e8f0; border-radius: 8px; padding: 20px; text-align: center; margin: 30px 0;">
                            <p style="color: #1e293b; font-size: 32px; font-weight: bold; margin: 0; letter-spacing: 8px;">{otp}</p>
                        </div>

                        <p style="color: #94a3b8; font-size: 14px; margin-top: 20px;">This OTP will expire in 10 minutes.</p>
                    </div>

                    <div style="border-top: 1px solid #e2e8f0; padding-top: 20px; text-align: center;">
                        <p style="color: #94a3b8; font-size: 12px; margin: 0;">If you didn't sign up for this account, please ignore this email.</p>
                        <p style="color: #94a3b8; font-size: 12px; margin: 10px 0 0 0;">© 2026 ExpenseTracker. All rights reserved.</p>
                    </div>
                </div>
            </body>
        </html>
        """

        response = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {Config.RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "from": Config.RESEND_FROM_EMAIL,
                "to": [normalized_email],
                "subject": subject,
                "html": html_body,
            },
            timeout=Config.RESEND_TIMEOUT,
        )
        if response.status_code in (200, 201):
            print(f"✅ Resend: OTP sent to {normalized_email}")
            return True
        print(f"❌ Resend API error: HTTP {response.status_code}")
        return False
    except Exception as e:
        print(f"❌ Error sending OTP email: {str(e)}")
        return False


def generate_otp():
    """Generate a 6-digit OTP"""
    return ''.join(random.choices(string.digits, k=Config.OTP_LENGTH))


def get_otp_expiry_time():
    """Get OTP expiry time"""
    return datetime.utcnow() + timedelta(minutes=Config.OTP_EXPIRY_MINUTES)
