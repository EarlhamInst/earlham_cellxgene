"""
Email Service

Sends access codes and notifications via email.

Constitutional Alignment:
- Principle II (Modular Architecture): Isolated email logic
- Principle IV (Fail-Fast): Clear error handling
"""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from dataclasses import dataclass


@dataclass
class EmailConfig:
    """Email service configuration."""
    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    from_email: str
    from_name: str = "CellXGene Explorer"
    use_tls: bool = True
    base_url: str = "http://localhost:8000"


class EmailService:
    """
    Service for sending emails.
    
    Supports SMTP with TLS for sending access codes and notifications.
    """
    
    def __init__(self, config: EmailConfig, logger: logging.Logger = None):
        """
        Initialize email service.
        
        Args:
            config: Email configuration
            logger: Optional logger instance
        """
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
    
    def send_access_code(
        self,
        to_email: str,
        access_code: str,
        dataset_name: str,
        expires_at: str
    ) -> bool:
        """
        Send an access code email to a reviewer.
        
        Args:
            to_email: Recipient email address
            access_code: The 6-digit access code
            dataset_name: Name of the dataset
            expires_at: ISO timestamp when access expires
            
        Returns:
            True if email was sent successfully
        """
        subject = f"Your CellXGene Access Code for: {dataset_name}"
        
        # Format expiry date nicely
        from datetime import datetime
        try:
            expires = datetime.fromisoformat(expires_at)
            expires_formatted = expires.strftime("%B %d, %Y")
        except Exception:
            expires_formatted = expires_at
        
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background: linear-gradient(135deg, #1a365d 0%, #2a6496 100%);
            color: white;
            padding: 30px;
            text-align: center;
            border-radius: 8px 8px 0 0;
        }}
        .content {{
            background: #f9f9f9;
            padding: 30px;
            border: 1px solid #e0e0e0;
            border-top: none;
            border-radius: 0 0 8px 8px;
        }}
        .code-box {{
            background: white;
            border: 2px solid #2a6496;
            border-radius: 8px;
            padding: 20px;
            text-align: center;
            margin: 20px 0;
        }}
        .code {{
            font-size: 36px;
            font-weight: bold;
            letter-spacing: 8px;
            color: #1a365d;
            font-family: 'Courier New', monospace;
        }}
        .dataset-name {{
            background: #e8f4f8;
            padding: 10px 15px;
            border-radius: 4px;
            font-weight: 600;
            color: #2a6496;
        }}
        .footer {{
            text-align: center;
            padding: 20px;
            color: #666;
            font-size: 12px;
        }}
        .warning {{
            background: #fff3cd;
            border: 1px solid #ffc107;
            border-radius: 4px;
            padding: 10px 15px;
            margin-top: 20px;
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🔬 CellXGene Explorer</h1>
        <p>Earlham Institute</p>
    </div>
    <div class="content">
        <p>Hello,</p>
        
        <p>You've been granted access to a private dataset. Use the code below to access it:</p>
        
        <div class="code-box">
            <div class="code">{access_code}</div>
            <p style="margin: 10px 0 0 0; color: #666; font-size: 14px;">Your access code</p>
        </div>
        
        <p><strong>Dataset:</strong></p>
        <p class="dataset-name">{dataset_name}</p>
        
        <p>To access the dataset:</p>
        <ol>
            <li>Click the button below to go to the private access page</li>
            <li>Enter your email address: <strong>{to_email}</strong></li>
            <li>Enter the access code above</li>
        </ol>
        
        <div style="text-align: center; margin: 25px 0;">
            <a href="{self.config.base_url}/private" style="
                display: inline-block;
                background: linear-gradient(135deg, #1a365d 0%, #2a6496 100%);
                color: white;
                text-decoration: none;
                padding: 15px 30px;
                border-radius: 8px;
                font-weight: bold;
                font-size: 16px;
            ">Access Private Dataset →</a>
        </div>
        
        <p style="text-align: center; color: #666; font-size: 13px;">
            Or copy this link: <a href="{self.config.base_url}/private" style="color: #2a6496;">{self.config.base_url}/private</a>
        </p>
        
        <div class="warning">
            ⏰ <strong>This code expires on {expires_formatted}</strong>
            <br>
            Do not share this code with anyone else.
        </div>
    </div>
    <div class="footer">
        <p>Earlham Institute | CellXGene Explorer</p>
        <p>If you did not request this access, please ignore this email.</p>
    </div>
</body>
</html>
"""
        
        text_body = f"""
CellXGene Explorer - Access Code

You've been granted access to a private dataset.

Your Access Code: {access_code}

Dataset: {dataset_name}

To access the dataset:
1. Go to: {self.config.base_url}/private
2. Enter your email address: {to_email}
3. Enter the access code above

This code expires on {expires_formatted}.
Do not share this code with anyone else.

---
Earlham Institute | CellXGene Explorer
If you did not request this access, please ignore this email.
"""
        
        return self._send_email(to_email, subject, text_body, html_body)
    
    def send_share_link(
        self,
        to_email: str,
        share_url: str,
        dataset_name: str,
        expires_at: str,
        created_by: Optional[str] = None,
        label: Optional[str] = None
    ) -> bool:
        """
        Send a shareable link email.
        
        Args:
            to_email: Recipient email address
            share_url: The full shareable URL
            dataset_name: Name of the dataset
            expires_at: ISO timestamp when link expires
            created_by: Email of person who created the link
            label: Optional label describing the link purpose
            
        Returns:
            True if email was sent successfully
        """
        subject = f"Shared CellXGene Dataset: {dataset_name}"
        
        # Format expiry date nicely
        from datetime import datetime
        try:
            expires = datetime.fromisoformat(expires_at)
            expires_formatted = expires.strftime("%B %d, %Y")
        except Exception:
            expires_formatted = expires_at
        
        # Build the label/context section
        context_html = ""
        context_text = ""
        if label:
            context_html = f'<p style="color: #666; font-style: italic;">"{label}"</p>'
            context_text = f'Note: "{label}"\n\n'
        
        if created_by:
            context_html += f'<p style="color: #666; font-size: 14px;">Shared by: {created_by}</p>'
            context_text += f"Shared by: {created_by}\n"
        
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background: linear-gradient(135deg, #1a365d 0%, #2a6496 100%);
            color: white;
            padding: 30px;
            text-align: center;
            border-radius: 8px 8px 0 0;
        }}
        .content {{
            background: #f9f9f9;
            padding: 30px;
            border: 1px solid #e0e0e0;
            border-top: none;
            border-radius: 0 0 8px 8px;
        }}
        .dataset-name {{
            background: #e8f4f8;
            padding: 15px 20px;
            border-radius: 4px;
            font-weight: 600;
            color: #2a6496;
            font-size: 18px;
            text-align: center;
            margin: 20px 0;
        }}
        .footer {{
            text-align: center;
            padding: 20px;
            color: #666;
            font-size: 12px;
        }}
        .info-box {{
            background: #f0f7ff;
            border: 1px solid #2a6496;
            border-radius: 4px;
            padding: 15px;
            margin-top: 20px;
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🔬 CellXGene Explorer</h1>
        <p>Earlham Institute</p>
    </div>
    <div class="content">
        <p>Hello,</p>
        
        <p>You've been invited to explore a single-cell dataset. Click the button below to access it immediately:</p>
        
        <p class="dataset-name">{dataset_name}</p>
        
        {context_html}
        
        <div style="text-align: center; margin: 30px 0;">
            <a href="{share_url}" style="
                display: inline-block;
                background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
                color: white;
                text-decoration: none;
                padding: 18px 40px;
                border-radius: 8px;
                font-weight: bold;
                font-size: 18px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            ">🚀 Open Dataset</a>
        </div>
        
        <p style="text-align: center; color: #666; font-size: 13px;">
            Or copy this link: <a href="{share_url}" style="color: #2a6496; word-break: break-all;">{share_url}</a>
        </p>
        
        <div class="info-box">
            ℹ️ <strong>One-click access</strong> - No login required. Just click the button above.
            <br><br>
            ⏰ <strong>Link expires:</strong> {expires_formatted}
        </div>
    </div>
    <div class="footer">
        <p>Earlham Institute | CellXGene Explorer</p>
        <p>If you were not expecting this email, you can safely ignore it.</p>
    </div>
</body>
</html>
"""
        
        text_body = f"""
CellXGene Explorer - Shared Dataset

You've been invited to explore a single-cell dataset!

Dataset: {dataset_name}

{context_text}
Click here to access immediately (no login required):
{share_url}

This link expires on {expires_formatted}.

---
Earlham Institute | CellXGene Explorer
If you were not expecting this email, you can safely ignore it.
"""
        
        return self._send_email(to_email, subject, text_body, html_body)
    
    def send_access_revoked(self, to_email: str, dataset_name: str) -> bool:
        """
        Send notification that access has been revoked.
        
        Args:
            to_email: Recipient email address
            dataset_name: Name of the dataset
            
        Returns:
            True if email was sent successfully
        """
        subject = f"CellXGene Access Revoked: {dataset_name}"
        
        text_body = f"""
Your access to the following dataset has been revoked:

Dataset: {dataset_name}

If you believe this is an error, please contact the dataset owner.

---
Earlham Institute | CellXGene Explorer
"""
        
        return self._send_email(to_email, subject, text_body)
    
    def _send_email(
        self,
        to_email: str,
        subject: str,
        text_body: str,
        html_body: Optional[str] = None
    ) -> bool:
        """
        Send an email.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            text_body: Plain text body
            html_body: Optional HTML body
            
        Returns:
            True if email was sent successfully
        """
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.config.from_name} <{self.config.from_email}>"
            msg['To'] = to_email
            
            # Attach plain text
            msg.attach(MIMEText(text_body, 'plain'))
            
            # Attach HTML if provided
            if html_body:
                msg.attach(MIMEText(html_body, 'html'))
            
            # Connect and send
            if self.config.use_tls:
                server = smtplib.SMTP(self.config.smtp_host, self.config.smtp_port)
                server.starttls()
            else:
                server = smtplib.SMTP(self.config.smtp_host, self.config.smtp_port)
            
            if self.config.smtp_username and self.config.smtp_password:
                server.login(self.config.smtp_username, self.config.smtp_password)
            
            server.sendmail(
                self.config.from_email,
                to_email,
                msg.as_string()
            )
            server.quit()
            
            self.logger.info(f"Email sent to {to_email}: {subject}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False


class MockEmailService:
    """
    Mock email service for development/testing.
    
    Logs emails instead of sending them.
    """
    
    def __init__(self, logger: logging.Logger = None):
        self.logger = logger or logging.getLogger(__name__)
        self.sent_emails = []
    
    def send_access_code(
        self,
        to_email: str,
        access_code: str,
        dataset_name: str,
        expires_at: str
    ) -> bool:
        """Log access code email."""
        email_record = {
            "type": "access_code",
            "to": to_email,
            "code": access_code,
            "dataset": dataset_name,
            "expires": expires_at
        }
        self.sent_emails.append(email_record)
        
        self.logger.warning(
            f"[MOCK EMAIL] Access code for {to_email}: {access_code} "
            f"(Dataset: {dataset_name})"
        )
        return True
    
    def send_access_revoked(self, to_email: str, dataset_name: str) -> bool:
        """Log revocation email."""
        self.logger.warning(
            f"[MOCK EMAIL] Access revoked for {to_email} (Dataset: {dataset_name})"
        )
        return True
    
    def send_share_link(
        self,
        to_email: str,
        share_url: str,
        dataset_name: str,
        expires_at: str,
        created_by: Optional[str] = None,
        label: Optional[str] = None
    ) -> bool:
        """Log share link email."""
        email_record = {
            "type": "share_link",
            "to": to_email,
            "url": share_url,
            "dataset": dataset_name,
            "expires": expires_at,
            "created_by": created_by,
            "label": label
        }
        self.sent_emails.append(email_record)
        
        self.logger.warning(
            f"[MOCK EMAIL] Share link for {to_email}: {share_url} "
            f"(Dataset: {dataset_name})"
        )
        return True
