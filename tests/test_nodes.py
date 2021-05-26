from lsif import MetadataNode


def test_metadata_node():
    mt = MetadataNode(projectRoot="./")

    assert mt.version == "0.5.0"
    assert mt.label == "metaData"

    d = mt.to_dictionary()

    assert d["label"] == mt.label
    assert d["version"] == mt.version
