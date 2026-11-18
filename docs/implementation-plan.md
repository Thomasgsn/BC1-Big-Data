# Plan progressif BC1 validé

**Plan validé explicitement par l’utilisateur le 17 novembre 2026 (« oui »). Développement en cours ; état réel dans [progress.md](progress.md).** Les tâches seront validées sur leurs preuves réelles. BC2 et BC3 sont exclus. Le projet et ses futures commandes s'exécutent depuis `bc1/`.

Les tâches sont ordonnées par dépendance. Chaque tâche produit ses tests, sa documentation et une mise à jour de progression/matrice. Les seuils proposés ci-dessous sont des objectifs de projet ajustables après mesure, pas des seuils RNCP.

## P0 — Cadrage

Livrable : audit, sources, architecture, matrice C1.1–C2.4, risques et plan. Critère : cinq PDF disponibles et lus, chaque compétence reliée à une réalisation et une preuve, limites identifiées ; validation utilisateur enregistrée séparément de la rédaction. Le contrôle documentaire peut être terminé sans que le plan soit approuvé.

## P1 — Faisabilité et socle reproductible

| Tâche | Dépendance | Réalisation après accord | Critères d'acceptation objectifs |
|---|---|---|---|
| 1.1 Environnement | Validation P0 | Vérifier moteur Docker, mémoire allouable, disques, accès registre et Gephi | `docker info` et conteneur minimal aboutissent ; RAM/disque relevés ; procédure Gephi testée ; aucun service payant engagé |
| 1.2 Acquisition PaySim | 1.1 pour les outils nécessaires | Acquérir dataset depuis source auteur, relever licence/version/SHA-256 | Fichier lisible ; licence et attribution enregistrées ; schéma, nombre de lignes, types, manquants, taux de cible et bornes temporelles calculés ; aucun chiffre supposé présenté comme mesuré |
| 1.3 Compatibilité | 1.1 | Tester versions Kafka/ZK, Spark/Python/Java/Scala, HDFS, Mongo/JDBC | Un job minimal lit Kafka, écrit/lit Parquet HDFS et joint SQL ; versions/digests et connecteurs verrouillés ; vulnérabilités et licences examinées |
| 1.4 Organisation autonome | 1.2–1.3 | Initialiser le dépôt local BC1, structure, environnement et outillage qualité | Commandes documentées depuis `bc1/` ; aucun import d'un autre bloc ; dépendances verrouillées ; secrets ignorés ; initialisation Git locale seulement, aucun push |

**Jalon :** si PaySim est inaccessible, conserver le blocage et proposer le générateur explicitement synthétique autorisé par SUJET. Si versions compatibles/sûres manquantes avec ZooKeeper, faire arbitrer le remplacement pédagogique. Clarifier binôme, échéance, seconde source, interprétation temps réel et moyens HA avant les jalons concernés.

## P2 — Infrastructure et contrats de données

| Tâche | Dépendance | Réalisation | Critères d'acceptation objectifs |
|---|---|---|---|
| 2.1 Compose minimal | P1 | ZK, Kafka, NameNode/DataNode, Spark master/worker | Configuration Compose valide ; healthchecks sains ; un message Kafka et un fichier HDFS survivent à l'arrêt/redémarrage sans suppression de volume |
| 2.2 Stockages métier | 2.1 | MongoDB, PostgreSQL, migrations et comptes techniques | PK/FK/contraintes et index présents ; connexions autorisées réussies et accès invalide refusé ; sauvegarde/restauration d'un petit jeu de test étiqueté |
| 2.3 Contrat transaction | 1.2, 2.1 | Enveloppe versionnée, mapping PaySim, identifiant stable, dates et montants | Tests valides/invalides, décimaux, champs absents, cible isolée ; deux lectures du même fichier génèrent les mêmes identifiants |
| 2.4 Producteur | 2.3 | Rejeu à débit configurable avec journal de progression | N lignes émises correspondent à N identifiants attendus ; débit observé enregistré ; erreur broker et arrêt propre testés |

## P3 — Streaming et lac de données

