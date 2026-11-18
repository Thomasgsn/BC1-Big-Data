// Appelé par mongosh --nodb ; le mot de passe ne figure pas dans les arguments.
const snapshot = process.env.BC1_SNAPSHOT_ID;
if (!snapshot || !/^[a-zA-Z0-9_-]{1,150}$/.test(snapshot)) throw new Error("Snapshot invalide");
const password = process.env.MONGO_APP_PASSWORD;
if (!password) throw new Error("Identité applicative requise");
const mongo = new Mongo("mongodb://bc1app:" + encodeURIComponent(password) + "@127.0.0.1:27017/fraud?authSource=fraud");
const fraud = mongo.getDB("fraud");
const metadata = fraud.graph_snapshots.findOne({_id: snapshot, status: "complete"});
if (!metadata) throw new Error("Snapshot complet introuvable");
const nodes = fraud.graph_nodes.find({snapshot_id: snapshot}).limit(100001).toArray();
const edges = fraud.graph_edges.find({snapshot_id: snapshot}).limit(50001).toArray();
if (nodes.length > 100000 || edges.length > 50000) throw new Error("Fenêtre trop grande");
if (nodes.length !== Number(metadata.nodes) || edges.length !== Number(metadata.edges)) throw new Error("Comptages incohérents");
const output = {snapshot_id: snapshot, origin: "MongoDB Data Lab", nodes: nodes.map(n => ({node_id: n.node_id})),
  edges: edges.map(e => ({edge_id: e._id, source: e.source, target: e.target,
    transaction_count: Number(e.transaction_count), total_amount: e.total_amount.toString()}))};
if (process.env.BC1_EXPORT_FILE) {
  const path = "/exports/mongo/" + snapshot + ".json";
  if (process.env.BC1_EXPORT_FILE !== path) throw new Error("Chemin d'export refusé");
  const fs = require("fs");
  fs.mkdirSync("/exports/mongo", {recursive: true});
  fs.writeFileSync(path, JSON.stringify(output), {flag: "wx", mode: 0o600});
  print(JSON.stringify({event: "mongodb_graph_exported", snapshot_id: snapshot, nodes: nodes.length, edges: edges.length}));
} else {
  print(JSON.stringify(output));
}
