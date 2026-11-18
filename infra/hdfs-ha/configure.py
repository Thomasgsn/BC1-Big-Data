"""Configuration locale HA ; aucune identité Kerberos de l'autre profil utilisée."""

import os
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET

folder = Path("/tmp/ha-conf")
folder.mkdir(exist_ok=True, mode=0o755)
for name in ["core-site.xml", "hdfs-site.xml"]:
    shutil.copyfile(Path("/scripts")/name, folder/name)
node = os.environ.get("NODE_ID", "")
if node not in {"", "nn1", "nn2", "jn1", "jn2", "jn3", "dn1", "dn2"}:
    raise ValueError("Nœud HA invalide")
tree = ET.parse(folder/"hdfs-site.xml")
values = {}
if node.startswith("nn"):
    values = {"dfs.ha.namenode.id": node, "dfs.nameservice.id": "bc1-ha"}
if node.startswith("dn"):
    values["dfs.datanode.hostname"] = node
for key, value in values.items():
    item = ET.SubElement(tree.getroot(), "property")
    ET.SubElement(item, "name").text = key
    ET.SubElement(item, "value").text = value
tree.write(folder/"hdfs-site.xml", encoding="utf-8", xml_declaration=True)
(folder/"log4j.properties").write_text(
    "log4j.rootLogger=INFO,console\nlog4j.appender.console=org.apache.log4j.ConsoleAppender\n"
    "log4j.appender.console.target=System.err\nlog4j.appender.console.layout=org.apache.log4j.PatternLayout\n"
    "log4j.appender.console.layout.ConversionPattern=%d{ISO8601} %-5p %c{1}: %m%n\n")
