// Jetons HDFS en fichier privé : aucune valeur secrète sur stdout ou dans Git.
import java.nio.file.Files;
import java.nio.file.StandardCopyOption;
import org.apache.hadoop.conf.Configuration;
import org.apache.hadoop.fs.FileSystem;
import org.apache.hadoop.fs.Path;
import org.apache.hadoop.security.Credentials;
import org.apache.hadoop.security.UserGroupInformation;

public final class CredentialBootstrap {
    public static void main(String[] args) throws Exception {
        Configuration configuration = new Configuration();
        UserGroupInformation.setConfiguration(configuration);
        UserGroupInformation user = UserGroupInformation.getLoginUser();
        if (!user.getAuthenticationMethod().equals(UserGroupInformation.AuthenticationMethod.KERBEROS)) {
            throw new IllegalStateException("Kerberos login required, no fallback");
        }
        Credentials credentials = new Credentials();
        try (FileSystem fs = FileSystem.get(configuration)) {
            fs.addDelegationTokens(user.getShortUserName(), credentials);
        }
        if (credentials.numberOfTokens() < 1) throw new IllegalStateException("Missing HDFS delegation token");
        java.nio.file.Path temporary = Files.createTempFile(java.nio.file.Path.of("/tmp"), "bc1-tokens-", ".tmp");
        try {
            Files.setPosixFilePermissions(temporary, java.nio.file.attribute.PosixFilePermissions.fromString("rw-------"));
            credentials.writeTokenStorageFile(new Path(temporary.toUri()), configuration);
            Files.move(temporary, java.nio.file.Path.of("/tmp/hadoop.tokens"), StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);
        } finally { Files.deleteIfExists(temporary); }
        System.out.println("{\"event\":\"hdfs_private_delegation_file_ready\",\"tokens\":" + credentials.numberOfTokens() + "}");
    }
}
