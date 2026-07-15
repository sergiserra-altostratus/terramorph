"""GCP project listing endpoints."""

from fastapi import APIRouter, HTTPException, Query

from app.core.credentials import get_credentials
from app.core.exceptions import CredentialError
from app.core.logging import get_logger

logger = get_logger("projects")

router = APIRouter()


@router.get("/projects")
async def list_projects(
    parent: str | None = Query(
        None,
        description="Parent resource: 'organizations/123' or 'folders/456'",
    ),
) -> dict:
    """List GCP projects accessible with current credentials.

    Optionally filter by parent organization or folder.
    """
    try:
        credentials = get_credentials()
    except CredentialError as e:
        raise HTTPException(status_code=401, detail=str(e))

    try:
        from google.cloud import resourcemanager_v3

        client = resourcemanager_v3.ProjectsClient(credentials=credentials)

        if parent:
            request = resourcemanager_v3.SearchProjectsRequest(query=f"parent:{parent}")
        else:
            request = resourcemanager_v3.SearchProjectsRequest()

        projects = []
        for project in client.search_projects(request=request):
            if project.state.name == "ACTIVE":
                projects.append(
                    {
                        "project_id": project.project_id,
                        "name": project.display_name,
                        "state": project.state.name,
                        "parent": project.parent,
                    }
                )

        return {"projects": projects}

    except Exception as e:
        logger.error(f"Failed to list projects: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list projects: {str(e)}",
        )
