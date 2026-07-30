"""GCP Project discovery (scoped to the specified parent)."""

import uuid
from app.core.logging import get_logger
from app.discovery.base import BaseDiscoverer
from app.models.resources import DiscoveredResource, ResourceType

logger = get_logger("discovery.projects_resource")


class ProjectDiscoverer(BaseDiscoverer):
    """Discovers GCP Projects within the specified scope."""

    async def discover(self, project_id: str) -> list[DiscoveredResource]:
        """Discover projects scoped to the parent.

        The project_id parameter context:
        - If numeric: it's a folder/org ID — search projects under it
        - If alphanumeric: it's a project ID itself — just describe that project
        """
        resources = []
        try:
            from google.cloud import resourcemanager_v3

            client = resourcemanager_v3.ProjectsClient(credentials=self.credentials)

            if project_id and not project_id.isdigit():
                # It's a project ID — describe this single project
                try:
                    project = client.get_project(name=f"projects/{project_id}")
                    if project.state.name == "ACTIVE":
                        resources.append(self._to_resource(project))
                except Exception:
                    pass
            else:
                # It's a numeric ID (folder or org) — search projects under it
                for parent_prefix in [f"folders/{project_id}", f"organizations/{project_id}"]:
                    try:
                        request = resourcemanager_v3.SearchProjectsRequest(
                            query=f"parent:{parent_prefix}"
                        )
                        for project in client.search_projects(request=request):
                            if project.state.name == "ACTIVE":
                                resources.append(self._to_resource(project))
                        if resources:
                            break
                    except Exception:
                        continue

            logger.info(f"Discovered {len(resources)} projects under {project_id}")
        except Exception as e:
            logger.error(f"Error discovering projects: {e}")
        return resources

    def _to_resource(self, project) -> DiscoveredResource:
        """Convert a GCP project to a DiscoveredResource."""
        billing_account = self._get_billing_account(project.project_id)
        enabled_apis = self._get_enabled_apis(project.project_id)

        return DiscoveredResource(
            id=str(uuid.uuid4()),
            type=ResourceType.GCP_PROJECT,
            name=project.display_name or project.project_id,
            project=project.project_id,
            location="global",
            terraform_resource_type="google_project",
            terraform_resource_name=self.sanitize_name(project.project_id),
            terraform_import_id=f"projects/{project.project_id}",
            attributes={
                "project_id": project.project_id,
                "name": project.display_name or "",
                "parent": project.parent or "",
                "labels": dict(project.labels) if project.labels else {},
                "billing_account": billing_account,
                "activate_apis": enabled_apis,
            },
        )

    def _get_billing_account(self, project_id: str) -> str:
        """Fetch the billing account linked to a project via Cloud Billing API."""
        try:
            from googleapiclient.discovery import build
            service = build("cloudbilling", "v1", credentials=self.credentials)
            result = service.projects().getBillingInfo(name=f"projects/{project_id}").execute()
            billing_account = result.get("billingAccountName", "")
            if billing_account:
                return billing_account.replace("billingAccounts/", "")
            return ""
        except Exception:
            return ""

    def _get_enabled_apis(self, project_id: str) -> list[str]:
        """Fetch enabled APIs for a project via Service Usage API."""
        apis = []
        try:
            from googleapiclient.discovery import build
            service = build("serviceusage", "v1", credentials=self.credentials)
            request = service.services().list(
                parent=f"projects/{project_id}",
                filter="state:ENABLED",
                pageSize=200,
            )
            while request:
                response = request.execute()
                for svc in response.get("services", []):
                    # Format: projects/123/services/compute.googleapis.com → extract API name
                    api_name = svc.get("config", {}).get("name", "")
                    if api_name:
                        apis.append(api_name)
                request = service.services().list_next(
                    previous_request=request, previous_response=response
                )
        except Exception as e:
            logger.warning(f"Could not fetch APIs for {project_id}: {e}")
        return sorted(apis)
