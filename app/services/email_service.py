"""
Email service for sending verification codes and notifications.
Uses SendGrid for email delivery.
"""
from typing import Optional
import logging
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content
from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Email service for sending verification codes and notifications."""

    def __init__(self):
        """Initialize SendGrid client."""
        self.client = None
        if settings.SENDGRID_API_KEY and len(settings.SENDGRID_API_KEY) > 10:
            try:
                self.client = SendGridAPIClient(settings.SENDGRID_API_KEY)
            except Exception as e:
                logger.error(f"Failed to initialize SendGrid client: {e}")

    def is_configured(self) -> bool:
        """Check if email service is properly configured."""
        return self.client is not None

    async def send_verification_code(self, email: str, code: str) -> bool:
        """
        Send a 6-digit verification code to the user's email.

        Args:
            email: Recipient email address
            code: 6-digit verification code

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.is_configured():
            logger.warning("SendGrid not configured. Email not sent.")
            # In development, log the code
            if settings.DEBUG:
                logger.info(f"[DEV] Verification code for {email}: {code}")
                return True
            return False

        try:
            # Create email message
            from_email = Email(settings.EMAIL_FROM_ADDRESS, settings.EMAIL_FROM_NAME)
            to_email = To(email)
            subject = f"Your verification code is {code}"

            # HTML content
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        line-height: 1.6;
                        color: #333;
                    }}
                    .container {{
                        max-width: 600px;
                        margin: 0 auto;
                        padding: 20px;
                    }}
                    .header {{
                        background-color: #4F46E5;
                        color: white;
                        padding: 20px;
                        text-align: center;
                        border-radius: 8px 8px 0 0;
                    }}
                    .content {{
                        background-color: #f9fafb;
                        padding: 30px;
                        border-radius: 0 0 8px 8px;
                    }}
                    .code {{
                        font-size: 32px;
                        font-weight: bold;
                        color: #4F46E5;
                        letter-spacing: 8px;
                        text-align: center;
                        padding: 20px;
                        background-color: white;
                        border-radius: 8px;
                        margin: 20px 0;
                    }}
                    .footer {{
                        text-align: center;
                        color: #666;
                        font-size: 12px;
                        margin-top: 20px;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Take My Dictation</h1>
                    </div>
                    <div class="content">
                        <h2>Email Verification</h2>
                        <p>Thank you for signing up! Please use the verification code below to complete your registration:</p>

                        <div class="code">{code}</div>

                        <p>This code will expire in <strong>15 minutes</strong>.</p>

                        <p>If you didn't request this code, you can safely ignore this email.</p>

                        <div class="footer">
                            <p>&copy; 2026 Take My Dictation. All rights reserved.</p>
                        </div>
                    </div>
                </div>
            </body>
            </html>
            """

            # Plain text content
            text_content = f"""
            Take My Dictation - Email Verification

            Thank you for signing up!

            Your verification code is: {code}

            This code will expire in 15 minutes.

            If you didn't request this code, you can safely ignore this email.

            © 2026 Take My Dictation. All rights reserved.
            """

            # Create message
            message = Mail(
                from_email=from_email,
                to_emails=to_email,
                subject=subject,
                plain_text_content=text_content,
                html_content=html_content
            )

            # Send email
            response = self.client.send(message)

            if response.status_code in [200, 201, 202]:
                logger.info(f"Verification code sent successfully to {email}")
                return True
            else:
                logger.error(f"Failed to send email: {response.status_code} - {response.body}")
                return False

        except Exception as e:
            logger.error(f"Error sending verification email to {email}: {e}")
            return False

    async def send_welcome_email(self, email: str, name: Optional[str] = None) -> bool:
        """
        Send a welcome email after successful verification.

        Args:
            email: Recipient email address
            name: User's name (optional)

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.is_configured():
            logger.warning("SendGrid not configured. Email not sent.")
            if settings.DEBUG:
                logger.info(f"[DEV] Welcome email for {email}")
            return False

        try:
            greeting = f"Hi {name}" if name else "Welcome"

            from_email = Email(settings.EMAIL_FROM_ADDRESS, settings.EMAIL_FROM_NAME)
            to_email = To(email)
            subject = "Welcome to Take My Dictation!"

            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        line-height: 1.6;
                        color: #333;
                    }}
                    .container {{
                        max-width: 600px;
                        margin: 0 auto;
                        padding: 20px;
                    }}
                    .header {{
                        background-color: #4F46E5;
                        color: white;
                        padding: 20px;
                        text-align: center;
                        border-radius: 8px 8px 0 0;
                    }}
                    .content {{
                        background-color: #f9fafb;
                        padding: 30px;
                        border-radius: 0 0 8px 8px;
                    }}
                    .button {{
                        display: inline-block;
                        background-color: #4F46E5;
                        color: white;
                        padding: 12px 30px;
                        text-decoration: none;
                        border-radius: 6px;
                        margin: 20px 0;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Welcome to Take My Dictation!</h1>
                    </div>
                    <div class="content">
                        <p>{greeting},</p>

                        <p>Your email has been verified successfully! You're all set to start using Take My Dictation.</p>

                        <p><strong>What's next?</strong></p>
                        <ul>
                            <li>Choose your subscription plan</li>
                            <li>Start recording and get AI-powered summaries</li>
                            <li>Export to Word or PDF</li>
                        </ul>

                        <p>If you have any questions, feel free to reach out to our support team.</p>

                        <p>Happy dictating!</p>

                        <p style="margin-top: 30px;">
                            <small>&copy; 2026 Take My Dictation. All rights reserved.</small>
                        </p>
                    </div>
                </div>
            </body>
            </html>
            """

            text_content = f"""
            Welcome to Take My Dictation!

            {greeting},

            Your email has been verified successfully! You're all set to start using Take My Dictation.

            What's next?
            - Choose your subscription plan
            - Start recording and get AI-powered summaries
            - Export to Word or PDF

            If you have any questions, feel free to reach out to our support team.

            Happy dictating!

            © 2026 Take My Dictation. All rights reserved.
            """

            message = Mail(
                from_email=from_email,
                to_emails=to_email,
                subject=subject,
                plain_text_content=text_content,
                html_content=html_content
            )

            response = self.client.send(message)

            if response.status_code in [200, 201, 202]:
                logger.info(f"Welcome email sent successfully to {email}")
                return True
            else:
                logger.error(f"Failed to send welcome email: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Error sending welcome email to {email}: {e}")
            return False


# Global email service instance
email_service = EmailService()
