# Vérifications BC1

## Résultats actuels

Les sections datées P0/P1 ci-dessous sont historiques. Les résultats de plateforme, SQL/Mongo, ML et API sont maintenant réellement obtenus : voir [progress.md](progress.md), [preuve streaming](evidence/p3/runtime-v1.json) et [comparaison MLlib](evidence/p6/model-comparison.json). Derniers passages : 38 tests unitaires réussis (1,829 s), 6 tests API réels réussis sans skip (6,785 s). Les sorties LLM rejetées restent des échecs, aucune sécurité forte/HA n’est déduite d’un redémarrage.

Commandes : `env PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v` ; `docker compose run --rm api-tests`. Les essais persistants de décisions utilisent explicitement `origin=automated_test`.


## Campagne du 18 novembre — reproduction et dépendances

[Journal complet](evidence/p9/reproduction.json), [procédure](reproduction.md). Volumes métier neufs, réemploi explicite des images/CSV/poids ; mêmes découpages et métriques ML, mêmes SHA CSV de graphe, 1 000 scores/305 alertes, six tests HTTP, quatre décisions automatisées intégrées et deux appels Qwen réels. Brouillon relu techniquement, coquille de français conservée : pas d'approbation humaine bancaire.

- Audit `pip-audit 2.10.1` API : 18 dépendances, zéro avis connu, code 0.
- Runtime initial : quatre entrées de base d'avis, **deux avis distincts** sur kafka-python 2.3.1, code 1 attendu. Mise à jour 2.3.2, roue vérifiée, image reconstruite.
- Runtime corrigé : zéro avis connu, code 0. [Synthèse et limites](evidence/p8/dependency-security-summary.json). OS/JAR/images non audités par ce protocole.
- `env PYTHONPATH=src .venv/bin/python tests/integration/check_kafka_security.py` : deux tests réels, code 0 ; même script dans le conteneur Python Spark, deux tests code 0. Fixtures binaires/SCRAM artificielles explicitement identifiées, aucune attaque sur la version vulnérable.
- Rejeu corrigé `security-patch-v1` : 1 000 bruts/uniques, aucun rejet, IDs et sommes exactes ; attente producteur→consommateur de plusieurs minutes incluse dans p95 303,75 s.
- Retour au principal : premier démarrage Kafka échoué `NodeExists` ; ancienne session ZooKeeper expirée automatiquement, nœud absent au contrôle, relance avec même configuration réussie. Pas de suppression de znode ni de retry automatique implémenté. Incident reproductible à surveiller lors d'une reprise simultanée.
- HDFS principal `runtime-v1` : 1 000 bruts/uniques, zéro rejet, CSV/sommes exactes après retour. `check_restored_state.py` relit Mongo/SQL/readiness/Ollama : 1 000 scores/305 alertes, huit décisions et digest Qwen attendu, code 0. Première version du contrôle visait par erreur `scores` au lieu de `fraud_scores` ; corrigée avant validation, aucune perte métier constatée.

Commande de relecture métier, distincte du contrôle HDFS :

```bash
docker compose exec -T api python tests/integration/check_restored_state.py --model-version training-sample64-seed42:baseline-v1 --expected-scores 1000 --expected-alerts 305 --minimum-decisions 2 --check-llm
```

Les nombres sont des références de cette campagne, pas des valeurs universelles. Une autre campagne doit fournir ses propres références. Les sorties historiques ci-dessous sont conservées avec leur portée initiale.

## Inférence ML rechargée et parité Mongo

Commande réellement exécutée après renforcement des contrôles :

```bash
docker compose run --rm -e SPARK_DRIVER_PACKAGES=org.mongodb.spark:mongo-spark-connector_2.12:10.7.0 spark-driver /project/tests/integration/check_model_inference.py --training-run training-sample64-seed42 --model-version baseline-v1 --transaction-run runtime-v1 --expected-rows 1000
```

Code 0 : 21 fixtures artificielles par modèle LR/RF, vecteurs de neuf dimensions et distributions binaires finis. Cinq types autorisés, montants zéro/centime/maximum, changement de journée et step futur ; type inédit interne distinct du contrat métier. 1 000 scores réels HDFS→modèle comparés à Mongo : différence absolue maximale zéro, références/seuils/alertes égaux. Aucun label/solde en entrée, aucun entraînement ou changement de modèle ; [sortie réelle](evidence/p6/inference-verification.json). Ces fixtures testent le calcul, pas la qualité de détection hors distribution.

