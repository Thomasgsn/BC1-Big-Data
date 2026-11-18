# Préparation au jury BC1

Document de travail : chaîne réellement exécutée et reproduite sur volumes métier neufs, captures Gephi et rapport technique disponibles. La répétition orale chronométrée et le support final restent à produire. La validation officielle appartient au jury.

## Choix à savoir défendre

| Composant | Rôle / choix / alternative | Avantages et limites à expliquer | Preuve à produire |
|---|---|---|---|
| Kafka et ZooKeeper | Buffer, rejeu et coordination imposée par sujet ; KRaft comme alternative à faire accepter | Découplage et partitions ; coût d'exploitation, rétention et compatibilité versions | Offsets, reprise, partitions et panne broker, ACL |
| Spark | Traitement distribué, SQL et MLlib ; DStreams ou autre moteur comme alternatives | Un socle commun ; micro-batch, mémoire JVM, limites du continu | Jobs, métriques, fenêtres et reprise driver |
| HDFS/Parquet | Lac distribué et données canoniques ; stockage objet comme alternative conceptuelle | Schéma colonne et réplication ; NameNode critique, petits fichiers, sécurité | Fichiers, schémas, droits, compaction et bascule réelle |
| MongoDB | Data Lab et textes d'explication ; Cassandra alternative | Souplesse des documents et index ; duplication possible et cohérence multi-sinks | Upsert, requêtes, documents et export Gephi |
| PostgreSQL | Relationnel du référentiel, dossiers et décisions ; MySQL alternative | Normalisation, intégrité et transactions ; administration supplémentaire | Modèle, contraintes, charge et restauration |
| API FastAPI | Interopérabilité, accès contrôlé et OpenAPI ; Flask alternative | Contrats typés et tests ; quotas/auth à gérer, pas de HA implicite | Appels autorisés/refusés, pagination et 429 |
| Gephi | Exploration visuelle de graphe ; calcul serveur complémentaire | Degré et communautés interprétables ; limites mémoire et biais d'échantillonnage | Export Mongo, paramètres, captures et commentaire |
| MLlib | Détection comparée régression logistique/RF | Interprétabilité/coût contre non-linéarité ; déséquilibre et fuite | Modèles rechargés, jeu indépendant et métriques complètes |
| LLM | Reformulation de faits et brouillon ; API externe ou local | Compréhension métier ; hallucinations, latence, ressources et coût | Appel réel, contexte, sortie et revue qualité |
| Compose | Reproduction locale ; orchestration multi-hôte alternative | Simplicité ; ne protège pas contre la panne de la machine | Installation refaite, volumes et limites explicites |

Pour chaque décision, compléter après réalisation : configuration exacte, sécurité appliquée, latence/ressources observées, maintenance, incident testé et lien de preuve. Ne pas apprendre des résultats qui n'ont pas été mesurés.

## Scénario de démonstration envisagé

1. Exposer le besoin métier, le caractère synthétique de PaySim, l'architecture et la matrice.
2. Présenter les versions, le manifeste dataset et les services réellement sains.
3. Rejouer une période bornée ; retrouver un identifiant Kafka dans le Parquet HDFS puis ses agrégats MongoDB.
4. Montrer un rejet typé et expliquer la cohérence des comptages et montants.
5. Consulter l'API, démontrer une lecture autorisée et une écriture refusée ; saisir une décision analyste et la retrouver dans le lac via JDBC.
6. Importer un export Mongo dans Gephi ; présenter degré et modularité avec limites d'interprétation.
7. Comparer les deux modèles avec AUC, rappel, matrice et seuil, expliquer le découpage et les faux positifs.
8. Retrouver une alerte réelle du modèle, générer l'explication et le brouillon via le LLM ; montrer les motifs factuels et l'absence d'envoi.
9. Démontrer une reprise et, si le profil le permet, une vraie bascule ; préciser exactement le domaine de panne couvert.
10. Présenter performances, limites, écarts ouverts et reproductibilité.

La durée et les transactions retenues seront fixées après une répétition réelle. Une vidéo préenregistrée doit être identifiée comme telle. Aucun écran fictif ne remplace une preuve de fonctionnement.

