# Runtime HDFS et migration du principal

## État actuel

Le principal utilise désormais Hadoop 3.4.3 / Temurin 11.0.33 / Ubuntu 24.04.5. L'utilisateur a demandé de reprendre après la proposition de bascule ; nouvelle copie cohérente des volumes dans `rncp-bc1-hadoop-pre-migration-v1`, sources montées en lecture seule. Le contenu existant du `.env` a été conservé et seule la variable publique `COMPOSE_FILE` ajoutée ; permissions 0600. [Journal de déploiement](evidence/p8/hadoop-modern/deployment.json). Les tests ci-dessous décrivent aussi les étapes préparatoires sur l'ancien principal, avant cette bascule.

## Problème constaté

La plateforme principale fonctionne avec l'image Hadoop 3.4.2 épinglée, mais la lecture réelle de `/etc/os-release` et `java -version` révèle CentOS Linux 7 et OpenJDK 1.8.0_212. [CentOS Linux 7 est en fin de vie depuis le 30 juin 2024](https://www.centos.org/centos-linux/). Un digest fige un artefact ; il ne le rend pas maintenu ni exempt de vulnérabilités.

Apache recommande aux utilisateurs de 3.4.2 de passer à [Hadoop 3.4.3](https://hadoop.apache.org/release/). Ce candidat reste dans la branche 3.4 pour limiter les changements ; Hadoop 3.5 existe aussi. [Apache documente Java 11 pour l'exécution de Hadoop 3.3 et ultérieur](https://cwiki.apache.org/confluence/spaces/HADOOP/pages/100827883/Hadoop%2BJava%2BVersions). Aucun changement de technologie imposée par le sujet BC1.

## Candidat concret

`infra/hadoop-modern/Dockerfile` : archive officielle Hadoop 3.4.3, 514 917 037 octets, SHA-512 publié vérifié avant extraction et de nouveau pendant le build. Image [Temurin](https://adoptium.net/installation/containers/) 11 JRE/Ubuntu Noble par digest. Résultat observé : Hadoop 3.4.3, Temurin 11.0.33+10, Ubuntu 24.04.5 LTS, utilisateur UID 1000. Les binaires Hadoop restent en lecture seule pour cet utilisateur ; logs dans `/tmp`. BuildKit monte l'archive sans la conserver dans une couche de l'image finale.

Sources et empreintes : [verrou](../infra/hadoop-modern/lock.json), [journal](evidence/p8/hadoop-modern/experiment.json). Architecture testée : linux/amd64 uniquement. Signature GPG réellement vérifiée avec le fichier KEYS Apache dans un trousseau temporaire : empreinte `38237EE425050285077DB57AD22CF846DBB162A0`, [preuve](evidence/p8/hadoop-modern/signature.json). La clé a été acquise sur le site Apache en HTTPS ; son empreinte n’a pas été authentifiée par un canal indépendant. Aucun trousseau utilisateur global modifié. Audit OS/JAR et sécurité forte encore ouverts. Le bundle AWS SDK absent de cette distribution n'est pas nécessaire au scénario HDFS ; aucun fonctionnement S3A n'est revendiqué.

## Résultats vérifiés le 18 novembre

- Image construite, deux services HDFS sains et safemode OFF ; versions observées ci-dessus.
- Préfixe PaySim de 1 000 lignes écrit/relu, égalité multiensemble et sommes décimales exactes ; même résultat après redémarrage NN/DN.
- Copie du lac principal arrêté proprement : tous les fichiers sources/destinations ont les mêmes empreintes, sources inchangées pendant copie. Un second appel a refusé la destination non vide, code 1 attendu.
- Clone démarré sous 3.4.3 sans `-upgrade`/reformatage : préfixe original 1 000 raw/uniques, zéro rejet et sommes exactes ; 98 813 transactions d'entraînement relues.
- LR et RF rechargées : mêmes SHA des 1 000 scores chacune et même SHA du rapport que le principal ; LR 305 alertes. [Baseline principale](evidence/p8/hadoop-modern/primary-models.json), [résultat clone](evidence/p8/hadoop-modern/clone-models.json).
- Principal rétabli avec Hadoop **3.4.2**, version relue ; candidat neuf et clone arrêtés, volumes conservés. Aucune bascule principale effectuée.

Ces tests couvrent des lectures/écritures et fichiers de modèles réels. Ils ne couvrent pas une reprise Structured Streaming sur les checkpoints clonés, ni la sécurité forte, ni une charge prolongée. La reprise des checkpoints originaux sur le principal a ensuite été exécutée et consignée au journal de déploiement. Ne pas étendre cette preuve à l'ensemble de la plateforme.

## Acquisition et construction

Depuis `bc1/`, conserver les fichiers existants et utiliser l'archive correspondant au verrou :

```bash
mkdir -p tmp/hadoop-modern
curl --fail --location https://downloads.apache.org/hadoop/common/hadoop-3.4.3/hadoop-3.4.3.tar.gz -o tmp/hadoop-modern/hadoop-3.4.3.tar.gz
docker compose -f infra/hadoop-modern/compose.yml build namenode
docker compose -f infra/hadoop-modern/compose.yml up -d --wait --wait-timeout 180
docker compose -f infra/hadoop-modern/compose.yml exec -T namenode hdfs dfsadmin -safemode wait
docker compose -f infra/hadoop-modern/compose.yml run --rm probe
```

L'acquisition télécharge environ 515 Mo ; ne pas écraser une archive déjà vérifiée inutilement. Le build refuse un SHA-512 différent du verrou. Le run `modern-v1` refuse un chemin existant. Pour un nouvel essai, passer un nouvel identifiant à `check_hdfs_runtime.py` ou relire explicitement l'existant.

Le projet isolé n'expose aucun port hôte et possède ses propres volumes. Le test écrit un préfixe réel de 1 000 lignes PaySim en Parquet, compare toutes les lignes et sommes décimales, puis relit après redémarrage NN/DN. Spark est en mode local[2] pour ce test de protocole, pas en cluster distribué. Aucun résultat de disponibilité globale n'en est déduit.

```bash
docker compose -f infra/hadoop-modern/compose.yml restart namenode datanode
docker compose -f infra/hadoop-modern/compose.yml run --rm probe /project/tests/integration/check_hdfs_runtime.py --run-id modern-v1 --read-existing
```

## Validation d'une copie du lac existant

Préparer un **nouveau projet cible**, par exemple `rncp-bc1-hadoop-clone-v1`. `clone.yml` référence les volumes originaux avec `external: true` et les monte **en lecture seule**. `clone.sh` refuse une destination non vide, copie les fichiers, compare les empreintes de tous les fichiers et vérifie que les sources n'ont pas changé.

Arrêter proprement les NN/DN principaux avant la copie. Cette courte indisponibilité est réservée à la copie cohérente ; redémarrer ensuite le principal avec son runtime d'origine avant d'évaluer le clone. Ne jamais exécuter la copie sur une source active ni supprimer une destination pour contourner son refus.

```bash
docker compose stop -t 60 datanode namenode
docker compose -p rncp-bc1-hadoop-clone-v1 -f infra/hadoop-modern/compose.yml -f infra/hadoop-modern/clone.yml run --rm --no-deps clone
docker compose up -d --wait --wait-timeout 180 namenode datanode
docker compose -p rncp-bc1-hadoop-clone-v1 -f infra/hadoop-modern/compose.yml up -d --wait --wait-timeout 180
```

Rapprocher le préfixe `runtime-v1`, relire les modèles LR/RF et comparer leurs empreintes de scores au principal. Cette copie préserve les checkpoints sans les reprendre dans le clone. Leur reprise effective a ensuite été exécutée sur le principal migré, voir `checkpoint-resume.json` au journal de déploiement. Les résultats effectifs sont inscrits au journal ; une procédure écrite n'est pas une preuve exécutée.

## Bascule principale exécutée et exploitation

Fichier prêt à relire : [migration.yml](../infra/hadoop-modern/migration.yml), à superposer à `docker-compose.yml`. Il change uniquement les images des NN/DN/init et emploie les UID/GID numériques de la plateforme existante. Ni nouvelle exposition réseau, ni reformatage, ni modification Kafka/SQL/Mongo/API.

La bascule a été reprise sur instruction utilisateur (« reprend ») en réponse à la demande d’accord. La préparation sur clone ne valait pas autorisation à elle seule. Les prochaines modifications sensibles restent soumises à [AGENTS.md](../AGENTS.md).

La bascule a vérifié l’absence de jobs Spark actifs, arrêté proprement NN/DN, conservé une nouvelle copie cohérente puis démarré avec l’override. Les contrôles des données et modèles sont consignés au journal avant toute reprise de traitement. Les copies préparatoires restent conservées ; la copie supplémentaire prise au moment de la bascule protège les changements survenus depuis ces essais.

La variable publique `COMPOSE_FILE=docker-compose.yml:infra/hadoop-modern/migration.yml` est désormais présente dans la configuration locale, le modèle et le bootstrap. Ainsi les commandes habituelles chargeront les deux fichiers ; une simple relance par défaut ne reviendra pas silencieusement au runtime précédent. Aucun secret n'a besoin d'être changé. Les anciens digests restent comme preuve historique et référence de secours, pas comme runtime actif. En cas d'échec, garder les deux jeux de volumes et revenir à la copie cohérente ; ne pas promettre un simple retour de binaire sur des données éventuellement transformées. Aucun `-upgrade`, `-finalize`, `-rollback` ni `down -v` n'a été exécuté.

Les contrôles Kerberos, chiffrement des transports et HA restent distincts de cette mise à jour du runtime. [Hadoop Secure Mode](https://hadoop.apache.org/docs/r3.4.2/hadoop-project-dist/hadoop-common/SecureMode.html) guide le futur profil ; il ne décrit pas l'état actuel du laboratoire.
