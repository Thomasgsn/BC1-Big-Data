# Progression réelle — BC1

Dernière mise à jour : 17 novembre 2026.

## Reprise autonome — 17 novembre 2026

L’utilisateur a demandé de poursuivre sans arrêt intermédiaire. Les appels directs à `docker compose` accèdent désormais au moteur ; les refus observés via les scripts et `docker info` sont historiques. Le téléchargement des images et le build sont en cours ; aucune réussite du cluster n'est encore annoncée.

Implémenté depuis P1 : contrats/identifiants et producteur, Compose avec Kafka/ZooKeeper/HDFS/Spark/Mongo/PostgreSQL, initialisation SQL/Mongo, jobs Spark d’ingestion/vérification/JDBC, publication de graphe, export Gephi et entraînement MLlib. Les jobs de service restent à vérifier en exécution.

Vérifié : **29 tests unitaires réussis** sous Python 3.13.18 ; 10 000 JSONL réels rapprochés du CSV (68 labels fraude dans ce préfixe, aucun modèle évalué) ; cas d’erreur broker inaccessible retournant code 1 ; Compose valide, ports loopback, images par digest et `.env` 0600 ignoré. Rapports dans `docs/evidence/p2/`. SHA/CRC de 3 JAR top-level relevés dans `infra/connectors.lock.json` ; signatures et transitifs non encore vérifiés.

API, seconde source métier, scoring, LLM, sécurité forte/HA et livrables finaux restent à réaliser. Aucun bloc BC2/BC3 commencé. Les préparations isolées graphe/ML ne valident pas les phases dépendant du cluster.

## État P1 précédent — historique

**Plan validé explicitement par l’utilisateur (« oui »). Développement BC1 autorisé ; P1 en cours.** BC2 et BC3 ne sont pas commencés. Toute dépense ou publication reste soumise à accord distinct.

| Tâche | Statut | Preuve / reste à faire |
|---|---|---|
| P0 Cadrage | Terminé et vérifié | PDF lus, matrice, architecture, plan ; validation reçue |
| P1.1 Environnement | Bloqué pour les essais Codex | Docker lancé, socket refusé ; hello-world réussi selon sortie utilisateur ; ressources VM et Gephi non vérifiés |
| P1.2 PaySim | Terminé et vérifié | Version 2 acquise, CC BY-SA 4.0 confirmée par métadonnées officielles, CRC/tailles et SHA-256, profil complet |
| Outils dataset | Terminé et vérifié | Extracteur/profileur exécutés sur véritable PaySim ; 8 tests unitaires réussis |
| P1.3 Compatibilité | Bloqué pour l’exécution | 5 images candidates épinglées ; intégration Kafka/Spark/HDFS/SQL non testée |
| P1.4 Socle | En cours | Git local main, package et tests ; dépendances plateforme non figées |
| Diagnostic Docker | Implémenté mais non vérifié pour les sondes réelles | Branche d’échec exécutée et rapport sauvegardé ; sondes images non exécutées |
| P2–P9 | À réaliser | Aucun Compose/service de plateforme, modèle, graphe ou génération LLM |

## Phase P1 : réalisations et résultats