| Tâche | Dépendance | Réalisation | Critères d'acceptation objectifs |
|---|---|---|---|
| 3.1 Ingestion brute | P2 | Kafka → Spark → HDFS raw et checkpoints | Événements sources retrouvés avec provenance ; reprise après arrêt testée ; pertes et doublons comptés, aucune garantie non démontrée |
| 3.2 Curated et quarantaine | 3.1 | Nettoyage, typage, contrôle qualité et Parquet | Entrées = valides + rejets selon règles explicites ; doublons rapprochés séparément ; schéma relu identique ; motifs de rejet testés |
| 3.3 Agrégations stream | 3.2 | Volume/minute de rejeu, sommes/type et agrégats temps simulé | Résultat égal à une référence sur jeu borné ; retards/doublons testés ; horloges et fermeture des fenêtres documentées |
| 3.4 Reprise et cohérence | 3.1–3.3 | Arrêts à différents moments, idempotence et relecture | Sur entrée fixe, ensemble des identifiants finaux et sommes identiques après reprise ; comportement checkpoint absent/corrompu explicité |

## P4 — Data Lab, API et seconde source

| Tâche | Dépendance | Réalisation | Critères d'acceptation objectifs |
|---|---|---|---|
| 4.1 Agrégats et graphe Mongo | P3 | HDFS → collections, nœuds/arêtes orientées | Identifiants uniques, aucun endpoint d'arête absent ; sommes rapprochées ; relance sans duplication ; index exercés |
| 4.2 API lecture | 4.1, 2.2 | OpenAPI, authentification, rôles, filtres, pagination et quotas | Tests 200/401/403/404/422/429/503 ; taille maximale respectée ; jeton révoqué refusé ; aucun secret dans logs |
| 4.3 Dossiers et décisions | 4.2 | Écriture SQL transactionnelle, idempotence, audit | Décision analyste persistée ; écriture lecteur refusée ; répétition idempotente ; référence inconnue refusée ; rollback testé |
| 4.4 Source SQL vers HDFS | 4.3 | Snapshot JDBC complet, immuable et borné, puis jointure des revues | Revues effectivement saisies présentes une seule fois au niveau logique ; snapshots distincts sans écrasement, décisions immuables et comptages relus ; provenance et jointure transaction démontrées |

**Jalon :** faire confirmer l'adéquation de la variété de sources au référentiel. Aucune ligne de la matrice multi-source ne sera déclarée couverte par le seul rejeu CSV → JSON.

## P5 — Analyse Gephi

| Tâche | Dépendance | Réalisation | Critères d'acceptation objectifs |
|---|---|---|---|
| 5.1 Export | 4.1 | Export de Mongo, CSV nœuds/arêtes ou GEXF, filtrage borné | Fichiers importables dans Gephi ; comptages cohérents ; fenêtre, critères, limites et checksum export enregistrés |
| 5.2 Analyse réseau | 5.1 | Degré, modularité, interprétation et captures | Algorithmes exécutés ; paramètres/seed et taille du graphe conservés ; captures réelles ; hubs discutés sans affirmer une fraude non démontrée |

## P6 — Modélisation et scoring MLlib

| Tâche | Dépendance | Réalisation | Critères d'acceptation objectifs |
|---|---|---|---|
| 6.1 Features et partitions | P3, profilage PaySim | Découpage temporel train/validation/test, variables historiques | Périodes disjointes ; prétraitement appris sur train seul ; aucun label ou futur dans features ; classes et données manquantes décrites |
| 6.2 Deux modèles | 6.1 | Régression logistique et Random Forest MLlib | Pipelines entraînés, sauvegardés et rechargés ; seed et paramètres tracés ; baseline simple calculée ; test d'inférence sur features limites |
| 6.3 Évaluation | 6.2 | Seuil sur validation, évaluation finale réservée | AUC-ROC, rappel et matrice calculés avec seuil/effectifs ; PR-AUC, précision et faux positifs ajoutés ; absence de classe positive traitée explicitement ; durée et ressources mesurées |
| 6.4 Scoring incrémental | 6.3, 4.1 | Modèle retenu → nouvelles données HDFS → scores Mongo | Une transaction franchissant le seuil crée une alerte versionnée ; parité features entraînement/inférence testée ; rejeu sans double alerte logique |

Le rappel cible et le coût des faux positifs seront discutés après profilage ; aucun résultat minimum arbitraire ne conditionne artificiellement la certification. Si aucune alerte n'apparaît dans l'échantillon, augmenter le périmètre ou utiliser un cas de test étiqueté, sans modifier le test final pour embellir les scores.

## P7 — Génération explicative

