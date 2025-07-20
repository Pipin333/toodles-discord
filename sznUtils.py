import json
from cryptography.fernet import Fernet
from database import Session, AppConfig
import os

FERNET_KEY = os.getenv("FERNET_KEY")
fernet = Fernet(FERNET_KEY) if FERNET_KEY else None

def save_config(key: str, value: str):
    if fernet:
        value = fernet.encrypt(value.encode()).decode()
    with Session.begin() as session:
        existing = session.query(AppConfig).filter_by(key=key).first()
        if existing:
            existing.value = value
        else:
            session.add(AppConfig(key=key, value=value))

def load_config(key: str) -> str | None:
    with Session.begin() as session:
        entry = session.query(AppConfig).filter_by(key=key).first()
        if entry:
            if fernet:
                try:
                    return fernet.decrypt(entry.value.encode()).decode()
                except Exception as e:
                    print(f"❌ Error al desencriptar valor de {key}: {e}")
                    return None
            return entry.value
    return None


def is_json_cookies(content: str) -> bool:
    """Detecta si el contenido tiene un array JSON de cookies, incluso con encabezado 'cookies ='"""
    cleaned = content.strip()

    # Elimina encabezado tipo 'cookies ='
    if cleaned.lower().startswith("cookies ="):
        cleaned = cleaned[len("cookies ="):].strip()

    # Heurística simple: empieza con [ y contiene "name"
    return cleaned.startswith("[") and '"name"' in cleaned
    
def json_to_netscape(cookies_json: str) -> str:
    """Convierte JSON de cookies a formato Netscape"""
    try:
        parsed = json.loads(cookies_json)
        if not isinstance(parsed, list) or not all("name" in c for c in parsed):
            raise ValueError("JSON no válido para cookies.")

        lines = ["# Netscape HTTP Cookie File"]
        for cookie in parsed:
            domain = cookie.get("domain", ".youtube.com")
            flag = "TRUE" if domain.startswith(".") else "FALSE"
            path = cookie.get("path", "/")
            secure = "TRUE" if cookie.get("secure", False) else "FALSE"
            expires = str(cookie.get("expirationDate", 2145916800))
            name = cookie["name"]
            value = cookie["value"]
            lines.append(f"{domain}\t{flag}\t{path}\t{secure}\t{expires}\t{name}\t{value}")
        return "\n".join(lines)
    except Exception as e:
        raise ValueError(f"Error al convertir cookies JSON a Netscape: {e}")

def check_cookies_format(text: str) -> str:
    """Valida si el texto tiene formato Netscape"""
    lines = text.strip().splitlines()
    if not lines:
        return "❌ Archivo vacío."
    if not lines[0].startswith("# Netscape HTTP Cookie File"):
        return "❌ Falta encabezado '# Netscape HTTP Cookie File'."
    if len(lines) < 2:
        return "❌ Archivo con muy pocas líneas (debe haber cookies reales)."
    if any(line.strip().startswith("{") or "[" in line for line in lines):
        return "❌ Aún contiene JSON, no está convertido."
    return "✅ Formato Netscape válido."