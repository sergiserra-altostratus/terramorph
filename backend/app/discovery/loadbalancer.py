"""Load Balancer (Forwarding Rules) discovery — global + regional."""

import uuid
from google.cloud import compute_v1
from app.core.logging import get_logger
from app.discovery.base import BaseDiscoverer
from app.models.resources import DiscoveredResource, ResourceType

logger = get_logger("discovery.loadbalancer")


class LoadBalancerDiscoverer(BaseDiscoverer):
    """Discovers forwarding rules (global and regional LBs)."""

    async def discover(self, project_id: str) -> list[DiscoveredResource]:
        resources = []

        # Global forwarding rules (HTTP/HTTPS LBs)
        try:
            client = compute_v1.GlobalForwardingRulesClient(credentials=self.credentials)
            request = compute_v1.ListGlobalForwardingRulesRequest(project=project_id)
            for rule in client.list(request=request):
                resources.append(DiscoveredResource(
                    id=str(uuid.uuid4()),
                    type=ResourceType.LOAD_BALANCER,
                    name=rule.name,
                    project=project_id,
                    location="global",
                    terraform_resource_type="google_compute_global_forwarding_rule",
                    terraform_resource_name=self.sanitize_name(rule.name),
                    terraform_import_id=f"projects/{project_id}/global/forwardingRules/{rule.name}",
                    attributes={
                        "target": rule.target.split("/")[-1] if rule.target else "",
                        "port_range": rule.port_range or "",
                        "ip_address": rule.I_p_address or "",
                        "ip_protocol": rule.I_p_protocol or "",
                        "load_balancing_scheme": rule.load_balancing_scheme or "",
                        "description": rule.description or "",
                        "scope": "global",
                        "labels": dict(rule.labels) if rule.labels else {},
                    },
                ))
        except Exception as e:
            logger.error(f"Error discovering global forwarding rules in {project_id}: {e}")

        # Regional forwarding rules (TCP/UDP, internal LBs)
        try:
            regional_client = compute_v1.ForwardingRulesClient(credentials=self.credentials)
            request = compute_v1.AggregatedListForwardingRulesRequest(project=project_id)
            for scope_key, scoped_list in regional_client.aggregated_list(request=request):
                if scoped_list.forwarding_rules:
                    region_name = scope_key.split("/")[-1]
                    for rule in scoped_list.forwarding_rules:
                        resources.append(DiscoveredResource(
                            id=str(uuid.uuid4()),
                            type=ResourceType.LOAD_BALANCER,
                            name=rule.name,
                            project=project_id,
                            location=region_name,
                            terraform_resource_type="google_compute_forwarding_rule",
                            terraform_resource_name=self.sanitize_name(f"{region_name}_{rule.name}"),
                            terraform_import_id=f"projects/{project_id}/regions/{region_name}/forwardingRules/{rule.name}",
                            attributes={
                                "target": rule.target.split("/")[-1] if rule.target else "",
                                "port_range": rule.port_range or "",
                                "ip_address": rule.I_p_address or "",
                                "ip_protocol": rule.I_p_protocol or "",
                                "load_balancing_scheme": rule.load_balancing_scheme or "",
                                "description": rule.description or "",
                                "scope": "regional",
                                "region": region_name,
                                "network": rule.network.split("/")[-1] if rule.network else "",
                                "labels": dict(rule.labels) if rule.labels else {},
                            },
                        ))
        except Exception as e:
            logger.error(f"Error discovering regional forwarding rules in {project_id}: {e}")

        logger.info(f"Discovered {len(resources)} forwarding rules (global+regional) in {project_id}")
        return resources