- Docker Desktop lancé par `open -a Docker`. Codex reçoit ensuite `permission denied` sur son socket ; aucun contournement tenté.
- L’utilisateur a transmis un hello-world réussi, image amd64, digest `sha256:1e4c05b897a751332ce85c7e9449da2d93514ea2dea6dbb0e2753c9e949b2bfa`. Résultat utilisateur, pas exécution Codex ; ressources Docker non déduites de ce seul test.
- Métadonnées officielles Kaggle et licence sauvegardées. Premier téléchargement en échec DNS ; nouvelle tentative réussie sans compte ni secret. Archive v2 extraite avec contrôle du membre unique, CRC et taille ; CSV intact.
- Profilage intégral : **6 362 620 transactions, 8 213 fraudes (environ 0,1291 %), 11 colonnes, 0 ligne invalide selon les contrôles implémentés**. Steps 1–743 sans retour en arrière, 16 montants nuls. Détails et limites dans `docs/dataset.md` et `docs/evidence/p1/paysim-profile.json`.
- Architecture corrigée : les quatre soldes sont exclus des prédicteurs selon l’avertissement de l’auteur Kaggle ; les deux labels le restent également.
- `PYTHONPATH=src python3 -m unittest discover -s tests -v` : **8/8 réussis**, fixtures synthétiques identifiées. Formats, valeurs non finies/négatives, champs absents/supplémentaires, ordre des steps, extraction et protection des fichiers existants contrôlés.
- CLI `dataset extract` et `dataset profile` : code 0 sur le véritable dataset complet. Aucune expérience ML ni performance de modèle revendiquée.
- Git initialisé dans `bc1/` sur main ; `git check-ignore` confirme l’exclusion du CSV et de l’archive. Aucun staging, commit, remote ou push.
- Cinq digests candidats relevés via Docker Hub dans `infra/images.lock.json`. Métadonnées seulement ; vulnérabilités, démarrages et intégration restent à vérifier.
- `python3 scripts/check_environment.py --actor codex` : code 1, accès Docker refusé ; rapport `docs/evidence/p1/environment-codex.json`. Aucune sonde de conteneur exécutée.
- Contrôles finaux : compilation Python des deux outils sans erreur, liens locaux et empreintes des cinq PDF vérifiés ; sommes par type/step rapprochées avec le total et les fraudes du profil ; cinq digests valides avec plateforme amd64 ; aucun BC2/BC3 créé. `git diff --check` ne remonte rien mais ne contrôle pas les nouveaux fichiers encore non suivis.

Fichiers ajoutés : `pyproject.toml`, `Makefile`, `src/rncp_bc1/{__init__,dataset}.py`, `tests/test_dataset.py`, `scripts/check_environment.py`, `infra/images.lock.json`, `docs/{dataset,compatibility}.md`, trois JSON de preuve dans `docs/evidence/p1/`. Archive et CSV locaux dans `data/raw/`, ignorés par Git.

Fichiers mis à jour : README/AGENTS racine et BC1, `.env.example`, architecture, matrice, sources, plan, progression et testing. L’initialisation Git et les outils sans dépendance ont été avancés indépendamment des essais P1.3, car ils ne nécessitent pas Docker.

Compétences préparées : C1.3 (source), C2.3 (profilage/contrats), C2.2 (veille). Aucune compétence entière déclarée couverte ni acquise.

## Blocage et prochaine action

Exécuter `python3 scripts/check_environment.py --probe-images` depuis le terminal qui accède à Docker, puis examiner `docs/evidence/p1/environment-terminal.json`. Vérifier les ressources VM et les binaires, puis effectuer le job Kafka → Spark → HDFS avec jointure SQL avant figement de Compose. P1 ne sera pas déclaré terminé sur le seul hello-world.

Risques restants : maintenance Kafka 3.9.2/ZooKeeper, sécurité des images, moyens HA sur 16 Go, Gephi absent du chemin standard, seconde source/interprétation temps réel à confirmer pédagogiquement, binôme et échéance inconnus.

---

## Historique P0 — état avant validation

**Cadrage rédigé ; validation du plan attendue. Développement non commencé.** L'instruction finale de l'utilisateur impose un dossier et une documentation propres à chaque projet : tout le cadrage BC1 est placé dans `bc1/`. BC2 et BC3 n'ont ni dossier de projet créé ni travail commencé ; leurs sujets ont seulement été lus comme demandé.

| Élément | Statut | Preuve / limite |
|---|---|---|
| Audit initial | Terminé et vérifié | Inventaire, absence de Git/code, diagnostics environnement dans `testing.md` |
| Lecture des cinq PDF | Terminé et vérifié | Extraction complète, analyse REF p. 2–6 et SUJET p. 1–3, manifeste SHA-256 |
| Analyse C1.1 à C2.4 | Terminé et vérifié | Matrice par critère, différences sujet/référentiel explicites |
| Vérification disponibilité PaySim | Terminé et vérifié pour le repérage uniquement | Lien auteur/Kaggle identifié, absent localement ; acquisition non vérifiée |
| Dataset exploitable | À réaliser | Aucun CSV, licence/version/schéma local non contrôlés |
| Architecture et plan | Terminé et vérifié pour le cadrage documentaire | Proposition, risques, critères de tâches et limites rédigés ; aucune preuve applicative |
| Validation utilisateur | À réaliser | Aucun accord de développement reçu |
| Infrastructure et code | À réaliser | Aucun fichier Compose, Dockerfile, code applicatif ou test créé |
| Intégration et tests de plateforme | À réaliser | Moteur Docker actuellement indisponible ; aucun essai d'intégration |
| Preuve HA C1.4 | À réaliser | Moyens matériels et périmètre d'évaluation à résoudre avant P8 |
| Rapport final / captures / démo | À réaliser | Seul un guide de préparation au jury est rédigé |

