# Reproduction isolée BC1

## Portée réellement vérifiée

Le 18 novembre 2026, le projet Compose `rncp-bc1-repro-v1` a démarré sur de nouveaux volumes Kafka, ZooKeeper, HDFS, PostgreSQL et MongoDB. Aucun port hôte publié. Les volumes du projet principal ont été conservés ; son arrêt temporaire limite la consommation mémoire.

Images déjà construites/téléchargées, CSV PaySim vérifié et poids publics Qwen réutilisés. Seul le sous-répertoire `models` du cache Ollama principal est monté en lecture seule : les clés privées du serveur ne sont pas partagées. Ce protocole vérifie une reconstruction de l'état métier ; il ne prouve pas une installation sur une machine vierge ni un fonctionnement sans réseau. Les dépendances Maven peuvent encore être résolues en ligne.

Le [journal d'exécution](evidence/p9/reproduction.json) distingue les étapes initiales sous kafka-python 2.3.1 de celles après correction en 2.3.2. Le rejeu initial n'a pas été exécuté intégralement sous la dépendance corrigée. Un nouveau rejeu de 1 000 lignes a été émis et rapproché après cette mise à jour ; les deux régressions du parseur/SCRAM ont passé localement et dans l'image.

## Résultats

| Étape | Observation |
|---|---|
| Initialisation | Services de base sains, HDFS hors safemode, topic trois partitions RF1, contraintes SQL vérifiées |
| Préfixe PaySim | 1 000 lignes acquittées, 1 000 IDs curated uniques, zéro rejet ; comptes et sommes exacts |
| Échantillon d'entraînement | 98 813 lignes, 141 labels positifs ; sélection SHA indépendante du label |
| MLlib | Même découpage, même modèle/seuil sélectionnés et mêmes métriques de test que le rapport initial ; pas de revendication d'égalité binaire de tous les fichiers modèles |
| Scoring | 1 000 scores, 305 alertes ; décomposition additive LR vérifiée |
| Mongo → Gephi | 1 597 nœuds et 1 000 arêtes, CSV identiques par SHA ; modularité 0,995408 |
| API | Six tests HTTP réussis, sans skip ; suite répétée après interruption, décisions explicitement automatisées |
| SQL → HDFS | Snapshot neuf de quatre décisions `automated_test`, références valides dans `runtime-v1` |
| Génération locale | Deux appels Qwen réels, référence et faits contrôlés ; coquille « factor » conservée, brouillon à relire, aucun envoi |
| Client Kafka corrigé | Nouveau run `security-patch-v1` : 1 000 bruts/uniques, zéro rejet, IDs et sommes rapprochés |

La latence logique du préfixe initial est 61,09 s p95 ; celle du rejeu après correction est 303,75 s, car plusieurs minutes séparent émission et ingestion. Ces mesures incluent cette attente et excluent le commit/visibilité. Elles ne sont pas présentées comme une régression du débit permanent.

## Runtime des campagnes

La campagne v1 conservée ci-dessus a utilisé le runtime initial 3.4.2. Le principal a ensuite basculé vers 3.4.3 ; voir [le journal](evidence/p8/hadoop-modern/deployment.json). Pour un nouvel essai du runtime courant, ajouter `-f infra/hadoop-modern/migration.yml` entre le fichier de base et `infra/reproduction.yml`. Un `-f` explicite remplace la sélection `COMPOSE_FILE` du `.env`. Ne pas réécrire la preuve v1 comme si elle avait été exécutée sous 3.4.3.

## Procédure pour un nouvel essai

Depuis `bc1/`, vérifier le fichier `infra/reproduction.yml` et choisir un **nouveau nom de projet**. Le nom `rncp-bc1-repro-v1` désigne désormais un état conservé, pas des volumes vierges. Le partage de cache exige que `rncp-bc1_ollama-models` existe déjà avec les poids verrouillés. Sur une machine neuve, utiliser le volume Ollama propre du projet et acquérir les poids selon l'installation, en adaptant cet override.

1. Arrêter la plateforme principale avec `docker compose stop`, sans supprimer ses volumes.
2. Démarrer le projet isolé : `docker compose -p MON_PROJET_NEUF -f docker-compose.yml -f infra/reproduction.yml up -d --wait --wait-timeout 300`.
3. Initialiser HDFS et le topic selon `scripts/stack.sh`, en ajoutant les mêmes options `-p` et `-f` à **chaque** commande Compose. Ne pas lancer le wrapper inchangé : il cible le projet principal.
4. Exécuter les commandes de [l'installation](installation.md), avec ces options Compose et des IDs de run/snapshot/version explicites : préfixe, ingestion/vérification, échantillon, entraînement, scoring, graphe, tests HTTP, extraction SQL et génération réelle.
5. Conserver les sorties, commandes, versions et empreintes. L'override isole les exports dans `exports/reproduction-v1` ; pour une nouvelle campagne, choisir un nouveau dossier hôte pour éviter l'écrasement. Les snapshots métier refusent les chemins existants.
6. Arrêter le projet isolé et redémarrer le principal. Ne lancer aucun `down -v`.

Pour restaurer le principal après cette campagne :

```bash
docker compose -p rncp-bc1-repro-v1 -f docker-compose.yml -f infra/reproduction.yml stop
docker compose -p rncp-bc1-repro-v1 -f docker-compose.yml -f infra/reproduction.yml stop ollama
docker compose up -d --wait --wait-timeout 300
docker compose up -d ollama
docker compose ps
```

La disponibilité après retour doit être observée, jamais déduite de la seule commande. Le journal précise l'état final. Les brokers de test RF3, le second worker et le client Gephi restent des profils optionnels à démarrer séparément.
