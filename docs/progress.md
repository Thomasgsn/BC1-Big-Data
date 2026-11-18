# Progression réelle — BC1

Mise à jour : 18 novembre 2026. Plan validé, développement autorisé. BC1 seul ; BC2/BC3 non commencés. Aucune publication, dépense ou transmission d'email.

## Finalisation BC1 en cours

Instruction utilisateur : « termine ». Candidat : **Thomas Gassmann**, réalisation individuelle, échéance non communiquée. Sécurité HDFS en cours dans `rncp-bc1-secure-hdfs-v1`, fichier `infra/secure-hdfs/compose.yml` : volumes métier et identités séparés, réseau interne sans port publié. Aucun montage de volumes du principal. Kerberos/SASL privacy/HTTPS/SPNEGO réellement exécutés et vérifiés : préfixe PaySim 1 000 lignes exact, faux utilisateur sans ticket et Bob authentifié refusés, CA/nom erronés et HTTPS anonyme refusés. Image HDFS maintenue : Netty 4.1.141, BC 1.87, JSch 0.2.26 ; audit OS/JAR 555→145 correspondances, critiques 9→0, 34 élevées résiduelles non acceptées/déclassées automatiquement. Les preuves sont dans `docs/evidence/p8/secure-hdfs/` et `dependency-scan/`. Profil sécurisé arrêté pour libérer la mémoire. Aucun déploiement Kerberos du principal à ce stade. Ne pas attribuer ces contrôles au principal avant déploiement prouvé.

Profil HA HDFS construit et testé : deux bascules automatiques nn1→nn2 et nn2→nn1, 80 fichiers synthétiques exacts par essai, zéro acquittement perdu, maxima d’écriture 4,023/11,236 s. Retour standby vérifié. Commande SSH arbitraire refusée et fencing réel du standby testé séparément. Correction du probe nc (adresse RPC configurée au lieu du loopback) vérifiée positivement/négativement. Profil arrêté sans suppression de volumes. [Dossier](hdfs-ha.md).

Kafka mTLS/ACL isolé : 1 000 lignes PaySim transmises/relues exactement, TLS 1.3, CA/hostname/certificat absent et droits interdits refusés. Spark isolé : calcul distribué authentifié exact, mauvais secret refusé avec timeout borné ; chiffrement RPC configuré sans fallback, aucune capture réseau. Ces profils sont arrêtés après essais et ne remplacent pas la configuration du principal. [Kafka](evidence/p8/secure-kafka/verification.json), [Spark](evidence/p8/secure-spark/verification.json).

## Dernière phase — Terminé et vérifié

Bascule principale vers Hadoop 3.4.3/Temurin 11.0.33/Ubuntu 24.04.5 effectuée après la reprise demandée (« reprend »). Nouvelle copie cohérente conservée dans `rncp-bc1-hadoop-pre-migration-v1`, sources montées en lecture seule. Sélection durable dans `COMPOSE_FILE`, modèle et bootstrap, secrets inchangés. NN/DN sains ; contrôles HDFS et modèles passés. [Journal](evidence/p8/hadoop-modern/deployment.json).

Le worker Spark était désinscrit du master malgré son conteneur actif ; redémarrage puis un worker ALIVE/deux cœurs observés et jobs terminés. Ajout d'un healthcheck vérifiant l'inscription réelle, testé positivement et négativement avec un nom artificiel absent. La cause initiale précise n'est pas établie ; aucune réparation automatique des conteneurs unhealthy n'est revendiquée. Checkpoints existants repris ; nouveau rejeu `post-migration-v1` vérifié : 1 000 bruts/uniques, zéro rejet, IDs et sommes exacts, quatre requêtes terminées. Le jeu d’origine a aussi été rapproché après reprise, sans changement de ses 1 000 transactions.

## État de la plateforme principale

Chaîne reproduite dans `rncp-bc1-repro-v1` sur volumes métier neufs. Projet isolé et son Ollama arrêtés, volumes conservés. **Plateforme principale rétablie et contrôlée** : API 200, 1 000 scores/305 alertes, dix décisions SQL après la nouvelle suite HTTP (huit avant celle-ci), digest Qwen attendu et préfixe HDFS exact. Premier démarrage Kafka refusé par une ancienne session ZooKeeper ; expiration automatique observée puis relance réussie avec la même configuration. Aucun znode ni volume supprimé. [Journal P9](evidence/p9/reproduction.json).

