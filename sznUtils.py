import json

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