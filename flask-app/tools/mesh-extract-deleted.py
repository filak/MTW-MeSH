import csv
import argparse
import gzip
from tqdm import tqdm
from urllib.parse import urlparse
base_uri = "http://id.nlm.nih.gov/mesh/"


def process_file(filename):
    identifiers = set()
    eng_terms = {}

    with open(filename, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            if row["Language"] == "ENG":
                if row["DescriptorUI"]:
                    identifiers.add(row["DescriptorUI"])
                if row["ConceptUI"]:
                    identifiers.add(row["ConceptUI"])
                # if row["TermUI"]:
                #    identifiers.add(row["TermUI"])

                term_str = row["String"]

                # Add term_str to eng_terms dict for each ID
                for id_key in ["DescriptorUI"]:
                    id_value = row.get(id_key)
                    if id_value:
                        if id_value not in eng_terms:
                            eng_terms[id_value] = []
                        eng_terms[id_value].append(term_str)

    return sorted(identifiers), eng_terms


def query_rdf_stream(rdf_file, identifiers):

    id_uris = set(base_uri + id_ for id_ in identifiers)

    triples = []

    # Count lines for tqdm
    with gzip.open(rdf_file, "rt", encoding="utf-8") as f:
        total_lines = sum(1 for _ in f)

    with gzip.open(rdf_file, "rt", encoding="utf-8") as f:
        for line in tqdm(f, total=total_lines, desc="Processing RDF triples"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # N-Triples format: <subject> <predicate> <object> .
            parts = line.rstrip(" .").split(" ", 2)
            if len(parts) != 3:
                continue
            s, p, o = parts
            s = s.strip("<>")
            p = p.strip("<>")
            o = o.strip("<>") if o.startswith("<") else o.strip('"')

            if s in id_uris:
                # Secure host comparison for RDF predicate (p)
                p_host = urlparse(p).hostname
                if base_uri in p or p.startswith("http://www.w3.org"):
                    triples.append((s, p, o))

    return triples


def mark_obsolete(triples, eng_terms):
    lookup_uri = []
    lookup_terms = {}

    for uid, terms in eng_terms.items():
        uri = base_uri + uid
        lookup_uri.append(uri)
        if uri not in lookup_terms:
            lookup_terms[uri] = [f'{term}"@en' for term in terms]

    updated_count = 0
    for i, (s, p, o) in enumerate(triples):
        if s in lookup_uri and o in lookup_terms.get(s):
            if not o.startswith("[OBSOLETE] "):
                triples[i] = (s, p, f"[OBSOLETE] {o}")
                updated_count += 1

    print(f"Updated {updated_count} triples with [OBSOLETE] label.")


def add_inactive_triples(triples, identifiers):
    active_predicate = "http://id.nlm.nih.gov/mesh/vocab#active"
    xsd_boolean = "<http://www.w3.org/2001/XMLSchema#boolean>"

    for identifier in identifiers:
        subject = f"{base_uri}{identifier}"
        obj = f'false"^^{xsd_boolean}'
        triples.append((subject, active_predicate, obj))


def main():
    parser = argparse.ArgumentParser(
        description="Extract inactive items from your MeSH RDF backup dataset"
    )
    parser.add_argument(
        "meshrdf", help="Path to the gzipped MeSH RDF N-Triples dataset"
    )
    parser.add_argument("deleted", help="Path to the deleted_mh.txt TSV file")
    parser.add_argument("--out", help="Output file", default="mesh_inactive_new.nt")
    args = parser.parse_args()

    identifiers, eng_terms = process_file(args.deleted)
    print("Total inactive identifiers found:", len(identifiers))

    triples = query_rdf_stream(args.meshrdf, identifiers)
    print(f"Found {len(triples)} triples.\n")

    print("Obsolete terms count:", len(eng_terms))
    mark_obsolete(triples, eng_terms)

    add_inactive_triples(triples, identifiers)

    # Show a preview
    # for t in sorted(triples_sorted[:30]):
    #    print(t)

    # Sort triples by subject, predicate, object
    triples_sorted = sorted(triples)

    with open(args.out, "w", encoding="utf-8") as f_out:
        for s, p, o in triples_sorted:
            # Subject and predicate always wrapped in <>
            s_out = f"<{s}>"
            p_out = f"<{p}>"

            # Decide how to format the object
            if o.startswith(base_uri):
                # Object is a URI
                o_out = f"<{o}>"
            elif o.endswith("@en") or "^^" in o:
                # Object already has language tag or datatype
                o_out = f'"{o}'
            else:
                # Plain literal
                o_out = f'"{o}"'

            f_out.write(f"{s_out} {p_out} {o_out} .\n")

    print(f"Saved {len(triples_sorted)} triples to {args.out}")


if __name__ == "__main__":
    main()