## Réponses appuyées sur les exécutions

**Pourquoi PostgreSQL en plus de Mongo ?** Le sujet pédagogique demande un Data Lab NoSQL ; C1.1 du référentiel évalue aussi le relationnel. PostgreSQL conserve dossiers, décisions immuables et audit avec contraintes et transactions. Mongo sert les agrégats, scores, graphes et textes. Le snapshot JDBC prouve leur intégration, sans transaction distribuée entre ces bases.

**Quelles sources distinctes ?** PaySim synthétique et registre SQL d'investigation. Le premier snapshot SQL contient deux décisions, celui de reproduction quatre, toutes `automated_test`. Elles prouvent le mécanisme logiciel, pas une consultation d'analystes ni une source bancaire indépendante. L'adéquation pédagogique de la variété doit être confirmée.

**Que signifient les horloges ?** `step` représente une heure simulée ; `event_time` part arbitrairement du 1er janvier 2000 UTC. `emitted_at` est l'heure réelle de rejeu, et `ingested_at` le timestamp Spark du batch. La p95 8,28 s du flux permanent exclut le commit/visibilité. Les 61 s ou 303 s des rejeux bornés incluent l'attente du consommateur et ne sont pas des mesures comparables de capacité.

**Que garantit le checkpoint ?** La progression d'une requête Structured Streaming et son état. Il ne crée pas une transaction commune aux sinks. Les IDs stables, upserts et rapprochements permettent une reprise contrôlée. L'essai a retrouvé 2 003 bruts, 1 000 uniques et trois rejets ; un checkpoint absent/corrompu reste un scénario à approfondir.

**Pourquoi ne pas utiliser l'accuracy ?** Toujours prédire non-fraude donne 99,65 % d'accuracy et aucun rappel. LR obtient 55,22 % de rappel mais seulement 3,80 % de précision : 37 vrais positifs et 937 faux positifs sur test. Ce coût d'investigation interdit de présenter le modèle comme prêt pour la banque.

**Comment éviter une fuite ?** Soldes PaySim, `isFlaggedFraud`, labels et comptes exclus des prédicteurs. Découpage par steps complets, transformations/poids appris sur train, seuil et modèle choisis sur validation. Test conservé séparé ; la RF a une meilleure PR-AUC test mais ne remplace pas après coup le gagnant choisi sur validation.

**Une modularité de 0,995408 prouve-t-elle du blanchiment ?** Non. Les 597 communautés correspondent ici aux 597 composantes déconnectées ; une formule indépendante retrouve le résultat. Le graphe provient d'un préfixe de 1 000 transactions. Le hub de degré entrant 23 est un compte synthétique, sans preuve de réseau frauduleux. Captures et paramètres dans [gephi.md](gephi.md).

**Que peut expliquer le LLM ?** Il reformule des faits et la plus forte contribution positive agrégée du modèle LR, après vérification additive du logit. La référence algébrique est le vecteur nul, pas un client typique. Cela n'établit aucune cause de fraude. Deux contextes séparés, sortie validée ou rejetée, score non calibré, revue humaine obligatoire. Un texte conserve une coquille ; les limites sémantiques ne sont pas cachées.

**Qu'a-t-on réellement rendu disponible ?** Sur un topic isolé RF3/ISR2, 220 messages ont été acquittés et relus sans perte/doublon observé lors de l'arrêt du leader, puis trois ISR retrouvés. Le principal et l'hôte restent uniques ; SQL/Mongo/API n'ont pas de bascule globale. Les restaurations sur le même hôte ne sont pas une reprise après sinistre.

**Quel incident a été rencontré au retour du principal ?** Kafka a refusé l'enregistrement d'un ID encore associé à une session restaurée ZooKeeper (`NodeExists`). L'expiration automatique puis l'absence du nœud ont été observées ; relance réussie, sans suppression ni changement de configuration. Le premier `up` a bien échoué, le protocole ne masque pas ce fait.