## Phase de cadrage réalisée

- Réalisé : inventaire, lecture des cinq supports, analyse des huit compétences, repérage PaySim, diagnostic environnement, architecture et plan proposés, organisation autonome BC1, consignes de reprise.
- Fichiers ajoutés : `bc1/README.md`, `bc1/AGENTS.md`, `bc1/.env.example`, `bc1/.gitignore`, `bc1/docs/{audit,sources,architecture,rncp-matrix,implementation-plan,testing,jury-preparation,progress}.md`, `bc1/docs/source-manifest.json`. À la racine : `README.md`, `AGENTS.md`, `.gitignore` pour l'organisation commune uniquement.
- Réorganisation : les premiers documents créés à la racine ont été déplacés vers `bc1/` après précision de l'utilisateur. Liens et chemins adaptés. Aucun fichier utilisateur supprimé ni PDF modifié.
- Vérifications réalisées : inventaire et diagnostics décrits dans `testing.md`, relecture des critères et contrôle des liens/empreintes en fin de cadrage. Aucun test applicatif, mesure de modèle ou capture de fonctionnement revendiqué.
- Résultat du contrôle documentaire : code 0 ; 22 liens locaux valides, 5/5 PDF inchangés, 10/10 fichiers minimaux BC1 présents, 8/8 compétences dans la matrice, blocs Markdown clos ; aucun code/Compose ni dossier BC2/BC3. Diagramme Mermaid rédigé mais non rendu graphiquement.
- Compétences : C1.1–C2.4 **analysées et planifiées**, aucune déclarée acquise ou implémentée.
- Difficultés : moteur Docker indisponible, Java hôte absent, contraintes 16 Go RAM, PaySim non acquis et page Kaggle non lisible par l'outil web, accès sysctl partiellement refusé.
- Risques ouverts : sécurité/version des images ZooKeeper, seconde source et interprétation temps réel à confirmer, capacité HA, disponibilités du binôme et échéance inconnues.

## Action prévue à la fin de P0 — historique

Exécuter P1.1 du plan : vérifier moteur Docker et ressources allouables, puis acquisition/profilage PaySim et validation des versions. Ne pas démarrer ce travail avant accord explicite. Toute ressource payante ou publication publique nécessite un accord distinct.

## Statuts à utiliser lors des prochaines phases

- **Terminé et vérifié** : comportement contrôlé avec preuve consultable.
- **Implémenté mais non vérifié** : fichiers écrits sans vérification suffisante.
- **En cours** : travail actif non terminé.
- **Bloqué** : dépendance manquante empêchant la tâche ; préciser la condition de reprise.
- **À réaliser** : tâche non commencée.

Une phase technique devra préciser fichiers modifiés, commandes, résultats, compétences concernées, difficultés, tâches restantes et blocages. La réussite d'un lancement ou d'une compilation n'est pas une validation du bloc. Le jury reste seul habilité à la prononcer.


## État archivé avant clôture de la reproduction — 18 novembre 2026

# Progression réelle — BC1

Mise à jour : 18 novembre 2026. Plan validé (« oui »), poursuite autonome autorisée. BC2 et BC3 non commencés. Aucune publication, dépense ou transmission d'email.

## Reproduction isolée — opération active

Projet `rncp-bc1-repro-v1`, configurations `docker-compose.yml` + `infra/reproduction.yml`. Arrêt temporaire du projet principal pour limiter la mémoire, sans supprimer ses volumes. Démarrage sur nouveaux volumes métier, aucun port publié. Dataset et images déjà téléchargés réutilisés ; poids publics Ollama seuls partagés en lecture seule. À la fin ou après interruption : arrêter le projet de reproduction, puis redémarrer le principal avec `docker compose up -d --wait --wait-timeout 300` et `docker compose up -d ollama`. Ne supprimer aucun volume. État et preuves dans `docs/evidence/p9/reproduction.json`.

