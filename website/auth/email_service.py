"""
Service d'envoi d'emails
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import sys
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import EMAIL_CONFIG, SITE_URL


def send_email(to_email: str, subject: str, html_content: str) -> bool:
    """
    Envoie un email
    Retourne True si succès
    """
    if not EMAIL_CONFIG['password']:
        print("⚠️ Email password not configured")
        return False
    
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = EMAIL_CONFIG['address']
        msg['To'] = to_email
        
        html_part = MIMEText(html_content, 'html')
        msg.attach(html_part)
        
        with smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port']) as server:
            server.starttls()
            server.login(EMAIL_CONFIG['address'], EMAIL_CONFIG['password'])
            server.sendmail(EMAIL_CONFIG['address'], to_email, msg.as_string())
        
        return True
    except Exception as e:
        print(f"❌ Erreur envoi email: {e}")
        return False


def send_welcome_email(to_email: str, name: str, language: str = 'fr') -> bool:
    """Envoie l'email de bienvenue"""
    if language == 'fr':
        subject = "Bienvenue sur MIA IA SYSTEM!"
        content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; background-color: #0A0E17; color: #FFFFFF; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background-color: #131722; border-radius: 12px; padding: 30px;">
                <h1 style="color: #00D4AA;">🎉 Bienvenue, {name}!</h1>
                <p>Votre compte MIA IA SYSTEM a été créé avec succès.</p>
                <p>Vous pouvez maintenant accéder au dashboard et découvrir toutes les fonctionnalités de MIA.</p>
                <a href="{SITE_URL}" style="display: inline-block; background-color: #00D4AA; color: #0A0E17; padding: 12px 24px; text-decoration: none; border-radius: 8px; font-weight: bold; margin-top: 20px;">
                    Accéder au Dashboard
                </a>
                <p style="color: #8892A0; margin-top: 30px; font-size: 12px;">
                    Cet email a été envoyé par MIA IA SYSTEM.<br>
                    Si vous n'avez pas créé de compte, ignorez cet email.
                </p>
            </div>
        </body>
        </html>
        """
    else:
        subject = "Welcome to MIA IA SYSTEM!"
        content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; background-color: #0A0E17; color: #FFFFFF; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background-color: #131722; border-radius: 12px; padding: 30px;">
                <h1 style="color: #00D4AA;">🎉 Welcome, {name}!</h1>
                <p>Your MIA IA SYSTEM account has been created successfully.</p>
                <p>You can now access the dashboard and discover all MIA features.</p>
                <a href="{SITE_URL}" style="display: inline-block; background-color: #00D4AA; color: #0A0E17; padding: 12px 24px; text-decoration: none; border-radius: 8px; font-weight: bold; margin-top: 20px;">
                    Access Dashboard
                </a>
                <p style="color: #8892A0; margin-top: 30px; font-size: 12px;">
                    This email was sent by MIA IA SYSTEM.<br>
                    If you did not create an account, please ignore this email.
                </p>
            </div>
        </body>
        </html>
        """
    
    return send_email(to_email, subject, content)


def send_password_reset_email(to_email: str, token: str, language: str = 'fr') -> bool:
    """Envoie l'email de reset password"""
    reset_url = f"{SITE_URL}?reset_token={token}"
    
    if language == 'fr':
        subject = "Réinitialisation de votre mot de passe - MIA IA SYSTEM"
        content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; background-color: #0A0E17; color: #FFFFFF; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background-color: #131722; border-radius: 12px; padding: 30px;">
                <h1 style="color: #00D4AA;">🔐 Réinitialisation du mot de passe</h1>
                <p>Vous avez demandé à réinitialiser votre mot de passe.</p>
                <p>Cliquez sur le bouton ci-dessous pour créer un nouveau mot de passe:</p>
                <a href="{reset_url}" style="display: inline-block; background-color: #00D4AA; color: #0A0E17; padding: 12px 24px; text-decoration: none; border-radius: 8px; font-weight: bold; margin-top: 20px;">
                    Réinitialiser mon mot de passe
                </a>
                <p style="color: #8892A0; margin-top: 30px; font-size: 12px;">
                    Ce lien expire dans 1 heure.<br>
                    Si vous n'avez pas demandé cette réinitialisation, ignorez cet email.
                </p>
            </div>
        </body>
        </html>
        """
    else:
        subject = "Reset your password - MIA IA SYSTEM"
        content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; background-color: #0A0E17; color: #FFFFFF; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background-color: #131722; border-radius: 12px; padding: 30px;">
                <h1 style="color: #00D4AA;">🔐 Password Reset</h1>
                <p>You requested to reset your password.</p>
                <p>Click the button below to create a new password:</p>
                <a href="{reset_url}" style="display: inline-block; background-color: #00D4AA; color: #0A0E17; padding: 12px 24px; text-decoration: none; border-radius: 8px; font-weight: bold; margin-top: 20px;">
                    Reset my password
                </a>
                <p style="color: #8892A0; margin-top: 30px; font-size: 12px;">
                    This link expires in 1 hour.<br>
                    If you did not request this reset, please ignore this email.
                </p>
            </div>
        </body>
        </html>
        """
    
    return send_email(to_email, subject, content)


def send_newsletter_confirmation(to_email: str, language: str = 'fr') -> bool:
    """Envoie la confirmation d'inscription à la newsletter"""
    if language == 'fr':
        subject = "Inscription à la newsletter MIA IA SYSTEM confirmée!"
        content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; background-color: #0A0E17; color: #FFFFFF; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background-color: #131722; border-radius: 12px; padding: 30px;">
                <h1 style="color: #00D4AA;">✅ Inscription confirmée!</h1>
                <p>Merci de vous être inscrit à la newsletter de MIA IA SYSTEM.</p>
                <p>Vous recevrez désormais les dernières actualités et mises à jour.</p>
                <p style="color: #8892A0; margin-top: 30px; font-size: 12px;">
                    Pour vous désinscrire, contactez-nous à MIA.IA.SYSTEM@GMAIL.COM
                </p>
            </div>
        </body>
        </html>
        """
    else:
        subject = "Newsletter subscription confirmed - MIA IA SYSTEM!"
        content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; background-color: #0A0E17; color: #FFFFFF; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background-color: #131722; border-radius: 12px; padding: 30px;">
                <h1 style="color: #00D4AA;">✅ Subscription confirmed!</h1>
                <p>Thank you for subscribing to the MIA IA SYSTEM newsletter.</p>
                <p>You will now receive the latest news and updates.</p>
                <p style="color: #8892A0; margin-top: 30px; font-size: 12px;">
                    To unsubscribe, contact us at MIA.IA.SYSTEM@GMAIL.COM
                </p>
            </div>
        </body>
        </html>
        """
    
    return send_email(to_email, subject, content)