**Quelle sécurité est prouvée ?** Tokens hachés/révocables, rôles/quotas, refus SQL/Mongo, API non root/read-only et montages limités. Audit Python et correctif kafka-python vérifiés ; pas d'audit OS/JAR complet. HDFS simple, Kafka/Spark non authentifiés et absence de TLS restent des écarts ouverts, pas des contrôles déjà acquis. L’image HDFS initiale contient CentOS 7/Java 8u212 ; un runtime Hadoop 3.4.3/Java 11 a été testé sur clone puis déployé, après reprise demandée et nouvelle copie cohérente. Il ne remplace pas les contrôles d’authentification/chiffrement encore ouverts.

**Qu'a-t-on reproduit ?** L'état métier depuis de nouveaux volumes, en réutilisant les images, le CSV et les poids acquis. Même découpage/sélection/métriques ML et mêmes SHA CSV de graphe ; API, snapshot SQL et LLM exécutés. Ce n'est pas une installation sur machine vierge. [Journal réel](evidence/p9/reproduction.json).

## Questions à répéter à l'oral

- Pourquoi une base SQL alors que le sujet cite MongoDB ? Comment prouver C1.1 ?
- Quelles sources sont réellement distinctes ? Quelle provenance pour les décisions ?
- Quelle différence entre `event_time`, `emitted_at`, heure simulée et minute de rejeu ?
- Que garantit le checkpoint, et que se passe-t-il entre deux écritures dans des sinks différents ?
- Pourquoi un rappel élevé peut-il être insuffisant ? Quel coût métier aux faux positifs ?
- Les variables existaient-elles au moment de la décision ? Comment éviter les fuites ?
- Une communauté Gephi prouve-t-elle du blanchiment ? Comment l'échantillonnage biaise-t-il les centralités ?
- Comment empêcher le LLM d'inventer une cause, une identité ou une action bancaire ?
- Quelle panne a été testée ? Plusieurs conteneurs sur un hôte sont-ils indépendants ?
- Quels contrôles de sécurité ont été exécutés, et lesquels restent manquants ?

Anglais technique, REF p. 25 : préparer un glossaire et pouvoir expliquer `checkpoint`, `watermark`, `replication factor`, `failover`, `data leakage`, `recall`, `false positive` et `least privilege`. Les modalités et la langue exactes de l'épreuve doivent être confirmées par l'école.

## Rapport et livrables à finaliser

Le [rapport technique](technical-report.md) couvre déjà le contexte et les exigences ; sources et qualité ; architecture et décisions ; réalisation et sécurité ; modèles/graphes/GenAI ; tests et performances ; résilience ; limites ; reproduction ; contributions ; index des preuves. Le sujet BC1 ne fixe pas de nombre de pages : ne pas importer les 10–15 pages du sujet BC3. Le format final, le délai et les modalités du binôme restent à confirmer.

## Support disponible et contributions

[Présentation PDF](../output/pdf/soutenance-bc1.pdf), [rapport PDF](../output/pdf/rapport-technique-bc1.pdf), sources modifiables `presentation.json` et `technical-report.md`. Thomas Gassmann travaille seul, avec assistance Codex pour l’ingénierie et les contrôles. Échéance non communiquée. Aucun jury ou entretien métier n’est simulé.

Les réponses historiques ci-dessus sont complétées par les nouveaux essais : [sécurité par profils](security-profiles.md), [HDFS HA](hdfs-ha.md), [préconditions de checkpoint](evidence/p3/checkpoint-preflight.json). HDFS fort, Kafka mTLS/ACL et Spark authentifié sont vérifiés séparément ; le principal conserve ses limites. La répétition orale doit être réalisée par le candidat.

## Parcours technique réellement exécuté

Le [journal de démonstration](evidence/p9/demonstration.json) retrace le run neuf `jury-20261118-v1`. Préfixe, sommes, graphe et scoring réussis, premier timeout LLM conservé puis génération réelle persistée. Les modèles étaient préparés à l’avance. La durée observée 1 600,667 s comprend des pauses/audits/reprise et ne doit pas être citée comme durée d’oral. Répéter humainement le support de douze pages, en montrant les commandes et preuves, reste nécessaire.
