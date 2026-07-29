"""GCP Folder discovery (scoped to the specified parent)."""

import uuid
from app.core.logging import get_logger
from app.discovery.base import BaseDiscoverer
from app.models.resources import DiscoveredResource, ResourceType

logger = get_logger("discovery.folders")


class FolderDiscoverer(BaseDiscoverer):
    """Discovers GCP Folders within the specified scope."""

    async def discover(self, project_id: str) -> list[DiscoveredResource]:
        """Discover folders.

        The project_id parameter here is actually the scope context:
        - If discovery scope is 'organization', project_id = org ID
        - If discovery scope is 'folder', project_id = folder ID
        - If discovery scope is 'project', folders are not applicable (returns empty)

        The orchestrator passes the project_id from _resolve_projects,
        but for folders we need the original scope. We search for folders
        whose parent matches the discovery scope.
        """
        resources = []
        try:
            from google.cloud import resourcemanager_v3

            client = resourcemanager_v3.FoldersClient(credentials=self.credentials)

            # Search folders filtering by parent
            # If project_id looks like a project (has letters), skip folder discovery
            if project_id and not project_id.isdigit():
                # This is a project ID, not a folder/org — skip
                return resources

            # Try to list direct child folders of the given parent
            # project_id in this context could be the org or folder numeric ID
            parent = f"folders/{project_id}" if project_id else ""

            # Try as folder parent first, then as org parent
            for parent_prefix in [f"folders/{project_id}", f"organizations/{project_id}"]:
                try:
                    request = resourcemanager_v3.ListFoldersRequest(parent=parent_prefix)
                    for folder in client.list_folders(request=request):
                        folder_id = folder.name.split("/")[-1]
                        resources.append(DiscoveredResource(
                            id=str(uuid.uuid4()),
                            type=ResourceType.GCP_FOLDER,
                            name=folder.display_name,
                            project=parent_prefix,
                            location="global",
                            terraform_resource_type="google_folder",
                            terraform_resource_name=self.sanitize_name(folder.display_name),
                            terraform_import_id=f"folders/{folder_id}",
                            attributes={
                                "display_name": folder.display_name,
                                "parent": parent_prefix,
                                "folder_id": folder_id,
                                "state": folder.state.name if folder.state else "ACTIVE",
                            },
                        ))
                    if resources:
                        break  # Found folders with this parent, no need to try the other
                except Exception:
                    continue  # Try next parent format

            logger.info(f"Discovered {len(resources)} folders under {project_id}")
        except Exception as e:
            logger.error(f"Error discovering folders: {e}")
        return resources
