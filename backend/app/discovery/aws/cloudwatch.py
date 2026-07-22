"""AWS CloudWatch Alarm discovery."""

import uuid
from app.core.logging import get_logger
from app.discovery.aws.base import AWSBaseDiscoverer
from app.models.resources import DiscoveredResource, ResourceType

logger = get_logger("aws.discovery.cloudwatch")


class CloudWatchDiscoverer(AWSBaseDiscoverer):
    async def discover(self) -> list[DiscoveredResource]:
        resources = []
        try:
            client = self.session.client("cloudwatch")
            paginator = client.get_paginator("describe_alarms")
            for page in paginator.paginate():
                for alarm in page.get("MetricAlarms", []):
                    resources.append(DiscoveredResource(
                        id=str(uuid.uuid4()), type=ResourceType.AWS_CLOUDWATCH_ALARM, name=alarm["AlarmName"],
                        project=self.region, location=self.region,
                        terraform_resource_type="aws_cloudwatch_metric_alarm",
                        terraform_resource_name=self.sanitize_name(alarm["AlarmName"]),
                        terraform_import_id=alarm["AlarmName"],
                        attributes={
                            "alarm_name": alarm["AlarmName"],
                            "metric_name": alarm.get("MetricName", ""),
                            "namespace": alarm.get("Namespace", ""),
                            "comparison_operator": alarm.get("ComparisonOperator", ""),
                            "threshold": alarm.get("Threshold", 0),
                            "period": alarm.get("Period", 300),
                            "evaluation_periods": alarm.get("EvaluationPeriods", 1),
                            "statistic": alarm.get("Statistic", "Average"),
                        },
                    ))
            logger.info(f"Discovered {len(resources)} CloudWatch alarms")
        except Exception as e:
            logger.error(f"Error discovering CloudWatch: {e}")
        return resources
