# Loucio — publication quotidienne

Pipeline automatique : évangile du jour à 6h30 (thème Aube), récit ou réponse à 21h (Nuit/Sauge).
Contenu dans `content/`, images générées dans `out/`, état dans `state.json`.
Déclenchement manuel : modifier `trigger/slot.txt` (matin | soir | auto) et pousser.

Le token Instagram est rafraîchi chaque lundi par refresh-token-instagram :
le nouveau token est chiffré avec le secret IG_TOKEN (qui sert d'amorce et
de clé, ne pas le modifier) et committé dans .automation/ig_token.enc,
déchiffré par publish.py à l'exécution.
