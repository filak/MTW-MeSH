from SPARQLWrapper import SPARQLWrapper, TURTLE, JSON
import time
from pathlib import Path
from tqdm import tqdm


def fetch_construct_graph(endpoint_url, base_query, limit=100, offset=0):
    # Modify the base query to add LIMIT and OFFSET
    paginated_query = f"{base_query.strip()}\nLIMIT {limit} OFFSET {offset}"

    sparql = SPARQLWrapper(endpoint_url)
    sparql.setQuery(paginated_query)
    sparql.setReturnFormat(TURTLE)

    try:
        result = sparql.query().convert()
        return result.decode("utf-8") if isinstance(result, bytes) else result
    except Exception as e:
        print(f"Error fetching data at offset {offset}: {e}")
        return None


def count_matching_triples(endpoint_url):
    count_query = """
    PREFIX meshv: <http://id.nlm.nih.gov/mesh/vocab#>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

    SELECT (COUNT(*) AS ?tripleCount)
    WHERE {
      ?s meshv:active "false"^^xsd:boolean .
      ?s ?p ?o .
    }
    """

    sparql = SPARQLWrapper(endpoint_url)
    sparql.setQuery(count_query)
    sparql.setReturnFormat(JSON)

    try:
        result = sparql.query().convert()
        count_str = result["results"]["bindings"][0]["tripleCount"]["value"]
        return int(count_str)
    except Exception as e:
        print(f"Error fetching triple count: {e}")
        return None


def retrieve_all_rdf(
    endpoint, query, output_file, total_triples=None, limit=100, delay=1.0
):
    offset = 0
    total_fetched = 0

    with open(output_file, "w", encoding="utf-8") as f, tqdm(
        total=total_triples or 1, unit="triple", dynamic_ncols=True
    ) as pbar:

        while True:
            rdf_chunk = fetch_construct_graph(
                endpoint, query, limit=limit, offset=offset
            )

            if not rdf_chunk or len(rdf_chunk.strip()) == 0:
                print("No more data to fetch.")
                break

            f.write(rdf_chunk + "\n")
            f.flush()

            # Count the number of newlines (triples) to track progress
            lines_fetched = rdf_chunk.count("\n")
            total_fetched += lines_fetched
            pbar.update(lines_fetched)

            offset += limit
            time.sleep(delay)

    print(f"\nFinished. Total triples written: {total_fetched}")


if __name__ == "__main__":
    endpoint_url = "https://id.nlm.nih.gov/mesh/sparql"
    script_dir = Path(__file__).resolve().parent

    output_file_path = script_dir / "mesh_inactive.ttl"

    sparql_query = """
    PREFIX meshv:  <http://id.nlm.nih.gov/mesh/vocab#>
    PREFIX xsd:  <http://www.w3.org/2001/XMLSchema#>

    CONSTRUCT {
        ?s ?p ?o
    }
    WHERE {
    ?s meshv:active "false"^^xsd:boolean .
    ?s ?p ?o .
    }
    """

    proceed = (
        input(
            f"Query & download the inactive MeSH triples from {endpoint_url} ? (y/n):  "
        )
        .strip()
        .lower()
    )
    if proceed not in ("y", "yes"):
        print("Aborted.")
    else:
        print("Counting total triples...")
        total = count_matching_triples(endpoint_url)

        if total is not None:
            print(f"Total matching triples: {total}")
        else:
            print("Proceeding without total count...")

        retrieve_all_rdf(
            endpoint_url,
            sparql_query,
            output_file_path,
            total_triples=total,
            limit=1000,
        )
