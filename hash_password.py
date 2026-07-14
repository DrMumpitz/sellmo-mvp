#!/usr/bin/env python3
"""
Sellmo · Passwort-Hash-Generator
================================
Helper-Skript zum Erzeugen von bcrypt-Hashes für neue User.

Verwendung:
  python3 hash_password.py
  > Gibt ein zufaelliges Passwort (12 Zeichen) plus dessen bcrypt-Hash aus
  > Du kopierst den Hash in users.yaml und schickst dem Closer das Klartext-Passwort

Oder mit eigenem Passwort:
  python3 hash_password.py "MeinPasswort123!"

Sicherheit:
  - Klartext-Passwort wird NIRGENDS gespeichert (nur in die Konsole gedruckt)
  - bcrypt-Hash ist Einweg-Funktion
  - jedes Passwort hat eigenen Salt
"""

import sys
import secrets
import string
import bcrypt


def generate_random_password(length: int = 12) -> str:
    """Erzeugt ein zufaelliges Passwort mit Buchstaben + Ziffern + Sonderzeichen."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*-_=+"
    # Mindestens 1 von jeder Kategorie
    while True:
        pw = "".join(secrets.choice(alphabet) for _ in range(length))
        if (any(c.islower() for c in pw)
                and any(c.isupper() for c in pw)
                and any(c.isdigit() for c in pw)
                and any(c in "!@#$%^&*-_=+" for c in pw)):
            return pw


def hash_password(plain: str) -> str:
    """Erzeugt bcrypt-Hash mit Default-Cost (12)."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(plain.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def main():
    if len(sys.argv) > 1:
        plain = sys.argv[1]
        print(f"\n📌  Eigenes Passwort gehashed:")
    else:
        plain = generate_random_password()
        print(f"\n🎲  Zufaelliges Passwort generiert:")

    hashed = hash_password(plain)

    print(f"\n  Klartext: {plain}")
    print(f"  bcrypt:   {hashed}")
    print()
    print("📋  Naechste Schritte:")
    print("   1. Kopiere den bcrypt-Hash in users.yaml unter dem User-Eintrag")
    print("   2. Schicke das Klartext-Passwort dem Closer (persoenlich/WhatsApp/Mail)")
    print("   3. Klartext NIRGENDS speichern (kein Screenshot, kein Notion)")
    print()


if __name__ == "__main__":
    main()
