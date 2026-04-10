"""Email verification helpers: OTP generation and sending.

Development mode logs the code to the console so SMTP is optional locally.
Production requires ``smtp_*`` settings; missing host results in a warning and
no send. The HTML template uses letter-spacing and spaced digits so the code
stays readable in common email clients (accessibility / UX).

Added: 2026-04-03
"""
import random
import string
from datetime import datetime, timedelta, timezone

from app.config import get_settings, Environment
from app.utils.logging import get_logger

logger = get_logger("email")

CODE_LENGTH = 6
CODE_EXPIRY_MINUTES = 15


def generate_verification_code() -> str:
    return "".join(random.choices(string.digits, k=CODE_LENGTH))


def verification_code_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(minutes=CODE_EXPIRY_MINUTES)


async def send_verification_email(
    email: str, code: str, full_name: str | None = None
) -> None:
    settings = get_settings()

    # Dev: no SMTP — print code directly to stdout.
    if settings.app_env == Environment.DEVELOPMENT:
        border = "=" * 60
        print(f"\n[backend] {border}")
        print(f"[backend]   EMAIL VERIFICATION CODE (Dev Mode)")
        print(f"[backend]   To:      {email}")
        print(f"[backend]   Name:    {full_name or 'N/A'}")
        print(f"[backend]   Code:    {code}")
        print(f"[backend]   Expires: {CODE_EXPIRY_MINUTES} minutes")
        print(f"[backend] {border}\n", flush=True)
        return

    # Non-dev without SMTP: fail soft (log) so signup flow doesn't crash in misconfigured envs.
    if not settings.smtp_host:
        logger.warning(
            "SMTP not configured — cannot send verification email",
            extra={"email": email},
        )
        return

    try:
        import aiosmtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"{code} is your {settings.app_name} verification code"
        msg["From"] = settings.smtp_from_email
        msg["To"] = email

        plain = (
            f"Hi {full_name or 'there'},\n\n"
            f"Your verification code is: {code}\n\n"
            f"Enter this code on the verification page to activate your account.\n"
            f"This code expires in {CODE_EXPIRY_MINUTES} minutes.\n\n"
            "If you did not create an account, you can safely ignore this email."
        )

        # Spaced + letter-spacing in HTML improves legibility in narrow/mobile mail clients.
        spaced_code = " ".join(code)
        html = f"""\
<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; padding: 40px 20px; background: #f9fafb;">
  <div style="max-width: 480px; margin: 0 auto; background: #fff; border-radius: 12px; padding: 32px; box-shadow: 0 1px 3px rgba(0,0,0,.1);">
    <h2 style="margin: 0 0 8px; font-size: 20px;">Verify your email</h2>
    <p style="color: #555; font-size: 15px;">Hi {full_name or 'there'},</p>
    <p style="color: #555; font-size: 15px;">Enter this code to verify your account:</p>
    <div style="text-align: center; margin: 28px 0;">
      <div style="display: inline-block; padding: 16px 32px; background: #f4f4f5; border-radius: 12px; letter-spacing: 8px; font-size: 32px; font-weight: 700; font-family: monospace; color: #18181b;">
        {spaced_code}
      </div>
    </div>
    <p style="color: #999; font-size: 13px;">This code expires in {CODE_EXPIRY_MINUTES} minutes.</p>
    <hr style="border: none; border-top: 1px solid #eee; margin: 24px 0;" />
    <p style="color: #bbb; font-size: 12px;">If you didn&rsquo;t create an account, ignore this email.</p>
  </div>
</body>
</html>"""

        msg.attach(MIMEText(plain, "plain"))
        msg.attach(MIMEText(html, "html"))

        await aiosmtplib.send(
            msg,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user or None,
            password=settings.smtp_password or None,
            use_tls=settings.smtp_use_tls,
        )
        logger.info("Verification email sent", extra={"email": email})
    except Exception as e:
        logger.error(
            f"Failed to send verification email: {e}",
            extra={"email": email},
        )
