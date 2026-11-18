import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import org.apache.hadoop.conf.Configuration;
import org.apache.hadoop.fs.FSDataOutputStream;
import org.apache.hadoop.fs.FileStatus;
import org.apache.hadoop.fs.FileSystem;
import org.apache.hadoop.fs.Path;
import org.apache.hadoop.hdfs.HdfsConfiguration;

/** Écriture/lecture réelles pendant panne ; payloads artificiels identifiés. */
public final class HaContinuityProbe {
  public static void main(String[] args) throws Exception {
    if (args.length != 1 || !args[0].matches("[a-zA-Z0-9_-]{1,80}")) {
      throw new IllegalArgumentException("Un identifiant de run valide est requis");
    }
    String run = args[0];
    java.nio.file.Path control = java.nio.file.Path.of("/control", run);
    Files.createDirectory(control); // Ne remplace aucun essai précédent.
    Configuration conf = new HdfsConfiguration();
    Path directory = new Path("/bc1-ha-probes/" + run);
    int count = 80;
    List<Double> times = new ArrayList<>();
    List<String> chronology = new ArrayList<>();
    try (FileSystem fs = FileSystem.get(conf)) {
      if (fs.exists(directory)) throw new IllegalStateException("Chemin HDFS déjà utilisé");
      fs.mkdirs(directory);
      for (int seq = 0; seq < count; seq++) {
        long started = System.nanoTime();
        long epoch = System.currentTimeMillis();
        byte[] payload = ("BC1_HA_SYNTHETIC_FIXTURE:" + seq + "\n").getBytes(StandardCharsets.UTF_8);
        try (FSDataOutputStream output = fs.create(new Path(directory, String.format("%04d", seq)), false)) {
          output.write(payload);
        }
        double seconds = (System.nanoTime() - started) / 1e9;
        times.add(seconds);
        chronology.add("{\"sequence\":"+seq+",\"started_epoch_ms\":"+epoch+",\"seconds\":"+seconds+"}");
        if (seq == 4) {
          String ready = "{\"event\":\"ha_probe_ready\",\"run_id\":\""+run+"\",\"acknowledged\":5}";
          Files.writeString(control.resolve("ready.json"), ready+"\n");
          System.out.println(ready);
          System.out.flush();
          long deadline = System.nanoTime() + 180_000_000_000L;
          while (!Files.exists(control.resolve("inject-now"))) {
            if (System.nanoTime() > deadline) throw new IllegalStateException("Injection non reçue sous 180 s");
            Thread.sleep(10);
          }
        }
        Thread.sleep(100);
      }
      FileStatus[] files = fs.listStatus(directory);
      if (files.length != count) throw new IllegalStateException("Nombre de fichiers différent des acquittements");
      for (int seq = 0; seq < count; seq++) {
        byte[] expected = ("BC1_HA_SYNTHETIC_FIXTURE:"+seq+"\n").getBytes(StandardCharsets.UTF_8);
        try (var input = fs.open(new Path(directory, String.format("%04d",seq)))) {
          if (!Arrays.equals(expected,input.readAllBytes())) throw new IllegalStateException("Contenu modifié/perdu");
        }
      }
      List<Double> sorted = new ArrayList<>(times);
      sorted.sort(Double::compareTo);
      String report = "{\"event\":\"ha_continuity_verified\",\"run_id\":\""+run+"\",\"synthetic_fixture\":true,"
        +"\"acknowledged\":"+count+",\"unique_files\":"+files.length+",\"data_equal\":true,\"lost_acknowledged\":0,"
        +"\"max_write_seconds\":"+sorted.get(count-1)+",\"p95_write_seconds\":"+sorted.get((int)Math.ceil(.95*count)-1)+","
        +"\"chronology\":["+String.join(",",chronology)+"],\"finished_at\":\""+Instant.now()+"\","
        +"\"scope\":\"process failure on one Docker host; no whole-platform or host-loss guarantee\"}";
      Files.writeString(control.resolve("result.json"),report+"\n");
      System.out.println(report);
    }
  }
}