| Tâche | Dépendance | Réalisation | Critères d'acceptation objectifs |
|---|---|---|---|
| 7.1 LLM réel | P1, 6.4 | Choisir un modèle local disponible, budget mémoire et licence | Appel réel réussit, nom/version/paramètres enregistrés, temps et mémoire mesurés ; si API payante nécessaire, accord préalable |
| 7.2 Explication et brouillon | 7.1, 4.2 | Endpoint de génération, motifs calculés et contexte borné | Sur alerte modèle persistée : explication conseiller et brouillon client effectivement générés, sauvegardés ; score/seuil/version conformes ; aucune donnée de contact inventée |
| 7.3 Qualité et erreurs | 7.2 | Grille factuelle, compréhension et sécurité | Cas vrai/faux positif et erreur LLM testés ; texte sans accusation certaine, demande de secret ou URL dangereuse ; panne/timeout signalés ; aucun email envoyé |

Un gabarit déterministe peut servir de comparaison mais ne remplace pas une preuve d'appel LLM. Une sortie simulée ne sera jamais étiquetée comme génération réelle.

## P8 — Sécurité, performance et résilience approfondies

La sécurité de base et les tests d'erreur sont intégrés aux phases précédentes ; ce jalon ajoute les preuves transversales.

| Tâche | Dépendance | Réalisation | Critères d'acceptation objectifs |
|---|---|---|---|
| 8.1 Sécurisation du lac et flux | P3–P7 | Authentification forte HDFS, permissions, TLS, ACL Kafka et contrôle des accès | Identité non autorisée refusée ; accès attendu autorisé ; transport vérifié ; secrets absents des fichiers/logs versionnés ; limites documentées |
| 8.2 Charge et optimisation | P4, P6 | Charge SQL/API/stream, index, partitionnement et compaction | Au moins une comparaison contrôlée avant/après ; débits, p50/p95, erreurs, ressources et intégrité publiés ; aucune amélioration affirmée si non observée |
| 8.3 Scalabilité | 8.2 | Ajouter worker/partitions/DataNode selon protocole | Deux configurations comparées sur même entrée ; impact et limites mesurés ; absence de gain admise et expliquée |
| 8.4 Réplication/bascule | P2–P4, moyens HA identifiés | Profil répliqué Kafka/HDFS et continuité des services critiques | Pannes injectées avec chronologie ; écritures/lectures suivies, RPO/RTO observés et rapprochements sans perte inexpliquée ; portée exacte des preuves publiée |
| 8.5 Restauration | 8.1, 8.4 | Restaurer sauvegardes et manifestes sur volumes isolés | Données SQL/Mongo/HDFS nécessaires récupérées et cohérentes ; preuve d'isolation des essais ; aucune suppression de volumes existants sans accord |

**Jalon C1.4 :** si le matériel ne permet pas les essais requis, marquer le travail Bloqué pour cette réalisation, préciser ce qui manque et faire arbitrer une ressource externe ou l'écart pédagogique. Un profil mono-hôte n'est jamais présenté comme HA physique. Aucun environnement payant n'est créé implicitement.

## P9 — Livraison et soutenance

| Tâche | Dépendance | Réalisation | Critères d'acceptation objectifs |
|---|---|---|---|
| 9.1 Reproduction | P1–P8 | Installation depuis environnement propre, guide installation/déploiement | Une procédure rejoue le chemin dataset → alerte → génération ; versions et fichiers nécessaires listés ; écarts enregistrés |
| 9.2 Rapport et preuves | 9.1 | Rapport technique, expériences, captures, matrice à jour | Chaque obligation relie une preuve réelle ; tous les écarts ouverts explicités ; contributions du binôme identifiées |
| 9.3 Démonstration et jury | 9.2 | Scénario, support, répétition et vidéo ou présentation | Démonstration bout en bout répétée, durée mesurée, questions techniques préparées ; anglais technique couvert selon modalités confirmées |
| 9.4 GitHub | 9.2 | Vérifier droits/secrets puis préparer publication | Résultat local prêt à relire ; accord explicite avant publication ; accès du jury vérifié après publication autorisée |

## Charge indicative et validation

Ordre de grandeur d'ingénierie à réestimer après P1 : P1–P2 4–6 jours, P3–P4 5–8 jours, P5–P7 5–8 jours, P8 4–8 jours, P9 3–5 jours, soit environ 21–35 jours de travail effectif hors délais d'accès, matériel et retours de l'école. Ce n'est ni une durée imposée ni un calendrier validé ; disponibilités et expérience du binôme inconnues.

Décisions proposées : projet autonome `bc1/`, MongoDB plutôt que Cassandra, PostgreSQL et FastAPI en complément, PaySim prioritaire, GenAI locale si faisable, progression par profils et preuves de résilience explicites. Après accord utilisateur, les prochaines tâches sont suivies dans `progress.md`. Aucune approbation n'est déduite de l'écoulement du temps ou de l'absence de réponse.
