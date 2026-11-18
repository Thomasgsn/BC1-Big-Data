# Contrôles de sécurité et portée

Les profils suivants sont des expériences indépendantes du principal. Ils utilisent des réseaux internes, des volumes propres et aucun port publié. Les secrets sont générés à l'exécution en volumes privés, jamais incorporés aux sources ou aux images. L'arrêt conserve les volumes. Ne pas utiliser `down -v` pour répéter les essais.

| Profil | Démarrage depuis bc1 | Contrôle réel | Limite |
|---|---|---|---|
| HDFS Kerberos | `docker compose -f infra/secure-hdfs/compose.yml up -d --wait` | Alice écrit/relit 1 000 lignes ; sans ticket/Bob sans droits refusés ; SASL privacy ; HTTPS/SPNEGO ; CA/hostname/anonyme refusés | KDC unique, profil distinct de la HA et du principal |
| Kafka mTLS | `docker compose -f infra/secure-kafka/compose.yml up -d --wait` puis `docker compose -f infra/secure-kafka/compose.yml run --rm check` | Préfixe PaySim 1 000 lignes exact sous TLS 1.3 ; clients sans certificat ou sans droits refusés | Un broker, ZooKeeper interne en clair, pas de migration du producteur métier principal |
| Spark RPC | `docker compose -f infra/secure-spark/compose.yml run --rm check` | Calcul distribué exact, secret incorrect refusé, timeout borné | Secret partagé standalone, interface Web interne sans TLS, aucune capture réseau |
| HDFS HA | Voir [hdfs-ha.md](hdfs-ha.md) | Deux sens de bascule et relecture exacte, fencing distinct testé | Authentification simple, un seul hôte |

Pour HDFS, après démarrage utiliser les services `admin`, `alice` et `bob` de `infra/secure-hdfs/compose.yml`, avec `run --rm --no-deps` pour les vérifications après initialisation. Les commandes et preuves précises figurent dans `docs/evidence/p8/secure-hdfs/`. Il faut d'abord construire `rncp-bc1-hadoop:3.4.3-java11`, puis l'image sécurisée et celle HA, dans cet ordre. Les profils réutilisent ces images locales explicitement nommées. L'image sécurisée contient la maintenance JAR décrite ci-dessous, pas le principal.

## Identités et droits

HDFS utilise des keytabs par rôle, des certificats serveur et un cache de tickets temporaire. Alice et Bob ont des identités distinctes et des permissions HDFS testées. Kafka impose les certificats clients, avec principal CN distinct, producer autorisé à écrire le topic ciblé, consumer autorisé à le lire et droits de groupe dédiés. Le certificat intruder est signé par la CA mais ne reçoit aucun droit. L'identité admin et sa clé ne sont pas montées dans le conteneur du test client.

Spark utilise deux configurations privées séparées, dont une contenant un secret incorrect pour le test négatif. Le chiffrement RPC est activé, le repli SASL désactivé et le chiffrement des fichiers locaux activé. L'API principale conserve les jetons hachés, la révocation, les rôles, quotas et contrôles transactionnels déjà testés. Le cloisonnement des profils ne constitue pas une intégration chiffrée de bout en bout du pipeline principal.

Les certificats de laboratoire expirent après 90 jours et les CA après 365 jours. Leur renouvellement n'est pas automatique. Les sauvegardes de volumes d'identité contiennent des secrets et nécessitent chiffrement, contrôle d'accès et rotation en cas d'exposition. Les clés privées ne sont pas des pièces à joindre au dossier du jury.

## Dépendances

Trivy 0.76.2 a scanné OS/JAR de l'image HDFS sécurisée avant/après maintenance : 555 puis 145 correspondances, neuf puis zéro critiques, 34 élevées résiduelles. Ce sont des correspondances de versions, sans démonstration d'exploitabilité. La mise à jour Netty/Bouncy Castle/JSch a été suivie d'une nouvelle vérification fonctionnelle HDFS et des refus. [Résumé](evidence/p8/dependency-scan/summary.json), [analyse](evidence/p8/dependency-scan/assessment.json). Un audit complémentaire des sept images principales est maintenant disponible : [résultats complets](evidence/p8/dependency-scan/platform-summary.json). Les corrections JAR du profil sécurisé ne sont pas appliquées au principal. Aucun risque résiduel n'est déclaré accepté au nom du candidat.

## Sources techniques

- [Hadoop 3.4.3 : mode sécurisé](https://hadoop.apache.org/docs/r3.4.3/hadoop-project-dist/hadoop-common/SecureMode.html).
- [Kafka 3.9 : TLS](https://kafka.apache.org/39/security/encryption-and-authentication-using-ssl/) et [ACL](https://kafka.apache.org/39/security/authorization-and-acls/).
- [Spark 3.5.8 : authentification et chiffrement](https://spark.apache.org/docs/3.5.8/security.html).

Ces choix précis sont des recommandations techniques mises en œuvre pour tester les propriétés de sécurité du référentiel. Les PDF ne sont pas présentés comme imposant ces versions ou chacun de ces mécanismes.

## Audit étendu des images principales

Les sept scans rootfs ont terminé avec le code 0, hors réseau, en réutilisant le cache public du scanner. Aucun volume métier ou secret monté. Les chiffres ci-dessous comptent les correspondances de paquets/versions, parfois répétées entre JAR embarqués, pas des chemins d'exploitation démontrés.

| Image principale | Correspondances | Critiques | Élevées |
|---|---:|---:|---:|
| api | 368 | 2 | 99 |
| spark | 6927 | 89 | 1424 |
| hdfs-main | 542 | 9 | 248 |
| kafka | 206 | 7 | 67 |
| mongo | 155 | 1 | 36 |
| postgres | 586 | 4 | 139 |
| ollama | 54 | 0 | 3 |

La couverture inclut OS et dépendances reconnues par Trivy, avec bases en cache ; elle ne remplace pas une analyse de code ou d'exploitabilité. Le client Gephi, l'image documentaire et toutes les variantes optionnelles n'ont pas reçu ce scan complet. La plateforme reste un laboratoire à ne pas exposer comme service de production. Aucun effacement de finding ni acceptation de risque n'a été effectué.

Deux correspondances critiques de l'API méritent une lecture contextuelle : [Debian CVE-2023-45853](https://security-tracker.debian.org/tracker/CVE-2023-45853) précise que contrib/minizip n'est pas construit dans les binaires zlib de bookworm, ce qui rend cette association de version impropre à une conclusion d'exposition du binaire installé. [Debian CVE-2025-7458](https://security-tracker.debian.org/tracker/CVE-2025-7458) conserve SQLite bookworm vulnérable et décrit un prérequis d'exécution SQL arbitraire. Le code métier utilise PostgreSQL, pas SQLite ; aucun chemin d'exploitation n'est démontré ici. Les résultats bruts sont conservés, sans transformer ces observations en affirmation que toute l'image est sûre.
