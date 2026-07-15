"""Pub/Sub topic and subscription discovery."""

import uuid

from googleapiclient.discovery import build

from app.core.logging import get_logger
from app.discovery.base import BaseDiscoverer
from app.models.resources import DiscoveredResource, ResourceType

logger = get_logger("discovery.pubsub")


class PubSubDiscoverer(BaseDiscoverer):
    """Discovers Pub/Sub topics and subscriptions."""

    async def discover(self, project_id: str) -> list[DiscoveredResource]:
        """Discover all Pub/Sub topics and subscriptions in a project."""
        resources = []

        try:
            service = build("pubsub", "v1", credentials=self.credentials)

            # Discover topics
            topics_req = service.projects().topics().list(
                project=f"projects/{project_id}"
            )
            topics_resp = topics_req.execute()

            for topic in topics_resp.get("topics", []):
                name = topic["name"].split("/")[-1]
                if name.startswith("_"):  # Skip internal topics
                    continue

                resource = DiscoveredResource(
                    id=str(uuid.uuid4()),
                    type=ResourceType.PUBSUB_TOPIC,
                    name=name,
                    project=project_id,
                    location="global",
                    terraform_resource_type="google_pubsub_topic",
                    terraform_resource_name=self.sanitize_name(name),
                    terraform_import_id=f"projects/{project_id}/topics/{name}",
                    attributes={
                        "labels": topic.get("labels", {}),
                        "message_retention_duration": topic.get(
                            "messageRetentionDuration", ""
                        ),
                        "kms_key_name": topic.get("kmsKeyName", ""),
                    },
                )
                resources.append(resource)

            # Discover subscriptions
            subs_req = service.projects().subscriptions().list(
                project=f"projects/{project_id}"
            )
            subs_resp = subs_req.execute()

            for sub in subs_resp.get("subscriptions", []):
                name = sub["name"].split("/")[-1]
                topic_name = sub.get("topic", "").split("/")[-1]

                resource = DiscoveredResource(
                    id=str(uuid.uuid4()),
                    type=ResourceType.PUBSUB_SUBSCRIPTION,
                    name=name,
                    project=project_id,
                    location="global",
                    terraform_resource_type="google_pubsub_subscription",
                    terraform_resource_name=self.sanitize_name(name),
                    terraform_import_id=f"projects/{project_id}/subscriptions/{name}",
                    attributes={
                        "topic": topic_name,
                        "ack_deadline_seconds": sub.get("ackDeadlineSeconds", 10),
                        "message_retention_duration": sub.get(
                            "messageRetentionDuration", "604800s"
                        ),
                        "retain_acked_messages": sub.get("retainAckedMessages", False),
                        "labels": sub.get("labels", {}),
                        "push_endpoint": sub.get("pushConfig", {}).get(
                            "pushEndpoint", ""
                        ),
                    },
                )
                resources.append(resource)

            logger.info(f"Discovered {len(resources)} Pub/Sub resources in {project_id}")

        except Exception as e:
            logger.error(f"Error discovering Pub/Sub in {project_id}: {e}")

        return resources
