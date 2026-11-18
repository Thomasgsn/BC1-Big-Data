// Sauvegarde réelle et restauration dans UNE NOUVELLE base de test, jamais dans fraud.
const fs = require("fs"), cp = require("child_process"), crypto = require("crypto");
const suffix = Date.now().toString();
const directory = "/tmp/bc1-restore-"+suffix;
const targetName = "fraud_restore_test_"+suffix;
fs.mkdirSync(directory, {mode: 0o700});
const uri = "mongodb://bc1owner:"+encodeURIComponent(process.env.MONGO_INITDB_ROOT_PASSWORD)+"@127.0.0.1:27017/?authSource=admin";
const config = directory+"/credentials.yml", archive = directory+"/fraud.archive.gz";
fs.writeFileSync(config, JSON.stringify({uri}), {mode: 0o600});
try {
  for (const [executable, args] of [
    ["mongodump", ["--config", config, "--db", "fraud", "--archive="+archive, "--gzip"]],
    ["mongorestore", ["--config", config, "--archive="+archive, "--gzip", "--nsInclude=fraud.*", "--nsFrom=fraud.*", "--nsTo="+targetName+".*", "--stopOnError"]]
  ]) {
    const result = cp.spawnSync(executable, args, {encoding: "utf8", timeout: 120000});
    if (result.status !== 0) throw new Error(executable+" échoué ; aucun détail d'authentification affiché");
  }
  const connection = new Mongo(uri), source = connection.getDB("fraud"), target = connection.getDB(targetName);
  const evidence = {};
  for (const collection of source.getCollectionNames().sort()) {
    const before = source.getCollection(collection).find().sort({_id: 1}).toArray();
    const after = target.getCollection(collection).find().sort({_id: 1}).toArray();
    const digest = rows => crypto.createHash("sha256").update(EJSON.stringify(rows, {relaxed: false})).digest("hex");
    if (before.length !== after.length || digest(before) !== digest(after)) throw new Error("Contenu restauré différent : "+collection);
    evidence[collection] = {rows: before.length, content_sha256: digest(after),
      indexes_before: source.getCollection(collection).getIndexes().length,
      indexes_after: target.getCollection(collection).getIndexes().length};
    if (evidence[collection].indexes_before !== evidence[collection].indexes_after) throw new Error("Index restaurés différents");
  }
  print(JSON.stringify({event: "mongo_restore_verified", target_database: targetName, original_untouched: true,
    archive_sha256: crypto.createHash("sha256").update(fs.readFileSync(archive)).digest("hex"),
    collections: evidence, scope: "same Mongo process; isolated namespace; not host disaster recovery"}));
} finally {
  fs.unlinkSync(config); // Effacement du secret temporaire créé par ce seul test.
}