## Runtime HDFS candidat : essais isolés

[Procédure et résultats](hadoop-runtime.md), [journal d'expérience](evidence/p8/hadoop-modern/experiment.json). Archive Hadoop 3.4.3 SHA-512 vérifié ; base Temurin 11 JRE/Noble par digest, build code 0. Versions réellement relevées : Hadoop 3.4.3, Java 11.0.33, Ubuntu 24.04.5. Nouveau projet sans port hôte ni partage de volumes métier actifs.

Écriture/relecture Parquet du préfixe réel 1 000 : exact sur toutes les lignes et sommes ; redémarrage puis relecture identique, code 0. Clone des volumes originaux arrêtés proprement : tous fichiers rapprochés par hash, sources inchangées pendant copie, refus réel d'une destination non vide (code 1 attendu). Démarrage du clone, vérification du préfixe original et relecture de 98 813 transactions d'entraînement : code 0. Deux modèles rechargés : SHA du rapport et de chacun des deux ensembles de 1 000 scores identiques au principal. Baseline principale en Spark distribué, contrôle clone en Spark local[2] ; aucune mesure de performance comparative.

Le principal utilise encore 3.4.2, remis en service après copie. Candidat et clone arrêtés, aucun volume effacé. Signature GPG de l’archive vérifiée dans un trousseau temporaire, [preuve](evidence/p8/hadoop-modern/signature.json) ; clé récupérée sur le site Apache, sans authentification hors bande. Audit OS/JAR, requêtes reprenant leurs checkpoints et sécurité forte restent hors de cette preuve. La bascule principale nécessite l'accord prévu pour une modification sensible.

## Bascule principale vers Hadoop 3.4.3 — 18 novembre, matin

[Journal](evidence/p8/hadoop-modern/deployment.json). Nouvelle copie cohérente dans `rncp-bc1-hadoop-pre-migration-v1`, sources read-only, tous fichiers rapprochés, aucune suppression. Variables/secrets existants conservés ; sélection publique persistante du runtime et bootstrap vérifiés dans un répertoire temporaire réel, mode 0600 et non-écrasement testés.

- NN/DN sains sous Hadoop 3.4.3, Temurin 11.0.33, Ubuntu 24.04.5 ; image réellement utilisée : `sha256:ec962c7edaaee18d3326e6c62a70e8673787f233cc8128eed6adccd7c3a77f69`.
- Dernière suite unitaire : **38/38**, code 0, 1,829 s. Suite HTTP : **6/6**, code 0, 6,785 s. Les décisions automatisées passent de huit à dix après cette suite ; aucune revue humaine prétendue.
- [Préfixe existant](evidence/p8/hadoop-modern/deployed-hdfs.json) : 1 000 bruts/uniques, zéro rejet, IDs et sommes CSV exacts. [Modèles rechargés](evidence/p8/hadoop-modern/deployed-models.json) : 98 813 transactions lisibles, mêmes SHA du rapport et des deux ensembles de scores que la baseline.
- Worker absent du master alors que son conteneur tournait : redémarrage, un worker ALIVE/deux cœurs, puis jobs terminés. Cause initiale précise non établie. Nouveau healthcheck d'inscription réelle : code 0 sur le worker, code 1 attendu sur un nom artificiel absent ; worker recréé healthy. Il détecte l'anomalie mais ne déclenche pas automatiquement un redémarrage.
- [Checkpoints originaux repris](evidence/p8/hadoop-modern/checkpoint-resume.json), code 0. Rejeu neuf `post-migration-v1` : 1 000 messages acquittés, neuf labels fraude, [quatre requêtes terminées](evidence/p8/hadoop-modern/post-migration-ingestion.json) avec `active=false` et métriques lisant 1 000 transactions.
- Une suspicion d'arrêt anticipé du code a été retirée après relecture complète : il attendait déjà les trois sorties de données avant le snapshot métriques. L'attente redondante proposée a été supprimée ; seul l'état actif des requêtes est ajouté au journal. Aucun correctif algorithmique non justifié présenté comme acquis.

Les durées de rejeu comprennent les attentes et démarrages ; pas de nouvelle mesure de capacité. Les limites TLS/Kerberos, audits OS/JAR et HA restent ouvertes.

## Résultats effectivement observés au cadrage

Date : 17 novembre 2026. Les commandes ci-dessous sont des diagnostics, pas des tests de l'application. Cette section décrit le cadrage avant validation. Les tests des outils dataset exécutés ensuite sont consignés dans la section P1 ci-dessous ; aucun test de plateforme ou modèle n’avait été exécuté à cette date du cadrage.

| Vérification | Commande ou méthode | Résultat réel |
|---|---|---|
| Inventaire | `rg --files --hidden`, `ls -la` | Cinq PDF et configuration IDE ; aucun code initial |
| État Git | `git status --short` | Échec : aucun dépôt Git dans le dossier ou ses parents |
| Lecture PDF | `pdfplumber.open`, extraction page par page | INFO 5 pages ; REF 25 ; SUJET BC1 3 ; BC2 4 ; BC3 5 ; texte disponible pour les cinq |
| Structure sujet/référentiel | Rendus `page.to_image(resolution=100)`, planche visuelle | 3 pages SUJET et 5 pages REF BC1 rendues et inspectées ; structure des tableaux identifiée |
| Intégrité sources | SHA-256 calculés en Python | Manifestes enregistrés dans `source-manifest.json` ; aucun PDF modifié |
| Architecture hôte | `uname -m` | `x86_64` |
| RAM et CPU | `system_profiler SPHardwareDataType -detailLevel mini` | 16 Go RAM ; 8 cœurs annoncés ; avertissements sysctl, CPU à confirmer |
| Lecture sysctl directe | `sysctl -n hw.memsize hw.ncpu` | Refus d'accès ; ne pas la présenter comme une mesure réussie |
| Espace disque | `df -h .` | Environ 424 Gio disponibles au moment du contrôle |
| Python | `python3 --version` | 3.12.13 |
| Docker CLI/moteur | `docker version --format '{{json .}}'` | Client 29.9.3 ; serveur absent ; socket Docker Desktop introuvable |
| Compose | `docker compose version` | v5.7.0 |
| Java | `java -version` | Échec : aucun runtime Java trouvé ; lanceur `/usr/bin/java` seulement |
| PaySim local | Inventaire `.data/` | Aucun CSV/archive PaySim présent |
| PaySim externe | Page auteur et page Kaggle consultées | Source référencée par l'auteur ; page Kaggle non lisible par outil web ; téléchargement non vérifié |
| Métadonnées Kaggle | Requête curl vers API publique avec délai maximal | Aucun fichier de métadonnées exploitable ; licence, taille et version non vérifiées |

Contrôle documentaire exécuté en Python en fin de cadrage : 22 liens locaux résolus sans erreur, 5 empreintes PDF inchangées sur 5, 10 fichiers minimaux présents sur 10 dans `bc1/`, 8 compétences présentes sur 8 dans la matrice, blocs Markdown correctement clos, absence de code Python/Compose et de dossiers BC2/BC3. Commande terminée avec code 0. Le rendu Mermaid n'est pas encore vérifié dans un moteur graphique ; sa présence est contrôlée, pas son rendu.

## Protocole de tests à implémenter après validation

| Niveau | Cas nécessaires | Critère de réussite |
|---|---|---|
| Unitaire / contrat | JSON invalide, champ manquant, type inconnu, montant nul/négatif/limite, précision, date reconstruite, identifiant stable | Comportement conforme au contrat, erreur explicite ou quarantaine ; aucune perte silencieuse |
| Intégration stream | Flux borné, doublons, messages retardés, arrêt/reprise | Identifiants et totaux rapprochés ; checkpoints réutilisés ; ambiguïtés d'écriture traitées |
| Stockages | PK/FK, rollback SQL, upsert Mongo, arêtes orphelines, export puis import Gephi | Intégrité démontrée ; relance sans duplication logique ; export traçable |
| Multi-source | Décision SQL, snapshot complet immuable borné, mise à jour versionnée, jointure HDFS | Provenance préservée, snapshot relu, décisions rattachées au bon dossier/transaction |
| API | Authentification, révocation, rôles, quota, filtres, limites, absence dépendance | Codes et contrat documentés ; refus corrects ; pas de fuite d'information sensible |
| ML | Découpage temporel, prétraitement, absence fuite, classes rares, reload modèle, parité features | Deux modèles effectivement comparés ; métriques recalculables ; test final indépendant |
| GenAI | Appel réel, contexte insuffisant, incohérence factuelle, contenu hostile, timeout, backend absent | Sorties validées ou erreur visible ; preuve du modèle utilisé ; brouillons sans envoi |
| Sécurité | Identités non autorisées, droits HDFS, ACL Kafka, TLS, secrets et logs | Accès refusé où attendu, chaîne de confiance vérifiée, secret non divulgué |
| Résilience | Arrêts processus puis bascules profil répliqué, perte du driver, sink indisponible | Reprise et continuité mesurées séparément ; RPO/RTO observés, pertes/doublons expliqués |
| Performance | Charge SQL et API, débit Kafka/Spark/HDFS/Mongo, fichiers/index avant/après | Jeu et environnement identiques, mesure p50/p95/débit/erreurs, intégrité après charge |
| Reproduction | Installation isolée, relance et restauration | Chaîne complète refaite depuis procédure, provenance et résultats conservés |

Les fixtures automatisées seront synthétiques et clairement étiquetées. Une fixture valide un comportement logiciel ; elle ne prouve pas la qualité d'un modèle sur PaySim ou un résultat financier réel.

## Mesures proposées, non obtenues

Point de départ : 100 transactions/s pendant 10 minutes sur un échantillon documenté, puis paliers selon mémoire et retard ; objectif exploratoire de latence p95 émission → stockage consultable inférieur à 15 secondes, à confirmer après baseline. Lecture API bornée : objectif exploratoire p95 inférieur à 500 ms à 5 requêtes/s. Quotas et capacité ne sont pas la même mesure.

Comparer le pipeline initial et optimisé sur les mêmes entrées, après échauffement, avec au moins trois répétitions si la variabilité l'exige. Rapporter valeurs observées, étendue, volume, configuration et erreurs ; ne pas retirer les échecs pour embellir les résultats. Pour les pannes, viser d'abord une reprise inférieure à 120 secondes sur le jeu de démonstration ; ce seuil est une hypothèse de travail, pas une garantie ou une exigence du référentiel.

Modèle de journal futur : date UTC, identifiant de tâche, commande exacte sans secret, version code/images, SHA dataset, jeu et paramètres, attendu, observé, code retour, emplacement de preuve, limites et action suivante. Un test non lancé reste « non exécuté » ; un composant écrit sans essai reste « Implémenté mais non vérifié ».


## P1 — tests et exécutions après validation

- `PYTHONPATH=src python3 -m unittest discover -s tests -v` : code 0, 8 tests réussis, 0,017 s lors du premier passage. Fixtures synthétiques ; aucun mock d’un service réel présenté comme intégration.
- `PYTHONPATH=src python3 -m rncp_bc1.dataset extract --archive data/raw/paysim-v2.zip --destination data/raw` : code 0 ; CRC ZIP, membre et taille contrôlés ; empreinte archive enregistrée dans `dataset.md`.
- `PYTHONPATH=src python3 -m rncp_bc1.dataset profile --csv data/raw/PS_20174392719_1491204439457_log.csv --output docs/evidence/p1/paysim-profile.json` : code 0 ; 6 362 620 lignes lues, 0 invalide selon les règles implémentées. Aucun test d’unicité par contenu, modèle ou graphe réalisé.
- `git check-ignore data/raw/paysim-v2.zip data/raw/PS_20174392719_1491204439457_log.csv` : deux chemins confirmés ignorés.
- `python3 scripts/check_environment.py --actor codex` : code 1 ; Docker inaccessible, aucune sonde image exécutée. Rapport dans `docs/evidence/p1/environment-codex.json`.
- `docker run --rm hello-world` : réussite transmise par l’utilisateur, avec digest image ; exécution non effectuée par Codex. La mémoire VM et l’intégration restent à vérifier.

Les versions candidates, digests et commandes de reprise figurent dans `compatibility.md`. Les tests API, Kafka, Spark, HDFS, SQL/Mongo, MLlib, Gephi, LLM, sécurité et résilience restent non exécutés.

Contrôles finaux exécutés : `python3 -m py_compile` sur les deux outils (code 0), validation des liens Markdown locaux et des 5 empreintes PDF, sommes type/step/labels du profil cohérentes, 5 digests d'images syntaxiquement valides avec amd64. `git diff --check` ne remonte rien mais ne couvre pas les nouveaux fichiers non suivis. Aucune exécution de sonde Docker réussie n'est déduite de ces contrôles statiques.


## Reprise P2/P3 — contrôles hors ligne puis démarrage réel

- `make test` sous `.venv/bin/python` 3.13.18 : **29 tests réussis**, 0,773 seconde lors du dernier passage. Extracteur/profileur, contrat, CLI fichier réelle (publication atomique et préservation de fichier), métriques et choix de seuil, référence CSV, export CSV de mini-graphes artificiels. Aucun mock de Kafka/Spark/SQL/Mongo présenté comme intégration.
- 10 000 événements JSONL générés depuis le véritable CSV : comparaison ligne par ligne des identifiants, champs et montants, 10 000 identifiants uniques ; 68 labels fraude observés dans ce préfixe. Rapport `docs/evidence/p2/jsonl-control.json`. Ce débit JSONL n’est pas une mesure Kafka.
- Producteur vers `127.0.0.1:1` : code 1, `NoBrokersAvailable`, zéro ligne acquittée, reprise à la ligne 1. Gestion d’erreur réelle, pas succès d’ingestion.
- `docker compose config --quiet` : code 0. Configuration résolue inspectée sans afficher les secrets : images externes par digest, ports publiés sur loopback seulement, `.env` 0600 et chemins sensibles ignorés. Rapport `docs/evidence/p2/config-check.json`.
- `bash -n` sur les scripts et compilation des modules Python : code 0. `node --check` sur les scripts Mongo : code 0. Ces contrôles ne prouvent pas le fonctionnement des services.
- Une tentative `bash scripts/stack.sh smoke` depuis le contexte restreint a échoué au socket avant création des services. Un appel direct ultérieur `docker compose ps` a réussi, puis le démarrage direct Compose a effectivement commencé les téléchargements. Les résultats d’intégration seront ajoutés à réception, sans confondre accès CLI et services opérationnels.


## Cohérence du dossier local après cette phase

[Contrôle réellement exécuté](evidence/p9/local-delivery-checks.json) : 94 fichiers source/configuration/tests rapprochés du manifeste, 55 JSON, syntaxe de 44 Python, 119 liens locaux Markdown hors historique ; zéro erreur détectée. Recherche des valeurs exactes des secrets locaux courants dans les fichiers texte non ignorés : aucun résultat, sans afficher de valeur. Cette recherche limitée n'est pas un audit global de secrets. `docker compose -f docker-compose.yml -f infra/hadoop-modern/migration.yml config --quiet` : code 0. Git sans commit ni publication ; un `git diff --check` vide n'aurait pas validé les fichiers encore non suivis, d'où un contrôle direct des espaces finaux.


Après la reprise des checkpoints : [jeu original vérifié](evidence/p8/hadoop-modern/after-checkpoint-verified.json), 1 000 bruts/uniques et zéro rejet, IDs/sommes exacts. Nouveau rejeu : [post-migration-v1](evidence/p8/hadoop-modern/post-migration-verified.json), mêmes contrôles réussis et quatre requêtes inactives au compte rendu final. L'état `completed_and_verified` du journal concerne cette migration et ses contrôles, pas la livraison du bloc RNCP. Les latences logiques conservées ne sont pas présentées comme un benchmark de montée de version.

## Finalisation du 18 novembre

- 38 tests unitaires réexécutés : code 0, 0,735 s.
- Contrôles réellement exécutés des profils [sécurité](security-profiles.md) et [HA HDFS](hdfs-ha.md) : preuves P8 correspondantes.
- `env PYTHONPATH=src .venv/bin/python tests/integration/check_producer_failures.py` : code 0 ; broker inaccessible, zéro acquittement et erreur explicite ; SIGINT après deux lignes, code 130, aucun JSONL partiel publié, temporaire retiré. Préfixe réel de 100 lignes dans un CSV temporaire identifié.
- `docker compose run --rm --no-deps -e SPARK_DRIVER_PACKAGES= spark-driver /project/tests/integration/check_checkpoint_guard.py` : code 0 ; nouveau run vide et métadonnées valides acceptés, checkpoint absent/corrompu/ID invalide refusés, run réel existant accepté. Fixtures artificielles conservées en namespace neuf. Contrôle préalable uniquement, pas une vérification exhaustive de chaque fichier d’état.
- Rapport PDF et présentation PDF exportés, texte extrait et toutes les pages rendues/inspectées visuellement. Aucun passage oral humain revendiqué.

Six tests HTTP réexécutés après les ajouts, code 0, 4,768 s. Démonstration [jury-20261118-v1](evidence/p9/demonstration.json) et [nouveau brouillon réel](evidence/p9/demonstration-draft.json) vérifiés ; l’échec initial reste conservé. Audits Trivy des sept images principales : code 0 pour l’exécution de chaque scan, avec des correspondances critiques/élevées résiduelles. Un scan terminé n’est pas un test de sécurité sans vulnérabilité.
