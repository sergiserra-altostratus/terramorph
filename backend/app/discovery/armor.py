"""Cloud Armor security policy discovery (global + regional) with full rules."""

import uuid
from google.cloud import compute_v1
from app.core.logging import get_logger
from app.discovery.base import BaseDiscoverer
from app.models.resources import DiscoveredResource, ResourceType

logger = get_logger("discovery.armor")


def _extract_rules(policy) -> list[dict]:
    """Extract rules from a security policy into a serializable format."""
    rules = []
    for rule in (policy.rules or []):
        rule_data = {
            "action": rule.action or "allow",
            "priority": rule.priority if rule.priority is not None else 2147483647,
            "description": rule.description or "",
            "preview": rule.preview if hasattr(rule, "preview") else False,
        }

        # Match condition
        if rule.match:
            match_data = {}
            if rule.match.versioned_expr:
                match_data["versioned_expr"] = rule.match.versioned_expr
            if rule.match.config:
                match_data["src_ip_ranges"] = list(rule.match.config.src_ip_ranges) if rule.match.config.src_ip_ranges else []
            if rule.match.expr:
                match_data["expression"] = rule.match.expr.expression or ""
            rule_data["match"] = match_data
        else:
            rule_data["match"] = {"versioned_expr": "SRC_IPS_V1", "src_ip_ranges": ["*"]}

        # Rate limit options
        if hasattr(rule, "rate_limit_options") and rule.rate_limit_options:
            rule_data["rate_limit"] = True

        rules.append(rule_data)

    # Sort by priority
    rules.sort(key=lambda r: r["priority"])
    return rules


class CloudArmorDiscoverer(BaseDiscoverer):
    """Discovers Cloud Armor security policies (global and regional) with full rules."""

    async def discover(self, project_id: str) -> list[DiscoveredResource]:
        resources = []

        # Global security policies
        try:
            client = compute_v1.SecurityPoliciesClient(credentials=self.credentials)
            request = compute_v1.ListSecurityPoliciesRequest(project=project_id)
            for policy in client.list(request=request):
                resources.append(DiscoveredResource(
                    id=str(uuid.uuid4()),
                    type=ResourceType.CLOUD_ARMOR,
                    name=policy.name,
                    project=project_id,
                    location="global",
                    terraform_resource_type="google_compute_security_policy",
                    terraform_resource_name=self.sanitize_name(policy.name),
                    terraform_import_id=f"projects/{project_id}/global/securityPolicies/{policy.name}",
                    attributes={
                        "description": policy.description or "",
                        "type": policy.type_ if hasattr(policy, "type_") else "CLOUD_ARMOR",
                        "scope": "global",
                        "rules": _extract_rules(policy),
                    },
                ))
        except Exception as e:
            logger.error(f"Error discovering global Cloud Armor policies in {project_id}: {e}")

        # Regional security policies
        try:
            agg_client = compute_v1.SecurityPoliciesClient(credentials=self.credentials)
            agg_request = compute_v1.AggregatedListSecurityPoliciesRequest(project=project_id)

            for scope_key, scoped_list in agg_client.aggregated_list(request=agg_request):
                if scoped_list.security_policies:
                    region_name = scope_key.split("/")[-1]
                    for policy in scoped_list.security_policies:
                        if "regions/" not in (policy.self_link or ""):
                            continue
                        resources.append(DiscoveredResource(
                            id=str(uuid.uuid4()),
                            type=ResourceType.CLOUD_ARMOR,
                            name=policy.name,
                            project=project_id,
                            location=region_name,
                            terraform_resource_type="google_compute_region_security_policy",
                            terraform_resource_name=self.sanitize_name(f"{region_name}_{policy.name}"),
                            terraform_import_id=f"projects/{project_id}/regions/{region_name}/securityPolicies/{policy.name}",
                            attributes={
                                "description": policy.description or "",
                                "type": policy.type_ if hasattr(policy, "type_") else "CLOUD_ARMOR",
                                "scope": "regional",
                                "region": region_name,
                                "rules": _extract_rules(policy),
                            },
                        ))
        except Exception as e:
            logger.error(f"Error discovering regional Cloud Armor policies in {project_id}: {e}")

        logger.info(f"Discovered {len(resources)} Cloud Armor policies (global+regional) in {project_id}")
        return resources