## État courant

| Phase | Statut | Réalisations vérifiées et limites |
|---|---|---|
| P0 Cadrage | Terminé et vérifié | Cinq PDF lus, exigences et écarts distingués ; plan validé |
| P1 Socle | En cours | PaySim complet profilé ; Python 3.13.18 local, Spark 3.5.8/Java 17/Python 3.10 en conteneur ; Git local ; examen de vulnérabilités et interface Gephi à compléter |
| P2 Plateforme/contrats | En cours | Cluster réellement démarré ; Kafka/ZooKeeper/HDFS/Spark/Mongo/PostgreSQL opérationnels ; contraintes SQL et contrat testés ; restaurations SQL/Mongo vérifiées dans des bases isolées ; snapshot HDFS restauré et relu |
| P3 Streaming/lac | En cours | Rejeu de 1 000 lignes rapproché du CSV, 0 rejet, IDs uniques, sommes et métriques exactes ; checkpoints réutilisés et données relues après redémarrage Kafka/HDFS ; mode permanent exécuté, puis 1 000 doublons et 3 événements invalides rapprochés après reprise |
| P4 API/multi-source | En cours | API réelle, rôles, quotas, concurrence/idempotence ; 6 tests HTTP réussis ; deux décisions AUTOMATISÉES extraites SQL→HDFS et jointes aux transactions ; révocation 200→401 et panne Mongo 503→200 vérifiées |
| P5 Gephi | En cours | Mongo→CSV réel : 1 597 nœuds/1 000 arêtes ; Gephi Toolkit exécuté, degrés rapprochés et modularité 0,995408 ; SVG/PNG inspectés ; captures réelles du client Linux conservées |
| P6 MLlib | En cours | Deux modèles réellement entraînés/évalués ; modèle sélectionné rechargé ; 1 000 scores publiés dont 305 alertes ; relance idempotente et cas limites à approfondir |
| P7 GenAI | En cours | Qwen 3B verrouillé ; sorties réelles conformes sur vrai/faux positif PaySim, labels hors prompt ; échecs et rejet de qualité conservés ; revue humaine avant usage requise |
| P8 Sécurité/charge/résilience | En cours | Comptes SQL/Mongo séparés, tokens hachés, ports loopback, API non root/read-only ; reprise processus seulement ; charge, index, partitionnement, deux workers et restaurations isolées testés ; bascule Kafka en cours ; TLS/Kerberos et HA globale absents |
| P9 Livraison | À réaliser | Documentation de travail présente ; rapport final, répétition de démonstration, captures et publication autorisée restent à produire |

## Résultats effectivement observés

- PaySim v2 : 6 362 620 lignes, 8 213 fraudes ; provenance/licence et SHA dans [dataset.md](dataset.md). Données et dates de démonstration synthétiques.
- `env PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v` : **38/38**, code 0 (0,777 s). Test ajouté contre la lecture probabiliste d'un score non calibré ; constaté en échec avant correction.
- `docker compose run --rm api-tests` : **6/6**, code 0 (3,539 s), sans test ignoré. Auth/rôles, bornes, références inconnues, décision persistée, répétition, conflit, quatre appels concurrents et quota 429. Les décisions de ces essais portent `origin=automated_test`, pas une décision humaine bancaire.
- Kafka→Spark→HDFS : `runtime-v1`, 1 000 curated/1 000 uniques, données source et agrégats rapprochés ; reprise sans nouvelles entrées puis redémarrage broker/NN/DN et relecture. [Preuve P3](evidence/p3/runtime-v1.json).
- Latence p95 de ce rejeu borné : **87,4284 s**, incluant le démarrage différé du consommateur ; aucune revendication de régime établi ou d'objectif 15 s atteint.
- Échantillon temporel : sélection SHA déterministe indépendante du label, modulo 64, seed 42 ; **98 813 transactions, 141 fraudes** ingérées. Train 59 399/54 positives, validation 20 029/20 positives, test 19 385/67 positives ; bornes de steps 281 et 355.
- MLlib : choix LR sur PR-AUC validation ; seuil 0,7 sur validation. Test LR TP=37, FP=937, TN=18 381, FN=30, rappel **55,22 %**, précision **3,80 %**, ROC-AUC **0,92043**, PR-AUC **0,09164**. RF : TP=24, FP=468, TN=18 850, FN=43. [Rapport réel](evidence/p6/model-comparison.json). Résultats insuffisants pour un usage bancaire ; aucun test final utilisé pour sélectionner le gagnant.
- Les quatre soldes PaySim, labels et comptes exclus des prédicteurs ; features montant logarithmique, type et heure simulée ; prétraitements et poids appris sur train seul.
- Modèle `training-sample64-seed42:baseline-v1` rechargé pour l'inférence : 305 alertes sur les 1 000 transactions, sans les assimiler à 305 fraudes.
- Source SQL : snapshot immuable `api-review-tests-v1`, **2 décisions de test**, origines conservées, références HDFS vérifiées. Une lecture complète bornée remplace le curseur incrémental initialement envisagé pour éviter les commits tardifs ; ce n'est pas une CDC.

