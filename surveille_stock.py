#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SURVEILLANCE DE STOCK - Midea PortaSplit
==========================================
Ce script vérifie régulièrement 3 sites (Amazon, Castorama, Leroy Merlin)
et t'envoie un message Telegram dès qu'un produit redevient disponible.

TU N'AS QUE 2 LIGNES A REMPLIR (voir plus bas, section "A REMPLIR") :
  1. TELEGRAM_BOT_TOKEN
  2. TELEGRAM_CHAT_ID

Le reste, tu n'as rien à comprendre ni à toucher.
"""

import os
import time
import random
import json
import requests

# ============================================================
# Le token et le chat_id sont lus depuis les "secrets" GitHub
# (jamais écrits en clair ici, puisque le dépôt est public)
# ============================================================
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
# ============================================================


# Produits à surveiller : nom + URL
PRODUITS = [
    {
        "nom": "Amazon",
        "url": "https://amzn.eu/d/0iwogRAl",
    },
    {
        "nom": "Castorama",
        "url": "https://www.castorama.fr/climatiseur-portasplit-midea-reversible-3500w/8431312260509_CAFR.prd",
    },
    {
        "nom": "Leroy Merlin",
        "url": "https://www.leroymerlin.fr/produits/climatiseur-split-mobile-reversible-portasplit-midea-par-optimea-93857579.html",
    },
]

# Fichier qui garde en mémoire le dernier statut connu de chaque site,
# pour ne pas renvoyer une notif à chaque run si rien n'a changé.
FICHIER_ETAT = "etat.json"

# Mots qui indiquent que le produit N'EST PAS disponible.
# Si la page contient un de ces mots, on considère que c'est en rupture.
MOTS_INDISPONIBLE = [
    "actuellement indisponible",
    "rupture de stock",
    "en rupture",
    "produit indisponible",
    "n'est plus disponible",
    "épuisé",
    "temporairement indisponible",
    "hors stock",
]

# Différents "User-Agent" pour faire croire qu'on est un navigateur classique
# (le script en choisit un au hasard à chaque vérification)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
]


def envoyer_telegram(message):
    """Envoie un message sur Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": message}, timeout=10)
    except Exception as e:
        print(f"[Erreur envoi Telegram] {e}")


def charger_etat():
    """Charge l'état précédent (quel site était dispo la dernière fois)."""
    if os.path.exists(FICHIER_ETAT):
        try:
            with open(FICHIER_ETAT, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"[Erreur lecture état] {e}")
    return {}


def sauver_etat(etat):
    """Sauvegarde l'état pour le prochain run."""
    try:
        with open(FICHIER_ETAT, "w") as f:
            json.dump(etat, f)
    except Exception as e:
        print(f"[Erreur écriture état] {e}")


def produit_disponible(html):
    """
    Regarde le texte de la page.
    Renvoie True si le produit semble disponible, False sinon.
    """
    texte = html.lower()
    for mot in MOTS_INDISPONIBLE:
        if mot in texte:
            return False
    return True


def verifier_page(url):
    """Télécharge une page et vérifie si le produit est disponible."""
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "fr-FR,fr;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    reponse = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
    reponse.raise_for_status()
    return produit_disponible(reponse.text)


def verification_unique():
    """
    Fait UNE seule vérification de chaque site, puis s'arrête.
    (GitHub Actions relance ce script automatiquement toutes les 5 minutes,
    donc pas besoin de boucle infinie ici.)

    Ne notifie sur Telegram que si le statut vient de PASSER
    de "indisponible" à "disponible" (pas à chaque run).
    """
    etat = charger_etat()

    for produit in PRODUITS:
        nom = produit["nom"]
        url = produit["url"]
        try:
            disponible = verifier_page(url)
        except Exception as e:
            print(f"[{nom}] Erreur de vérification : {e}")
            continue

        print(f"[{nom}] Disponible ? {disponible}")

        etait_disponible = etat.get(nom, False)

        # On ne notifie que lors du changement rupture -> disponible
        if disponible and not etait_disponible:
            envoyer_telegram(f"🟢 DISPONIBLE chez {nom} !\n{url}")

        etat[nom] = disponible

        # Petite pause entre chaque site pour ne pas envoyer les requêtes
        # toutes en même temps (ça fait plus naturel)
        time.sleep(random.uniform(3, 8))

    sauver_etat(etat)


if __name__ == "__main__":
    verification_unique()
