"""Tools for querying data.gouv.fr datasets and files."""

import json
import urllib.request
import urllib.parse
import urllib.error


class Tools:
    """Data.gouv.fr helper tools for dataset discovery and file access."""

    def search_data_gouv_datasets(self, query: str) -> str:
        """Search datasets on data.gouv.fr by keywords.

        Args:
            query: Search keywords (for example, "water quality testing").

        Returns:
            A formatted list of dataset IDs and titles, or an error message.
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
        """List CSV or text files for a dataset ID.

        Args:
            dataset_id: Dataset identifier returned by search.

        Returns:
            A formatted list of file URLs and metadata, or an error message.
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
        """Read the first chunk of a CSV or text file by URL.

        Args:
            file_url: Direct file URL from data.gouv.fr.

        Returns:
            The initial file contents (truncated) or an error message.
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
