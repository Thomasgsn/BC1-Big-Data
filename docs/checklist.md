# Checklist BC1

Statuts : **À faire**, **En cours**, **Fait** (coché seulement avec une preuve). Ordre = priorité.

## 1. À faire personnellement (Thomas)

| # | Action | Pourquoi | Comment | Preuve à garder | Statut |
|---|---|---|---|---|---|
| 1 | Faire accepter le travail individuel | Le sujet prévoit un binôme | Écrire à l’enseignant du module (adresse dans le sujet), demander l’accord pour un rendu seul | Réponse écrite de l’enseignant | À faire |
| 2 | Publier le dépôt GitHub | Livrable exigé par le sujet | Vérifier `git status`, que `.env`, `data/`, `secrets` et poids ne sont pas suivis, commiter, pousser, ouvrir le README en ligne | URL du dépôt et SHA du commit remis | À faire |
| 3 | Relire rapport, support et déclaration d’usage de l’IA | Le contenu est assisté par IA ; vous devez pouvoir tout défendre | Lire `docs/rapport.md`, les deux PDF ; vérifier le règlement de l’école sur l’IA | Version relue, éventuelles corrections | À faire |
| 4 | Préparer la démonstration du flux complet | Le sujet demande une vidéo ou une présentation de Kafka jusqu’à la réponse de l’IA | Répéter le parcours du README ; enregistrer une vidéo si l’école la préfère au support | Vidéo ou support final | À faire |
| 5 | Répéter l’oral, y compris en anglais | Modalités du référentiel | Utiliser le support et les documents de préparation orale | Notes de répétition | À faire |
| 6 | Remettre le rendu | Évaluation | Déposer rapport, lien GitHub et support sur la plateforme de l’école, dans les délais | Accusé de dépôt | À faire |

## 2. À autoriser ou fournir pour qu’un agent continue

| # | Action | Pourquoi | Comment | Statut |
|---|---|---|---|---|
| 7 | Autoriser le commit et le push par l’agent, ou les faire vous-même | Les consignes actuelles interdisent commit et push | Dire explicitement « commit et push autorisés » et donner l’URL du dépôt distant | À faire |
| 8 | Décider du sort de la vulnérabilité critique libxml2 (PostgreSQL) | Une acceptation de risque est une décision humaine | Lire `docs/evidence/p10/maintenance-triage.json` ; accepter, ou demander un changement d’image | À faire |

## 3. Reste technique (automatisable)

| # | Action | Pourquoi | Statut |
|---|---|---|---|
| 9 | Brancher le modèle à historique destinataire au scoring en flux | Meilleur modèle, mais non utilisé en production de démonstration | À faire |
| 10 | Élargir la grille de seuils au-delà de 0,9 et augmenter les fraudes de validation | Seuil retenu en bord de grille, 45 fraudes en validation | À faire |
| 11 | Tester sécurité et haute disponibilité ensemble | Aujourd’hui testées dans des profils séparés | À faire |

## 4. Améliorations facultatives

- Passer Kafka en mode KRaft (à faire accepter, le sujet demande ZooKeeper).
- Compacter les petits fichiers Parquet.
- Sauvegarde hors de la machine.

## Déjà fait (preuves)

- [x] Flux Kafka → Spark → HDFS rapproché sur 1 000 transactions — `docs/evidence/p10/final-hdfs-verification.json`
- [x] Analyse Gephi avec captures réelles — `docs/evidence/p5/`
- [x] Deux modèles comparés, modèle enrichi — `docs/evidence/p6/`, `docs/evidence/p11/`
- [x] Explication et brouillon d’email générés — `docs/evidence/p10/final-draft.json`
- [x] Rapport PDF et support PDF générés — `output/pdf/`
