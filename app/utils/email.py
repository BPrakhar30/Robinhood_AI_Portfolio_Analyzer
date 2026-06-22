"""Email verification helpers: OTP generation and sending.

Dev mode logs the code to the console (SMTP optional). Production needs
``smtp_*`` settings; missing host logs a warning and skips send.
"""

import hashlib
import random
import string
from datetime import datetime, timedelta, timezone

from app.config import get_settings, Environment
from app.utils.logging import get_logger

logger = get_logger("email")


def _redact(email: str) -> str:
    """SHA-256 prefix so logs are indexable without exposing PII."""
    return hashlib.sha256(email.lower().encode()).hexdigest()[:16]

CODE_LENGTH = 6
CODE_EXPIRY_MINUTES = 15
RESET_TOKEN_EXPIRY_MINUTES = 15


def generate_verification_code() -> str:
    return "".join(random.choices(string.digits, k=CODE_LENGTH))


def verification_code_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(minutes=CODE_EXPIRY_MINUTES)


async def send_verification_email(
    email: str, code: str, full_name: str | None = None
) -> None:
    settings = get_settings()

    # Dev: no SMTP  -  print code directly to stdout.
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
            "SMTP not configured - cannot send verification email",
            extra={"email_hash": _redact(email)},
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

        greeting = full_name.split()[0] if full_name else "there"

        plain = (
            f"Hi {greeting},\n\n"
            f"Welcome to Portfolio Copilot! Your verification code is: {code}\n\n"
            f"Enter this code on the verification page to activate your account.\n"
            f"This code expires in {CODE_EXPIRY_MINUTES} minutes.\n\n"
            "If you did not create an account, you can safely ignore this email.\n\n"
            "-- The Portfolio Copilot Team"
        )

        code_cells = "".join(
            f'<td style="width:44px;height:52px;text-align:center;font-size:28px;'
            f'font-weight:700;font-family:\'SF Mono\',Menlo,Consolas,monospace;'
            f'color:#18181b;background:#f4f4f5;border-radius:8px;border:1px solid #e4e4e7;">{d}</td>'
            f'<td style="width:6px;"></td>'
            for d in code
        )

        html = f"""\
<html>
<head><meta charset="utf-8"/></head>
<body style="margin:0;padding:0;background:#f4f4f5;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f4f5;padding:40px 16px;">
    <tr><td align="center">
      <table width="100%" cellpadding="0" cellspacing="0" style="max-width:520px;background:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,.06);">
        <!-- Header -->
        <tr>
          <td style="padding:32px 40px 0 40px;">
            <table cellpadding="0" cellspacing="0"><tr>
              <td style="width:36px;height:36px;background:#f59e0b;border-radius:10px;text-align:center;vertical-align:middle;">
                <span style="color:#fff;font-size:16px;font-weight:700;">P</span>
              </td>
              <td style="padding-left:10px;font-size:15px;font-weight:600;color:#18181b;">Portfolio Copilot</td>
            </tr></table>
          </td>
        </tr>
        <!-- Body -->
        <tr>
          <td style="padding:28px 40px 0 40px;">
            <h1 style="margin:0 0 6px;font-size:22px;font-weight:700;color:#18181b;">Verify your email</h1>
            <p style="margin:0;font-size:15px;color:#52525b;line-height:1.6;">
              Hi {greeting}, welcome aboard! Enter this code to confirm your email and start exploring your portfolio with AI.
            </p>
          </td>
        </tr>
        <!-- Code block -->
        <tr>
          <td style="padding:28px 40px;">
            <table cellpadding="0" cellspacing="0" style="margin:0 auto;">
              <tr>{code_cells}</tr>
            </table>
          </td>
        </tr>
        <!-- Expiry -->
        <tr>
          <td style="padding:0 40px;">
            <p style="margin:0;font-size:13px;color:#a1a1aa;text-align:center;">
              This code expires in {CODE_EXPIRY_MINUTES} minutes. Don&rsquo;t share it with anyone.
            </p>
          </td>
        </tr>
        <!-- Divider -->
        <tr><td style="padding:28px 40px 0 40px;"><hr style="border:none;border-top:1px solid #e4e4e7;margin:0;" /></td></tr>
        <!-- Footer -->
        <tr>
          <td style="padding:20px 40px 32px 40px;">
            <p style="margin:0 0 4px;font-size:12px;color:#a1a1aa;line-height:1.5;">
              If you didn&rsquo;t create an account on Portfolio Copilot, ignore this email.
            </p>
            <p style="margin:0;font-size:12px;color:#d4d4d8;">
              &copy; {settings.app_name} &mdash; AI-powered portfolio intelligence. Not financial advice.
            </p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
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
            start_tls=settings.smtp_use_tls,
        )
        logger.info("Verification email sent", extra={"email_hash": _redact(email)})
    except Exception as e:
        logger.error(
            "Failed to send verification email",
            extra={"email_hash": _redact(email), "error": str(e)},
        )


def password_reset_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(minutes=RESET_TOKEN_EXPIRY_MINUTES)


async def send_password_reset_email(
    email: str, token: str, full_name: str | None = None
) -> None:
    settings = get_settings()
    frontend_url = getattr(settings, "frontend_url", "http://localhost:3000")
    reset_link = f"{frontend_url}/reset-password?token={token}"

    if settings.app_env == Environment.DEVELOPMENT:
        border = "=" * 60
        print(f"\n[backend] {border}")
        print(f"[backend]   PASSWORD RESET (Dev Mode)")
        print(f"[backend]   To:      {email}")
        print(f"[backend]   Name:    {full_name or 'N/A'}")
        print(f"[backend]   Token:   {token}")
        print(f"[backend]   Link:    {reset_link}")
        print(f"[backend]   Expires: {RESET_TOKEN_EXPIRY_MINUTES} minutes")
        print(f"[backend] {border}\n", flush=True)
        return

    if not settings.smtp_host:
        logger.warning(
            "SMTP not configured - cannot send password reset email",
            extra={"email_hash": _redact(email)},
        )
        return

    try:
        import aiosmtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Reset your {settings.app_name} password"
        msg["From"] = settings.smtp_from_email
        msg["To"] = email

        greeting = full_name.split()[0] if full_name else "there"

        plain = (
            f"Hi {greeting},\n\n"
            f"We received a request to reset your Portfolio Copilot password.\n\n"
            f"Click this link to set a new password:\n{reset_link}\n\n"
            f"This link expires in {RESET_TOKEN_EXPIRY_MINUTES} minutes.\n\n"
            "If you did not request a password reset, you can safely ignore this email.\n\n"
            "-- The Portfolio Copilot Team"
        )

        html = f"""\