## État des phases

| Phase | Statut | Réalisation et réserve |
|---|---|---|
| P0 Cadrage | Terminé et vérifié | Cinq PDF lus, exigences distinctes des recommandations, plan validé |
| P1 Socle | En cours | PaySim intégral profilé, versions/digests, Git local, intégrations exécutées et client Gephi capturé ; audit Python réalisé, audit des sept images principales exécuté, alertes critiques/élevées ouvertes |
| P2 Infrastructure/contrats | Terminé et vérifié | Services opérationnels, contraintes et contrats testés, sauvegardes restaurées dans espaces isolés ; broker inaccessible et SIGINT vérifiés sans publication partielle |
| P3 Streaming/lac | Terminé et vérifié | Préfixe exact, checkpoints et persistance ; flux permanent, 1 000 doublons et trois rejets rapprochés ; préconditions checkpoint absent/corrompu vérifiées ; visibilité finale à approfondir |
| P4 API/multi-source | En cours | Six tests HTTP, rôles/quotas/concurrence/idempotence ; snapshots SQL joints ; décisions automatisées, adéquation pédagogique de la variété à confirmer |
| P5 Gephi | Terminé et vérifié | Export Mongo réel, degrés/modularité rapprochés, projet portable et captures du vrai client ; interprétation limitée à PaySim |
| P6 MLlib | Terminé et vérifié | LR/RF entraînés, test temporel réservé, rechargement et upserts idempotents ; parité reproduite ; 21 fixtures limites artificielles par modèle passées et scores publiés identiques au calcul direct |
| P7 GenAI | Terminé et vérifié | Qwen réel sur vrai/faux positif et reproduction ; sorties rejetées conservées ; contrôles partiels et qualité humaine encore nécessaires |
| P8 Sécurité/performance/résilience | En cours | Permissions/isolation, charge, optimisations, deux workers, restaurations et bascule leader Kafka RF3 testées ; TLS/auth forte et HA HDFS testés séparément, intégration au principal et HA globale ouvertes |
| P9 Livraison | En cours | Reproduction métier, installation, rapport et présentation PDF, preuves réelles ; machine vierge, répétition orale et publication autorisée restent ouvertes |

## Dernière phase exécutée

Reproduction complète des données métier : nouveaux volumes Kafka/ZooKeeper/HDFS/PostgreSQL/Mongo, sans port hôte, images/CSV/poids publics acquis réutilisés. 1 000 transactions initiales, échantillon 98 813/141 positives, deux modèles, scoring 1 000/305 alertes, export 1 597 nœuds/1 000 arêtes, Gephi 0,995408, API, extraction de quatre décisions automatisées et deux appels LLM. Même découpage, sélection et métriques de test ML que le premier rapport ; CSV graphe identiques par SHA. Pas de revendication de machine vierge ni d'égalité binaire des modèles. [Procédure et portée](reproduction.md), [journal](evidence/p9/reproduction.json), [sortie LLM brute](evidence/p9/generated-draft.json).

Audit Python : 18 dépendances API sans avis connu ; deux avis distincts sur kafka-python 2.3.1 ont motivé le passage à 2.3.2, roue vérifiée par SHA et image reconstruite. Deux régressions parseur/SCRAM passent localement et en conteneur. Audit runtime après correction : zéro avis connu. Le rejeu initial et l'entraînement ont précédé le patch ; un nouveau run de 1 000 transactions avec le client corrigé est exact dans HDFS. L'audit ne couvre pas OS/JAR/images. [Preuve](evidence/p8/dependency-security-summary.json).

Fichiers concernés : `requirements-runtime.txt`, `tests/integration/check_kafka_security.py`, `infra/reproduction.yml`, preuves P8/P9 ; README et documents installation, compatibilité, rapport, matrice, tests, progression et jury. Le manifeste du code rattache les preuves aux fichiers sans prétendre à un commit absent.

## Vérifications exécutées

