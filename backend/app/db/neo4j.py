from neo4j import GraphDatabase

from app.core.config import settings


class Neo4jConnection:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
            connection_timeout=settings.NEO4J_CONNECTION_TIMEOUT_SECONDS,
            max_transaction_retry_time=settings.NEO4J_MAX_RETRY_SECONDS,
        )

    def close(self):
        if self.driver:
            self.driver.close()

    def execute_write(self, query: str, parameters: dict | None = None):
        with self.driver.session() as session:
            return session.execute_write(
                lambda tx: list(tx.run(query, parameters or {}))
            )

    def execute_read(self, query: str, parameters: dict | None = None):
        with self.driver.session() as session:
            return session.execute_read(
                lambda tx: list(tx.run(query, parameters or {}))
            )


neo4j_conn = Neo4jConnection()