<html>
<head><meta charset="utf-8"/></head>
<body style="margin:0;padding:0;background:#f4f4f5;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f4f5;padding:40px 16px;">
    <tr><td align="center">
      <table width="100%" cellpadding="0" cellspacing="0" style="max-width:520px;background:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,.06);">
        <!-- Header -->
        <tr>
          <td style="padding:32px 40px 0 40px;">
            <table cellpadding="0" cellspacing="0"><tr>
              <td style="width:36px;height:36px;background:#f59e0b;border-radius:10px;text-align:center;vertical-align:middle;">
                <span style="color:#fff;font-size:16px;font-weight:700;">P</span>
              </td>
              <td style="padding-left:10px;font-size:15px;font-weight:600;color:#18181b;">Portfolio Copilot</td>
            </tr></table>
          </td>
        </tr>
        <!-- Body -->
        <tr>
          <td style="padding:28px 40px 0 40px;">
            <h1 style="margin:0 0 6px;font-size:22px;font-weight:700;color:#18181b;">Reset your password</h1>
            <p style="margin:0;font-size:15px;color:#52525b;line-height:1.6;">
              Hi {greeting}, we received a request to reset the password on your Portfolio Copilot account.
              Click the button below to choose a new one.
            </p>
          </td>
        </tr>
        <!-- CTA Button -->
        <tr>
          <td style="padding:28px 40px;" align="center">
            <a href="{reset_link}" style="display:inline-block;padding:14px 40px;background:#f59e0b;color:#18181b;border-radius:10px;text-decoration:none;font-weight:700;font-size:15px;letter-spacing:0.3px;">
              Reset Password
            </a>
          </td>
        </tr>
        <!-- Fallback link -->
        <tr>
          <td style="padding:0 40px;">
            <p style="margin:0;font-size:12px;color:#a1a1aa;text-align:center;word-break:break-all;">
              Or copy this link: <a href="{reset_link}" style="color:#f59e0b;">{reset_link}</a>
            </p>
          </td>
        </tr>
        <!-- Expiry -->
        <tr>
          <td style="padding:16px 40px 0 40px;">
            <p style="margin:0;font-size:13px;color:#a1a1aa;text-align:center;">
              This link expires in {RESET_TOKEN_EXPIRY_MINUTES} minutes.
            </p>
          </td>
        </tr>
        <!-- Divider -->
        <tr><td style="padding:28px 40px 0 40px;"><hr style="border:none;border-top:1px solid #e4e4e7;margin:0;" /></td></tr>
        <!-- Footer -->
        <tr>
          <td style="padding:20px 40px 32px 40px;">
            <p style="margin:0 0 4px;font-size:12px;color:#a1a1aa;line-height:1.5;">
              If you didn&rsquo;t request a password reset, ignore this email. Your password won&rsquo;t change.
            </p>
            <p style="margin:0;font-size:12px;color:#d4d4d8;">
              &copy; {settings.app_name} &mdash; AI-powered portfolio intelligence. Not financial advice.
            </p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
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
            start_tls=settings.smtp_use_tls,
        )
        logger.info("Password reset email sent", extra={"email_hash": _redact(email)})
    except Exception as e:
        logger.error(
            "Failed to send password reset email",
            extra={"email_hash": _redact(email), "error": str(e)},
        )