- `env PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v` : **38/38, code 0, 0,902 s**, après mise à jour de dépendance.
- Projet isolé, `docker compose … run --rm api-tests` : **6/6, code 0, 2,374 s**, sans skip. Répétition délibérée après perte de sortie lors de la reprise ; quatre décisions automatisées présentes au snapshot, pas de saisie humaine.
- `check_kafka_security.py` : **2/2 local et conteneur**, code 0 ; longueurs de trame et itérations SCRAM bornées, cas valides inclus.
- Vérification `security-patch-v1` : **1 000 raw/curated uniques, zéro rejet**, identités et sommes décimales exactes. Latence logique p95 303,75 s comprenant plusieurs minutes d'attente avant ingestion, pas une mesure de débit permanent.
- Génération réelle isolée : deux appels, environ **53,84 s** cumulés côté backend. Score non calibré et revue humaine, référence correcte, contribution sans causalité. Coquille « factor » conservée ; aucun envoi.

## Inférence après retour au principal

Les deux pipelines sauvegardés ont été rechargés sur 21 fixtures artificielles chacun : cinq types autorisés, montants zéro/centime/maximum Decimal(18,2), changement de journée et heure future ; un type inédit teste uniquement l'encodage interne, le contrat d'ingestion le refuse toujours. Vecteurs de neuf dimensions et scores finis, distributions binaires cohérentes. Les 1 000 scores Mongo ont été rapprochés d'une nouvelle transformation des transactions HDFS sans label/solde : différence absolue maximale **0**, mêmes seuils et alertes. Aucun réentraînement ni écriture métier. [Preuve](evidence/p6/inference-verification.json). Fichiers ajoutés : `tests/integration/check_model_inference.py` et `check_restored_state.py` ; premier essai puis relance après renforcement des contrôles de valeurs nulles.

## Contrôles finaux du dossier local

[Rapport des contrôles](evidence/p9/local-delivery-checks.json) : empreintes source/configuration/tests, JSON, syntaxe Python, liens Markdown et recherche limitée des secrets locaux par valeur exacte. Le rapport daté précise le dernier périmètre vérifié ; ce contrôle ne remplace pas un scanner général. Dépôt local, sans publication.

Fichiers du chantier runtime : `infra/hadoop-modern/{Dockerfile,compose.yml,clone.yml,clone.sh,migration.yml,lock.json}`, `tests/integration/{check_hdfs_runtime.py,check_hdfs_models.py}`, `docs/hadoop-runtime.md` et preuves `docs/evidence/p8/hadoop-modern/`. Baseline primaire et clone réels, aucun réentraînement ni ajustement du test temporel. Reprise demandée en réponse à la proposition de migration ; bascule exécutée, journal et nouvelle sauvegarde conservés.

## Résultats majeurs et limites

PaySim : 6 362 620 lignes, 8 213 fraudes, source/licence/SHA dans [dataset.md](dataset.md). Les données et horodatages métier sont synthétiques. Les soldes, labels et comptes ne sont pas des prédicteurs.

LR retenue sur validation, seuil 0,7 ; test réservé : TP 37, FP 937, TN 18 381, FN 30, rappel 55,22 %, précision 3,80 %, ROC-AUC 0,92043, PR-AUC 0,09164. La faible précision interdit une promesse bancaire. [Rapport ML](evidence/p6/model-comparison.json).

Flux permanent : 1 000 transactions à environ 50/s, puis doublons/rejets : raw 2 003, curated 1 000, quarantaine trois ; p95 logique 8,28 s hors commit/visibilité. [Preuve](evidence/p3/live-verification.json). Kafka RF3/ISR2 : 220 messages acquittés/relus, zéro perte/doublon observé pendant arrêt du leader, trois ISR retrouvés ; topic isolé, ZooKeeper/hôte uniques. [Preuve](evidence/p8/kafka-leader-failure.json).

API : 50 lectures à 5/s, p95 36,31 ms, zéro erreur. SQL : 100 000 lignes temporaires synthétiques, index mesuré ; Spark deux workers, gain faible/variable ; copie Parquet exacte, pruning 20→1 fichier. Restaurations SQL/Mongo/HDFS dans nouveaux espaces du même hôte, pas une reprise après sinistre. [Rapport technique](technical-report.md).

## Prochaines tâches

1. Migration et rejeu terminés/vérifiés. Prochain chantier : profil isolé d’authentification forte et chiffrement HDFS/Kafka/Spark, en conservant les limites et preuves du laboratoire actuel.
2. Cas limites ML vérifiés : [preuve](evidence/p6/inference-verification.json). Compléter les scénarios de reprise ouverts, sans retoucher le test final pour optimiser les métriques.
3. Approfondir la disponibilité des services critiques selon le plan ; audits OS/JAR, restauration des modèles et sauvegardes hors hôte restent ouverts. Toute opération sensible sur les données/comptes existants nécessite accord ; privilégier un profil isolé.
4. Finaliser rapport/support, répéter la démonstration avec durée mesurée ; compléter candidat/binôme/contributions réelles. Publication uniquement après accord explicite.

