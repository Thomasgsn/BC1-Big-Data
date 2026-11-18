package fr.rncp.bc1;

import java.awt.Color;
import java.io.StringReader;
import java.awt.image.BufferedImage;
import javax.imageio.ImageIO;
import java.nio.file.*;
import java.util.*;
import java.util.stream.Collectors;
import org.gephi.graph.api.*;
import org.gephi.io.exporter.api.ExportController;
import org.gephi.layout.plugin.force.StepDisplacement;
import org.gephi.layout.plugin.force.yifanHu.YifanHuLayout;
import org.gephi.preview.api.*;
import org.gephi.project.api.ProjectController;
import org.gephi.statistics.plugin.Modularity;
import org.openide.util.Lookup;
import org.apache.batik.transcoder.TranscoderInput;
import org.apache.batik.transcoder.TranscoderOutput;
import org.apache.batik.transcoder.image.ImageTranscoder;

/** Analyse réelle par le moteur Gephi ; aucun rendu ne constitue une capture de son interface. */
public final class NetworkAnalysis {
    public static void main(String[] args) throws Exception {
        if (args.length != 2) throw new IllegalArgumentException("Dossiers CSV source et résultat requis");
        Path input = Path.of(args[0]), output = Path.of(args[1]);
        if (Files.exists(output)) throw new IllegalArgumentException("Le résultat existe déjà ; choisir une nouvelle version");
        Lookup.getDefault().lookup(ProjectController.class).newProject();
        GraphModel model = Lookup.getDefault().lookup(GraphController.class).getGraphModel();
        DirectedGraph graph = model.getDirectedGraph();
        model.getNodeTable().addColumn("in_degree", Integer.class);
        model.getNodeTable().addColumn("out_degree", Integer.class);
        model.getEdgeTable().addColumn("transaction_edge_id", String.class);
        model.getEdgeTable().addColumn("total_amount_exact", String.class);
        // Contrat volontairement restreint aux CSV produits par graph_export (identifiants alphanumériques).
        List<String> nodes = Files.readAllLines(input.resolve("nodes.csv"));
        if (!nodes.get(0).equals("Id,Label")) throw new IllegalArgumentException("Entête nœuds invalide");
        Random positions = new Random(42);
        for (String line : nodes.subList(1, nodes.size())) {
            String[] fields = line.split(",", -1);
            if (fields.length != 2 || !fields[0].matches("[A-Za-z0-9]+") || !fields[1].equals(fields[0]))
                throw new IllegalArgumentException("Nœud hors contrat CSV");
            Node node = model.factory().newNode(fields[0]);
            node.setLabel(fields[1]); node.setX(positions.nextFloat()*1000); node.setY(positions.nextFloat()*1000);
            if (!graph.addNode(node)) throw new IllegalArgumentException("Nœud dupliqué");
        }
        List<String> edges = Files.readAllLines(input.resolve("edges.csv"));
        if (!edges.get(0).equals("Id,Source,Target,Type,Weight,TotalAmount")) throw new IllegalArgumentException("Entête arêtes invalide");
        Set<String> identifiers = new HashSet<>();
        for (String line : edges.subList(1, edges.size())) {
            String[] f = line.split(",", -1);
            if (f.length != 6 || !f[0].matches("[a-f0-9]{64}") || !identifiers.add(f[0]) || !f[3].equals("Directed"))
                throw new IllegalArgumentException("Arête hors contrat CSV");
            Node source = graph.getNode(f[1]), target = graph.getNode(f[2]);
            long weight = Long.parseLong(f[4]);
            if (source == null || target == null || weight <= 0 || new java.math.BigDecimal(f[5]).signum() < 0)
                throw new IllegalArgumentException("Arête sans extrémité ou poids invalide");
            Edge edge = model.factory().newEdge(source, target, 0, (double)weight, true);
            edge.setAttribute("transaction_edge_id", f[0]); edge.setAttribute("total_amount_exact", f[5]);
            graph.addEdge(edge);
        }
        int nodeCount = graph.getNodeCount(), edgeCount = graph.getEdgeCount();
        if (nodeCount != nodes.size()-1 || edgeCount != edges.size()-1) throw new AssertionError("Import incomplet");
        Modularity modularity = new Modularity();
        modularity.setRandom(false); modularity.setUseWeight(true); modularity.setResolution(1.0);
        modularity.execute(model); // Gephi utilise ici sa projection non orientée.
        Set<Integer> communities = new HashSet<>();
        List<Node> ranked = new ArrayList<>(Arrays.asList(graph.getNodes().toArray()));
        for (Node node : ranked) {
            int community = ((Number)node.getAttribute(Modularity.MODULARITY_CLASS)).intValue();
            communities.add(community);
            node.setAttribute("in_degree", graph.getInDegree(node)); node.setAttribute("out_degree", graph.getOutDegree(node));
            node.setSize((float)(3 + 3*Math.sqrt(graph.getDegree(node))));
            node.setColor(Color.getHSBColor((float)((community*0.61803398875)%1), .65f, .8f));
        }
        ranked.sort(Comparator.<Node>comparingInt(graph::getDegree).reversed().thenComparing(n -> n.getId().toString()));
        StringBuilder degrees = new StringBuilder("id,in_degree,out_degree,total_degree,modularity_class\n");
        for (Node node : ranked) degrees.append(node.getId()).append(',').append(graph.getInDegree(node)).append(',')
            .append(graph.getOutDegree(node)).append(',').append(graph.getDegree(node)).append(',')
            .append(node.getAttribute(Modularity.MODULARITY_CLASS)).append('\n');
        Set<Node> seen = new HashSet<>(); List<List<Node>> components = new ArrayList<>();
        for (Node start : ranked) {
            if (!seen.add(start)) continue;
            ArrayDeque<Node> queue = new ArrayDeque<>(); List<Node> component = new ArrayList<>(); queue.add(start);
            while (!queue.isEmpty()) {
                Node current = queue.remove(); component.add(current);
                for (Node neighbor : graph.getNeighbors(current)) if (seen.add(neighbor)) queue.add(neighbor);
            }
            components.add(component);
        }
        components.sort(Comparator.<List<Node>>comparingInt(List::size).reversed()
            .thenComparing(c -> c.stream().map(n -> n.getId().toString()).min(String::compareTo).orElse("")));
        Files.createDirectories(output);
        Files.writeString(output.resolve("degrees.csv"), degrees);
        ExportController exporter = Lookup.getDefault().lookup(ExportController.class);
        exporter.exportFile(output.resolve("full-network.gexf").toFile());
        Set<Node> visible = components.stream().limit(5).flatMap(Collection::stream).collect(Collectors.toSet());
        for (Node node : graph.getNodes().toArray()) if (!visible.contains(node)) graph.removeNode(node);
        YifanHuLayout layout = new YifanHuLayout(null, new StepDisplacement(1f));
        layout.setGraphModel(model); layout.resetPropertiesValues(); layout.setOptimalDistance(200f); layout.initAlgo();
        for (int i = 0; i < 200 && layout.canAlgo(); i++) layout.goAlgo();
        layout.endAlgo();
        // Ranger les composantes indépendantes pour éviter un rendu dominé par l'espace vide.
        // Translation/échelle seulement : les arêtes et appartenances restent inchangées.
        for (int index = 0; index < Math.min(5, components.size()); index++) {
            List<Node> component = components.get(index);
            double cx = component.stream().mapToDouble(Node::x).average().orElseThrow();
            double cy = component.stream().mapToDouble(Node::y).average().orElseThrow();
            double radius = component.stream().mapToDouble(n -> Math.hypot(n.x()-cx, n.y()-cy)).max().orElse(1);
            for (Node node : component) {
                node.setX((float)((node.x()-cx)*200/Math.max(1, radius)+(index%2)*650));
                node.setY((float)((node.y()-cy)*200/Math.max(1, radius)+(index/2)*600));
                if (graph.getDegree(node) < 5) node.setLabel("");
            }
        }
        PreviewModel preview = Lookup.getDefault().lookup(PreviewController.class).getModel();
        preview.getProperties().putValue(PreviewProperty.SHOW_NODE_LABELS, true);
        preview.getProperties().putValue(PreviewProperty.EDGE_CURVED, false);
        preview.getProperties().putValue(PreviewProperty.BACKGROUND_COLOR, Color.WHITE);
        exporter.exportFile(output.resolve("largest-five-components.svg").toFile());
        // Rasterisation du SVG Gephi avec Batik, sans écran ni PNGExporter dépendant du desktop.
        ImageTranscoder raster = new ImageTranscoder() {
            public BufferedImage createImage(int width, int height) {
                BufferedImage image = new BufferedImage(width, height, BufferedImage.TYPE_INT_RGB);
                var graphics = image.createGraphics();
                graphics.setColor(Color.WHITE); graphics.fillRect(0, 0, width, height); graphics.dispose();
                return image;
            }
            public void writeImage(BufferedImage image, TranscoderOutput destination)
                    throws org.apache.batik.transcoder.TranscoderException {
                try {
                    if (!ImageIO.write(image, "png", destination.getOutputStream())) throw new java.io.IOException("Codec PNG absent");
                } catch (java.io.IOException error) { throw new org.apache.batik.transcoder.TranscoderException(error); }
            }
        };
        raster.addTranscodingHint(ImageTranscoder.KEY_WIDTH, 1800f);
        String svg = Files.readString(output.resolve("largest-five-components.svg")).replaceAll("(?s)<!DOCTYPE.*?>", "");
        try (var stream = Files.newOutputStream(output.resolve("largest-five-components.png"))) {
            raster.transcode(new TranscoderInput(new StringReader(svg)), new TranscoderOutput(stream));
        }
        String sizes = components.stream().map(c -> Integer.toString(c.size())).collect(Collectors.joining(","));
        String report = String.format(Locale.ROOT,
            "{\"engine\":\"Gephi Toolkit 0.11.4\",\"nodes\":%d,\"directed_edges\":%d,\"modularity\":%.12f,\"communities\":%d,\"modularity_projection\":\"undirected_weighted\",\"resolution\":1.0,\"randomize\":false,\"weak_components\":%d,\"component_sizes\":[%s],\"render_filter\":\"largest five weak components\",\"render_nodes\":%d,\"render_edges\":%d,\"is_desktop_screenshot\":false,\"fraud_conclusion\":\"none\"}\n",
            nodeCount, edgeCount, modularity.getModularity(), communities.size(), components.size(), sizes, graph.getNodeCount(), graph.getEdgeCount());
        Files.writeString(output.resolve("report.json"), report); System.out.println(report);
        ProjectController projects = Lookup.getDefault().lookup(ProjectController.class);
        projects.renameWorkspace(projects.getCurrentWorkspace(), "PaySim synthétique - cinq composantes - degré et modularité");
        projects.saveProject(projects.getCurrentProject(), output.resolve("five-components.gephi").toFile());
    }
}
