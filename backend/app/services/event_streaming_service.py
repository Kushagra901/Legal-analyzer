"""Event streaming service using Apache Kafka for document lifecycle events.

Publishes and consumes document processing events to decouple pipeline stages.
Supports event types: document.uploaded, document.processing, document.analyzed,
document.completed, document.failed, analysis.risk_flagged, report.generated.

Uses confluent-kafka Python client with Avro-style JSON schema validation.
"""
import json
import logging
from collections.abc import Callable
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.core.config import settings

logger = logging.getLogger(__name__)

# Graceful fallback for Kafka
try:
    from confluent_kafka import Consumer, KafkaError, Producer
    KAFKA_AVAILABLE = True
except ImportError:
    logger.warning("confluent_kafka not installed. Kafka event streaming will be disabled.")
    KAFKA_AVAILABLE = False


class EventType(StrEnum):
    DOCUMENT_UPLOADED = "document.uploaded"
    DOCUMENT_PROCESSING = "document.processing"
    DOCUMENT_ANALYZED = "document.analyzed"
    DOCUMENT_COMPLETED = "document.completed"
    DOCUMENT_FAILED = "document.failed"
    ANALYSIS_RISK_FLAGGED = "analysis.risk_flagged"
    REPORT_GENERATED = "report.generated"


class DocumentEvent(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    event_type: str
    document_id: UUID
    user_id: UUID | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    payload: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class EventStreamingService:
    def __init__(self) -> None:
        """Initialize the event streaming service with Kafka configuration."""
        self.bootstrap_servers = getattr(settings, "KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        self.topic_prefix = getattr(settings, "KAFKA_TOPIC_PREFIX", "legal_analyzer")
        self.producer = self._create_producer() if KAFKA_AVAILABLE else None

    def _create_producer(self) -> Optional['Producer']:
        """Factory method to create a Kafka Producer."""
        if not KAFKA_AVAILABLE:
            return None
        conf = {
            'bootstrap.servers': self.bootstrap_servers,
            'client.id': 'legal_analyzer_producer'
        }
        return Producer(conf)

    def _create_consumer(self, group_id: str) -> Optional['Consumer']:
        """Factory method to create a Kafka Consumer."""
        if not KAFKA_AVAILABLE:
            return None
        conf = {
            'bootstrap.servers': self.bootstrap_servers,
            'group.id': group_id,
            'auto.offset.reset': 'earliest'
        }
        return Consumer(conf)

    def publish_event(
        self,
        event_type: EventType,
        document_id: UUID,
        payload: dict[str, Any],
        user_id: UUID | None = None
    ) -> None:
        """Publishes a document event to Kafka."""
        if not self.producer:
            logger.warning(f"Kafka unavailable. Skipping publishing event {event_type} for document {document_id}")
            return

        event = DocumentEvent(
            event_type=event_type.value,
            document_id=document_id,
            user_id=user_id,
            payload=payload
        )

        topic = f"{self.topic_prefix}.{event_type.value}"

        def delivery_report(err: Any, msg: Any) -> None:
            if err is not None:
                logger.error(f"Message delivery failed: {err}")
            else:
                logger.debug(f"Message delivered to {msg.topic()} [{msg.partition()}]")

        try:
            self.producer.produce(
                topic,
                key=str(document_id).encode('utf-8'),
                value=event.model_dump_json().encode('utf-8'),
                callback=delivery_report
            )
            self.producer.poll(0)
        except Exception as e:
            logger.error(f"Failed to publish event to Kafka: {e}")

    def consume_events(
        self,
        topic: str,
        group_id: str,
        handler_fn: Callable[[DocumentEvent], None],
        max_messages: int = 100
    ) -> None:
        """Consumes events from a Kafka topic and processes them using a handler."""
        consumer = self._create_consumer(group_id)
        if not consumer:
            logger.warning("Kafka unavailable. Cannot consume events.")
            return

        consumer.subscribe([topic])

        try:
            messages_processed = 0
            while messages_processed < max_messages:
                msg = consumer.poll(1.0)

                if msg is None:
                    continue
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    else:
                        logger.error(f"Consumer error: {msg.error()}")
                        break

                try:
                    event_data = json.loads(msg.value().decode('utf-8'))
                    event = DocumentEvent(**event_data)
                    handler_fn(event)
                    messages_processed += 1
                except Exception as e:
                    logger.error(f"Error processing message: {e}")

        finally:
            consumer.close()

    def publish_document_uploaded(self, document_id: UUID, filename: str, user_id: UUID | None = None) -> None:
        """Convenience method to publish a document uploaded event."""
        self.publish_event(
            EventType.DOCUMENT_UPLOADED,
            document_id,
            payload={"filename": filename},
            user_id=user_id
        )

    def publish_analysis_completed(
        self,
        document_id: UUID,
        safety_score: float,
        risk_level: str,
        user_id: UUID | None = None
    ) -> None:
        """Convenience method to publish an analysis completed event."""
        self.publish_event(
            EventType.DOCUMENT_ANALYZED,
            document_id,
            payload={"safety_score": safety_score, "risk_level": risk_level},
            user_id=user_id
        )

    def publish_risk_alert(
        self,
        document_id: UUID,
        risk_level: str,
        high_risk_clauses: list,
        user_id: UUID | None = None
    ) -> None:
        """Convenience method to publish a high risk alert event."""
        self.publish_event(
            EventType.ANALYSIS_RISK_FLAGGED,
            document_id,
            payload={"risk_level": risk_level, "high_risk_clauses": high_risk_clauses},
            user_id=user_id
        )

    def close(self) -> None:
        """Flush and close connections."""
        if self.producer:
            self.producer.flush(10.0)