## Fichiers concernés et difficultés

Code : `src/rncp_bc1/{dataset,transactions,producer,model_metrics,graph_export,genai,api}.py`, jobs ingestion/vérification/JDBC/entraînement/scoring/publication/extraction, tests unitaires et HTTP. Plateforme : Compose, Dockerfiles, verrous images/connecteurs/Python/LLM, configurations Hadoop/Kafka/Mongo/SQL et scripts. Documentation et preuves dans `docs/`.

Les appels directs `docker compose` fonctionnent ; les refus de socket depuis certains scripts/subprocessus sont historiques et ne bloquent plus les appels directs. Le Python global 3.15 est hors plage : utiliser `.venv` 3.13. Des échecs ML (NumPy manquant puis import pandas indirect) ont été corrigés et les vrais jobs relancés avec succès. Le rendu Gephi PNG fonctionne via SVG/Batik/ImageIO. La capture desktop reste ouverte : montage DMG refusé, extraction alternative donnant une signature invalide, application non exécutée. Les textes Qwen initialement non conformes restent rejetés ; un texte structuré provisoirement stocké comme brouillon a été reclassé `rejected_quality_review` après revue technique et verrouillé par un test de régression. Deux sorties v6 conformes ont ensuite été réellement générées et revérifiées avec les contrôles renforcés.

## Dernières preuves P3/P5/P7/P8

- [Flux permanent](evidence/p3/live-verification.json) : 1 000 transactions à 50/s, puis rejeu et injection de trois fixtures invalides. Résultat : raw 2 003, curated 1 000 uniques, quarantaine 3 (type/destination/montant), 1 000 doublons supprimés ; sommes exactes. p95 logique 8,2806 s, hors commit/visibilité de lecture.
- [Gephi](evidence/p5/report.json) : 1 597 nœuds, 1 000 arêtes, 597 composantes et communautés ; degré maximal 23. Rendu de cinq composantes (88 nœuds/83 arêtes) ; aucun résultat de blanchiment inféré.
- [Faux positif, ligne PaySim 282](evidence/p7/generated-draft.json) et [vrai positif, ligne 252](evidence/p7/true-positive-draft.json) : appels Qwen 3B réels, deux contextes séparés et exemple de style explicite. Référence correcte, score non calibré, revue humaine, aucune devise/contact inventé. Le label sert à l'évaluation rétrospective uniquement. Le LLM n'explique pas causalement le modèle.
- Backend LLM arrêté : API 503 observé, code 1 attendu du script de génération ; aucune substitution par un gabarit. Ollama est temporairement arrêté pour les essais de charge.
- [Charge API](evidence/p8/api-load.json) : 50 requêtes à 5/s, zéro erreur, p95 36,31 ms. [SQL](evidence/p8/sql-index-benchmark.json) : 100 000 lignes temporaires synthétiques, plans Seq Scan/Index Scan et intégrité vérifiés ; résultat initial p95 14,85→0,36 ms, seconde répétition sauvegardée 35,21→0,39 ms, variabilité déclarée.
- [Deux workers](evidence/p8/spark-two-workers-fresh.json) contre [un worker](evidence/p8/spark-one-worker-fresh.json), même entrée et même résultat SHA : médianes 1,4562 contre 1,5444 s. Petit gain variable, pas de scalabilité linéaire revendiquée. Nouvelle QueryExecution par répétition ; premier protocole avec échange réutilisable conservé séparément et exclu de cette comparaison. Worker 2 arrêté après l'essai.
- [Parquet](evidence/p8/parquet-layout.json) : égalité multiensemble sur toutes les colonnes, copie partitionnée par type sans changer curated ; fichiers lus 20→1, médianes 0,6023→0,3520 s sur la requête TRANSFER/step>355. Pas de gain global supposé.
- [Permissions](evidence/p8/permissions.json), [panne Mongo](evidence/p8/mongo-outage.json) et [restaurations](evidence/p8/restoration.json) vérifiées. Restaurations sur le même hôte, sans suppression de bases/volumes existants ; pas une reprise après sinistre.

