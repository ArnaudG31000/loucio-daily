#!/usr/bin/env python3
"""Sentinelle du pipeline Loucio. Échoue (exit 1) si :
- le contenu de DEMAIN manque (gospel ou evening) → rien ne sera publié demain ;
- la journée d'HIER n'a AUCUNE publication dans state.json (journée blanche).
L'échec fait échouer le workflow GitHub, qui envoie un e-mail au propriétaire :
c'est l'alarme indépendante du pipeline, elle ne dépend d'aucune session Claude."""
import json, os, sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

today = datetime.now(ZoneInfo("Europe/Paris")).date()
problemes = []

demain = (today + timedelta(days=1)).isoformat()
for kind in ("gospel", "evening"):
    p = f"content/{kind}/{demain}.json"
    if not os.path.exists(p):
        problemes.append(f"STOCK VIDE : {p} manque, rien ne sera publié demain !")
    else:
        try:
            json.load(open(p))
        except Exception as e:
            problemes.append(f"JSON INVALIDE : {p} ({e})")

hier = (today - timedelta(days=1)).isoformat()
state = json.load(open("state.json")) if os.path.exists("state.json") else {}
if not state.get(hier):
    problemes.append(f"JOURNÉE BLANCHE : aucune publication le {hier} (voir l'onglet Actions).")

apres = (today + timedelta(days=2)).isoformat()
for kind in ("gospel", "evening"):
    if not os.path.exists(f"content/{kind}/{apres}.json"):
        print(f"avertissement : content/{kind}/{apres}.json pas encore créé (la session de 18h06 doit le faire)")

if problemes:
    for p in problemes:
        print(f"::error::{p}")
    sys.exit(1)
print(f"sentinelle OK : demain ({demain}) couvert, hier ({hier}) publié")
