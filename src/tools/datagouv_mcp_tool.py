import json
import urllib.request
import urllib.parse
import urllib.error


class Tools:
    def search_data_gouv_datasets(self, query: str) -> str:
        """
        DESCRIPTION: Use this tool to automatically search for public data, statistics, or files on data.gouv.fr.

        Args:
            query: Search keywords (e.g., “water quality testing”).
        """
        url = f"https://www.data.gouv.fr/api/1/datasets/?q={urllib.parse.quote(query)}&page_size=5"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "OpenWebUI-Agent"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                results = []
                for item in data.get("data", []):
                    results.append(f"ID Dataset: {item['id']} | Titre: {item['title']}")
                return (
                    "\n".join(results)
                    if results
                    else "Aucun résultat trouvé sur Data.gouv."
                )
        except Exception as e:
            return f"Erreur de recherche: {e}"

    def list_dataset_files(self, dataset_id: str) -> str:
        """
        Lists the CSV or text files in a dataset. Must be used after retrieving the dataset ID.

        Args:
            dataset_id: The identifier (dataset ID) of the dataset retrieved during the search.
        """
        url = (
            f"https://www.data.gouv.fr/api/1/datasets/{urllib.parse.quote(dataset_id)}/"
        )
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "OpenWebUI-Agent"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                resources = []
                for res in data.get("resources", []):
                    resources.append(
                        f"URL: {res['url']} | Format: {res.get('format', 'inconnu')} | Titre: {res['title']}"
                    )
                return (
                    "\n".join(resources)
                    if resources
                    else "Aucun fichier trouvé dans ce dataset."
                )
        except Exception as e:
            return f"Erreur lors de la récupération des fichiers: {e}"

    def read_file_content(self, file_url: str) -> str:
        """
        Reads the text content or raw data (the first few lines) from a CSV or text file.

        Args:
            file_url: The exact URL of the file to read (retrieved using the list_dataset_files tool).
        """
        try:
            req = urllib.request.Request(
                file_url, headers={"User-Agent": "OpenWebUI-Agent"}
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                content = resp.read(4000).decode("utf-8", errors="replace")
                return content + "\n\n... (Suite du fichier tronquée)"
        except Exception as e:
            return f"Erreur de lecture du fichier: {e}"
