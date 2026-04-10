"""RabbitMQ connection and messaging utilities.

This module provides helpers for RabbitMQ operations including
connection setup, queue management, and message publishing.
"""

import os
import time
from typing import Callable, Optional
import pika
from pika.adapters import blocking_connection

from app.utils.logging_config import StructuredLogger


logger = StructuredLogger.for_module(__name__)


class RabbitMQConnection:
    """Manager for RabbitMQ connections and operations.
    
    Handles connection setup with retries, queue declaration,
    and provides methods for message operations.
    """
    
    def __init__(self, rabbitmq_url: Optional[str] = None):
        """Initialize RabbitMQ connection manager.
        
        Args:
            rabbitmq_url: RabbitMQ URL. Uses environment variable if not provided.
        """
        self.rabbitmq_url = rabbitmq_url or os.getenv(
            "RABBITMQ_URL",
            "amqp://guest:guest@rabbitmq:5672/"
        )
        self.connection: Optional[blocking_connection.BlockingConnection] = None
        self.channel: Optional[pika.channel.Channel] = None
    
    def connect(self, max_retries: int = 5, retry_delay: int = 2) -> None:
        """Establish connection to RabbitMQ with retries.
        
        Args:
            max_retries: Maximum number of connection attempts
            retry_delay: Delay in seconds between retries
            
        Raises:
            pika.exceptions.AMQPConnectionError: If all retries fail
        """
        for attempt in range(max_retries):
            try:
                self.connection = pika.BlockingConnection(
                    pika.URLParameters(self.rabbitmq_url)
                )
                self.channel = self.connection.channel()
                
                logger.log_rabbitmq_event("CONNECTED", status="SUCCESS")
                return
                
            except pika.exceptions.AMQPConnectionError as e:
                logger.log_warning(
                    "RabbitMQ connection failed",
                    attempt=attempt + 1,
                    max_retries=max_retries,
                    error=str(e)
                )
                
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    logger.log_error(
                        "Failed to connect to RabbitMQ after all retries",
                        exc_info=e,
                        max_retries=max_retries
                    )
                    raise
    
    def declare_queue(self, queue_name: str, durable: bool = True) -> None:
        """Declare a queue on RabbitMQ.
        
        Args:
            queue_name: Name of the queue
            durable: Whether the queue survives broker restarts

        Raises:
            RuntimeError: If called before a channel is available.
            pika.exceptions.AMQPError: If queue declaration fails.
        """
        if not self.channel:
            raise RuntimeError("Not connected to RabbitMQ")
        
        self.channel.queue_declare(queue=queue_name, durable=durable)
        logger.log_debug("Queue declared", queue_name=queue_name, durable=durable)
    
    def publish_message(
        self,
        queue_name: str,
        message_body: str,
        persistent: bool = True
    ) -> None:
        """Publish a message to a queue.
        
        Args:
            queue_name: Target queue name
            message_body: Message content (usually JSON string)
            persistent: Whether message survives broker restarts

        Raises:
            RuntimeError: If called before a channel is available.
            pika.exceptions.AMQPError: If publishing fails.
        """
        if not self.channel:
            raise RuntimeError("Not connected to RabbitMQ")
        
        delivery_mode = 2 if persistent else 1
        
        self.channel.basic_publish(
            exchange='',
            routing_key=queue_name,
            body=message_body,
            properties=pika.BasicProperties(delivery_mode=delivery_mode)
        )
        
        logger.log_rabbitmq_event(
            "MESSAGE_SENT",
            status="SUCCESS",
            queue=queue_name,
            size_bytes=len(message_body)
        )
    
    def setup_consumer(
        self,
        queue_name: str,
        callback: Callable,
        prefetch_count: int = 1
    ) -> None:
        """Setup a message consumer on a queue.
        
        Args:
            queue_name: Queue to consume from
            callback: Function to call for each message
            prefetch_count: Max messages to process simultaneously

        Raises:
            RuntimeError: If called before a channel is available.
            pika.exceptions.AMQPError: If consumer configuration fails.
        """
        if not self.channel:
            raise RuntimeError("Not connected to RabbitMQ")
        
        self.channel.basic_qos(prefetch_count=prefetch_count)
        
        self.channel.basic_consume(
            queue=queue_name,
            on_message_callback=callback,
            auto_ack=False
        )
        
        logger.log_debug(
            "Consumer setup",
            queue=queue_name,
            prefetch_count=prefetch_count
        )
    
    def start_consuming(self) -> None:
        """Start consuming messages from configured queues.

        Raises:
            RuntimeError: If called before a channel is available.
            pika.exceptions.AMQPError: If the broker consume loop fails.
        """
        if not self.channel:
            raise RuntimeError("Not connected to RabbitMQ")
        
        logger.log_rabbitmq_event("START_CONSUMING", status="IN_PROGRESS")
        
        try:
            self.channel.start_consuming()
        except KeyboardInterrupt:
            logger.log_rabbitmq_event("STOP_CONSUMING", status="SUCCESS")
            self.stop_consuming()
        except pika.exceptions.AMQPError as exc:
            logger.log_error("RabbitMQ consume loop failed", exc_info=exc)
            raise
    
    def stop_consuming(self) -> None:
        """Stop consuming messages and close connection.

        This method is idempotent and safe to call during graceful shutdown.
        Connection shutdown errors are logged and swallowed to avoid masking
        the original shutdown reason.
        """
        if self.channel:
            try:
                self.channel.stop_consuming()
            except (pika.exceptions.AMQPError, RuntimeError) as e:
                logger.log_error("Error stopping consumer", exc_info=e)
        
        if self.connection and not self.connection.is_closed:
            try:
                self.connection.close()
                logger.log_rabbitmq_event("DISCONNECTED", status="SUCCESS")
            except (pika.exceptions.AMQPError, RuntimeError) as e:
                logger.log_error("Error closing RabbitMQ connection", exc_info=e)
    
    def __enter__(self) -> "RabbitMQConnection":
        """Context manager entry.

        Returns:
            RabbitMQConnection: The active connection manager.
        """
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit.

        Args:
            exc_type: Exception type, if raised inside context block.
            exc_val: Exception instance, if raised.
            exc_tb: Exception traceback, if raised.
        """
        self.stop_consuming()
