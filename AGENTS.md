# Instructions de travail

## Périmètre et point d'arrêt

- Projet actif : BC1 RNCP40875, fraude et réseaux financiers.
- État : plan validé explicitement par l’utilisateur le 17 novembre 2026 (« oui »). Développement BC1 autorisé ; procéder progressivement avec vérifications et suivi.
- BC2 et BC3 restent indépendants et nécessitent chacun une autorisation explicite avant tout travail.
- Demander l'accord avant destruction, publication publique, dépense ou modification sensible. Garder les secrets hors du dépôt.
- Livraison locale uniquement : instruction explicite de Thomas, aucun commit, push ou email. Conserver les commits préexistants ; archiver les fichiers de travail courants sans modifier l'index Git.

## Reprise du travail

1. Lire `../preparation-oral/bc1/checklist.md` (hors dépôt) pour connaître l'état réel et les blocages ; l'historique détaillé (progression, tests, plan, audit, sources) est archivé dans `../preparation-oral/bc1/docs/`.
2. Avant une décision de périmètre, consulter `docs/rapport.md` (exigences et correspondance RNCP), l'audit archivé et les PDF de `../.data/`. Distinguer sujet pédagogique, référentiel et recommandation.
3. Après validation, sélectionner la prochaine tâche de `../preparation-oral/bc1/checklist.md` (section technique), vérifier ses dépendances, implémenter puis exécuter ses critères d'acceptation.
4. À chaque tâche, consigner résultats et preuves dans `docs/evidence/`, mettre à jour `../preparation-oral/bc1/checklist.md` et, si un résultat change, `docs/rapport.md` (dont la correspondance RNCP) avec des preuves réellement produites.

## Règles de réalisation

- Documentation en français ; conventions de nommage propres au langage ; modules simples, types et erreurs explicites, logs structurés sans secrets.
- Vérifier la compatibilité des versions et connecteurs avant verrouillage. Épingler dépendances et images reproductibles ; documenter les vulnérabilités et arbitrages.
- Identifier les données synthétiques, jeux de test et horodatages reconstruits. Ne pas assimiler PaySim à des transactions réelles.
- Préserver la cible `isFraud` pour l'évaluation ; éviter toute fuite de cible ou d'information future dans les variables explicatives.
- Une reprise après arrêt n'est pas une preuve de haute disponibilité. Un déploiement sur un hôte unique ne protège pas contre sa perte.
- Générer des brouillons d'emails ; l'envoi à des tiers nécessite une instruction explicite.
- Statuts autorisés : Terminé et vérifié ; Implémenté mais non vérifié ; En cours ; Bloqué ; À réaliser.
- Aucun test, résultat de modèle, capture ou validation RNCP ne peut être déclaré sans preuve. La validation officielle appartient au jury.
