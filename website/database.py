"""
Gestion de la base de données SQLite
"""
import sqlite3
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List
import bcrypt

from config import DATABASE_PATH


def get_connection():
    """Crée une connexion à la base de données"""
    conn = sqlite3.connect(str(DATABASE_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """Initialise la base de données avec les tables nécessaires"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Table des utilisateurs
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT,
            name TEXT,
            google_id TEXT,
            is_verified INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            language TEXT DEFAULT 'fr'
        )
    """)
    
    # Table newsletter
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS newsletter (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            subscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active INTEGER DEFAULT 1,
            language TEXT DEFAULT 'fr'
        )
    """)
    
    # Table reset password tokens
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS password_resets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL,
            used INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    # Table messages contact
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS contact_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            message TEXT NOT NULL,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_read INTEGER DEFAULT 0
        )
    """)
    
    conn.commit()
    conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# FONCTIONS UTILISATEURS
# ═══════════════════════════════════════════════════════════════════════════════

def hash_password(password: str) -> str:
    """Hash un mot de passe avec bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(password: str, password_hash: str) -> bool:
    """Vérifie un mot de passe"""
    return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))


def create_user(email: str, password: str, name: str, language: str = 'fr') -> Optional[int]:
    """Crée un nouvel utilisateur"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        password_hash = hash_password(password)
        cursor.execute("""
            INSERT INTO users (email, password_hash, name, language, is_verified)
            VALUES (?, ?, ?, ?, 1)
        """, (email.lower(), password_hash, name, language))
        conn.commit()
        user_id = cursor.lastrowid
        return user_id
    except sqlite3.IntegrityError:
        return None  # Email déjà existant
    finally:
        conn.close()


def create_user_google(email: str, name: str, google_id: str, language: str = 'fr') -> Optional[int]:
    """Crée un utilisateur via Google OAuth"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO users (email, name, google_id, language, is_verified)
            VALUES (?, ?, ?, ?, 1)
        """, (email.lower(), name, google_id, language))
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        # L'utilisateur existe déjà, mettre à jour le google_id
        cursor.execute("""
            UPDATE users SET google_id = ?, name = ? WHERE email = ?
        """, (google_id, name, email.lower()))
        conn.commit()
        user = get_user_by_email(email)
        return user['id'] if user else None
    finally:
        conn.close()


def get_user_by_email(email: str) -> Optional[Dict]:
    """Récupère un utilisateur par email"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM users WHERE email = ?", (email.lower(),))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return dict(row)
    return None


def get_user_by_id(user_id: int) -> Optional[Dict]:
    """Récupère un utilisateur par ID"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return dict(row)
    return None


def authenticate_user(email: str, password: str) -> Optional[Dict]:
    """Authentifie un utilisateur"""
    user = get_user_by_email(email)
    
    if user and user['password_hash'] and verify_password(password, user['password_hash']):
        # Mettre à jour last_login
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET last_login = ? WHERE id = ?", 
                      (datetime.now(), user['id']))
        conn.commit()
        conn.close()
        return user
    
    return None


def update_user_password(user_id: int, new_password: str) -> bool:
    """Met à jour le mot de passe d'un utilisateur"""
    conn = get_connection()
    cursor = conn.cursor()
    
    password_hash = hash_password(new_password)
    cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?",
                  (password_hash, user_id))
    conn.commit()
    success = cursor.rowcount > 0
    conn.close()
    
    return success


def update_user_language(user_id: int, language: str) -> bool:
    """Met à jour la langue d'un utilisateur"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("UPDATE users SET language = ? WHERE id = ?", (language, user_id))
    conn.commit()
    success = cursor.rowcount > 0
    conn.close()
    
    return success


# ═══════════════════════════════════════════════════════════════════════════════
# FONCTIONS RESET PASSWORD
# ═══════════════════════════════════════════════════════════════════════════════

def create_password_reset_token(user_id: int) -> str:
    """Crée un token de reset password"""
    conn = get_connection()
    cursor = conn.cursor()
    
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now() + timedelta(hours=1)
    
    cursor.execute("""
        INSERT INTO password_resets (user_id, token, expires_at)
        VALUES (?, ?, ?)
    """, (user_id, token, expires_at))
    conn.commit()
    conn.close()
    
    return token


def verify_reset_token(token: str) -> Optional[int]:
    """Vérifie un token de reset et retourne l'user_id si valide"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT user_id FROM password_resets 
        WHERE token = ? AND used = 0 AND expires_at > ?
    """, (token, datetime.now()))
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return row['user_id']
    return None


def mark_reset_token_used(token: str):
    """Marque un token comme utilisé"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("UPDATE password_resets SET used = 1 WHERE token = ?", (token,))
    conn.commit()
    conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# FONCTIONS NEWSLETTER
# ═══════════════════════════════════════════════════════════════════════════════

def subscribe_newsletter(email: str, language: str = 'fr') -> bool:
    """Inscrit un email à la newsletter"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO newsletter (email, language)
            VALUES (?, ?)
        """, (email.lower(), language))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False  # Déjà inscrit
    finally:
        conn.close()


def unsubscribe_newsletter(email: str) -> bool:
    """Désinscrit un email de la newsletter"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("UPDATE newsletter SET is_active = 0 WHERE email = ?", (email.lower(),))
    conn.commit()
    success = cursor.rowcount > 0
    conn.close()
    
    return success


def get_newsletter_subscribers() -> List[Dict]:
    """Récupère tous les abonnés actifs"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM newsletter WHERE is_active = 1")
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


# ═══════════════════════════════════════════════════════════════════════════════
# FONCTIONS CONTACT
# ═══════════════════════════════════════════════════════════════════════════════

def save_contact_message(name: str, email: str, message: str) -> bool:
    """Enregistre un message de contact"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO contact_messages (name, email, message)
        VALUES (?, ?, ?)
    """, (name, email.lower(), message))
    conn.commit()
    conn.close()
    
    return True


def get_contact_messages(unread_only: bool = False) -> List[Dict]:
    """Récupère les messages de contact"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if unread_only:
        cursor.execute("SELECT * FROM contact_messages WHERE is_read = 0 ORDER BY sent_at DESC")
    else:
        cursor.execute("SELECT * FROM contact_messages ORDER BY sent_at DESC")
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


# Initialiser la base de données au chargement du module
init_database()