## Prochaines tâches

1. Terminer l'essai Kafka RF3/ISR2 sur `resilience-bc1-v1`, conserver le résultat, remettre le broker initial et Ollama en service.
2. Tester la relance des sinks Mongo sans duplication ; finaliser la documentation d'installation et de démonstration.
3. Sécurisation forte HDFS/Kafka/Spark, TLS, HA HDFS et portée de continuité : encore ouvertes ; ne pas qualifier le laboratoire de production.
4. Captures dans le logiciel client Gephi, rapport technique, répétition jury et reproduction depuis volumes neufs ; publication uniquement après accord.

Compétences préparées par les exécutions : C1.1–C1.3 et C2.1–C2.4, avec critères encore ouverts ; C1.4 reste largement à démontrer. Le jury seul valide officiellement. [Historique P0/P1](progress-history.md).

## Compléments après reprise du serveur — 18 novembre

- Kafka RF3/ISR2 : arrêt du leader 1 pendant émission ; leader 101, 220 messages acquittés/relus/uniques, zéro perte/doublon observé, acquittement maximal 1,0216 s. Broker 1 redémarré, trois ISR retrouvés ; [preuve](evidence/p8/kafka-leader-failure.json). Deux brokers auxiliaires arrêtés ensuite pour libérer la mémoire ; leur topic de test n'est pas disponible en écriture avec un seul ISR. ZooKeeper et hôte toujours uniques : aucune HA globale revendiquée.
- Montages des conteneurs restreints aux fichiers nécessaires, `.env` exclu. API UID 10001, propriétaires/tokens clients/dataset brut absents, écriture refusée : [contrôle réel](evidence/p8/api-isolation.json). Six tests API après cette modification : code 0, 3,165 s.
- Scoring relancé sans augmentation des comptes : 1 000 uniques/305 alertes. Décomposition additive LR vérifiée sur les 1 000 marges (tolérance 1e-8), noms issus du VectorAssembler car StandardScaler ne conserve pas les noms dans ses métadonnées. Un premier essai a échoué sur cette métadonnée avant publication, puis correction et relance réussies.
- GenAI v7 : facteur positif agrégé issu de cette décomposition, sans nombre technique client ni causalité. Premier appel froid 55 s en timeout ; budget porté à 90 s/appel, empreinte du prompt conservée. Génération réelle FP réussie : [preuve](evidence/p7/linear-signal-draft.json), 55,11 s cumulés de backend ; coquille « factor » à corriger à la revue humaine, texte brut non réécrit. Second cas v7 en cours.
- Client Gephi Linux 0.11.4 : aperçu et table des degrés/classes réellement capturés et inspectés ; [manifeste](evidence/p5/desktop-manifest.json). Le client est arrêté, sources/projets conservés.
- [Rapport technique intermédiaire](technical-report.md) créé ; installation et architecture actualisées. Répétition complète depuis volumes métier neufs encore à exécuter ; `infra/reproduction.yml` validé syntaxiquement pour un projet Compose séparé sans ports. Aucune publication ou compétence officiellement acquise annoncée.
