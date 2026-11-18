"""Préconditions de reprise : ne jamais recréer silencieusement un état perdu."""

import json
import uuid


def guard_streaming_state(spark, root: str) -> None:
    """Contrôler tous les sinks avant lancement ; Spark valide ensuite offsets/état.

    Une reconstruction après perte de checkpoint doit utiliser un nouveau run,
    puis un rapprochement explicite. Ce contrôle ne répare aucun checkpoint.
    """
    jvm = spark._jvm
    configuration = spark._jsc.hadoopConfiguration()
    for name in ("raw", "curated", "quarantine", "metrics"):
        output = jvm.org.apache.hadoop.fs.Path(root + "/" + name)
        checkpoint = jvm.org.apache.hadoop.fs.Path(root + "/checkpoints/" + name)
        fs = output.getFileSystem(configuration)
        metadata = jvm.org.apache.hadoop.fs.Path(checkpoint, "metadata")
        populated = fs.exists(output) and bool(fs.listStatus(output))
        if not fs.exists(metadata):
            if populated or (fs.exists(checkpoint) and bool(fs.listStatus(checkpoint))):
                raise RuntimeError(f"Checkpoint {name} absent/incomplet : reprise refusée ; restaurer l'état cohérent ou créer un nouveau run.")
            continue
        if fs.getFileStatus(metadata).getLen() > 8192:
            raise RuntimeError(f"Métadonnées checkpoint {name} trop grandes : reprise refusée.")
        reader = jvm.java.io.BufferedReader(jvm.java.io.InputStreamReader(fs.open(metadata), "UTF-8"))
        try:
            lines = []
            while True:
                line = reader.readLine()
                if line is None:
                    break
                lines.append(line)
            value = json.loads("\n".join(lines))
            uuid.UUID(value["id"])
        except (ValueError, KeyError, TypeError) as error:
            raise RuntimeError(f"Métadonnées checkpoint {name} corrompues : reprise refusée.") from error
        finally:
            reader.close()