Aucune compétence n'est déclarée officiellement acquise. Les limites et critères ouverts figurent dans [la matrice](rncp-matrix.md). [Historique conservé](progress-history.md).


Vérifications de cette phase : 38 tests unitaires (dernier passage code 0, 1,829 s), six tests HTTP (code 0, 6,785 s), bootstrap réel en répertoire temporaire, santé d'inscription positive/négative, rechargement des deux modèles, reprise checkpoint et nouveaux/anciens préfixes rapprochés. Fichiers modifiés : bootstrap, `.env.example`, sélection publique du `.env` ignoré, Compose (santé workers), journal actif des requêtes dans `ingest.py`, documentation et preuves. `scripts/check_spark_worker.py` ajouté. La suspicion d'arrêt anticipé a été retirée : code initial déjà ordonné correctement, seule la visibilité du journal est améliorée. Compétences préparées : C1.3 et C2.2–C2.4 ; aucune validation officielle ou HA globale revendiquée.

## Livraison en cours : vérifications supplémentaires

- Candidat confirmé : Thomas Gassmann, seul, date de remise non communiquée.
- Ajouts : `infra/{hdfs-ha,secure-kafka,secure-spark,audit,documents}/`, contrôle préalable `src/rncp_bc1/streaming_state.py`, tests checkpoint et producteur, export documentaire, sources de présentation, documentation et preuves liées.
- 38 tests unitaires réussis (0,735 s), six tests HTTP réussis (4,768 s). Les deux tests réseau/arrêt producteur et six contrôles préalables checkpoint ont terminé avec le code 0.
- Audit Trivy des sept images principales terminé, résultats publics en P8. Des critiques/élevées restent à analyser et corriger ; aucun risque accepté au nom du candidat. Voir [sécurité](security-profiles.md).
- Rapport final de huit pages et présentation de douze pages PDF produits après les dernières preuves, pages inspectées ; aucune répétition orale humaine revendiquée.
- Démonstration `jury-20261118-v1` : préfixe et agrégats exacts, graphe Mongo et scoring 1 000/305 vérifiés. Première génération : 503 après timeout de chargement à 90 s, échec conservé ; préchauffage réussi puis nouvelle génération réelle réussie (88,026 s côté modèle, deux appels, chargement compris). Modèles sauvegardés réutilisés explicitement.
- Compétences préparées : C1.3/C1.4 et C2.2–C2.4 ; la matrice conserve les réserves de portée et d’appréciation pédagogique.

## État final observé de cette campagne

La démonstration technique `jury-20261118-v1` a parcouru Kafka, Spark, HDFS, MongoDB, le modèle sauvegardé, l’API et le LLM réel. Les 1 000 lignes et sommes sont exactes, zéro rejet, 305 alertes et export 1 597 nœuds/1 000 arêtes. Une tentative LLM a échoué au chargement ; après préchauffage, le brouillon réel a été persisté. La coquille « factor » reste visible et la revue humaine est obligatoire. [Journal](evidence/p9/demonstration.json), [texte brut](evidence/p9/demonstration-draft.json).

Durée observée du parcours : 1 600,667 secondes, avec pauses documentaires, audits et reprise de génération. Ce n’est pas une durée de présentation continue. Aucune répétition orale du candidat ni vidéo fictive n’est déclarée. Le rapport et le support PDF sont fournis et les sources restent modifiables.

Les phases techniques marquées terminées couvrent leurs critères logiciels dans le périmètre documenté. P8 reste En cours : maintenance des vulnérabilités restantes, intégration des profils sécurisés au principal et continuité globale. P4 conserve les réserves d’appréciation pédagogique sur la seconde source. P9 conserve la répétition orale, la machine vierge et la publication autorisée. Le projet n’est pas déclaré entièrement prêt au jury tant que ces écarts ne sont pas traités ou arbitrés explicitement.

Les services principaux ont été observés sains après la campagne (Ollama actif sans healthcheck). Les profils HA, Kerberos, mTLS et Spark sécurisé sont arrêtés, leurs volumes conservés. Aucun BC2/BC3 commencé, aucune publication ou dépense effectuée.
