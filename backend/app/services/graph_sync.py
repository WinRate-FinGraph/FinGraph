from app.db.neo4j import neo4j_conn
from app.models.transaction import Transaction
from app.models.qris import PaymentEvent


def clear_graph():
    query = """
    MATCH (n)
    DETACH DELETE n
    """
    neo4j_conn.execute_write(query)


def sync_transaction_to_graph(transaction: Transaction):
    sender = transaction.sender_account
    receiver = transaction.receiver_account
    device = transaction.device
    merchant = transaction.merchant

    query = """
    MERGE (sender:Account {id: $sender_id})
    SET sender.account_number = $sender_account_number,
        sender.holder_name = $sender_holder_name,
        sender.risk_level = $sender_risk_level

    MERGE (receiver:Account {id: $receiver_id})
    SET receiver.account_number = $receiver_account_number,
        receiver.holder_name = $receiver_holder_name,
        receiver.risk_level = $receiver_risk_level

    MERGE (trx:Transaction {id: $transaction_id})
    SET trx.reference = $transaction_reference,
        trx.amount = $amount,
        trx.currency = $currency,
        trx.channel = $channel,
        trx.status = $status,
        trx.fraud_score = $fraud_score,
        trx.risk_level = $risk_level,
        trx.source_country = $source_country,
        trx.destination_country = $destination_country

    MERGE (sender)-[:SENT]->(trx)
    MERGE (trx)-[:RECEIVED_BY]->(receiver)

    MERGE (sourceCountry:Country {code: $source_country})
    MERGE (destCountry:Country {code: $destination_country})
    MERGE (trx)-[:FROM_COUNTRY]->(sourceCountry)
    MERGE (trx)-[:TO_COUNTRY]->(destCountry)
    """

    params = {
        "sender_id": str(sender.id),
        "sender_account_number": sender.account_number,
        "sender_holder_name": sender.holder_name,
        "sender_risk_level": sender.risk_level,
        "receiver_id": str(receiver.id),
        "receiver_account_number": receiver.account_number,
        "receiver_holder_name": receiver.holder_name,
        "receiver_risk_level": receiver.risk_level,
        "transaction_id": str(transaction.id),
        "transaction_reference": transaction.transaction_reference,
        "amount": float(transaction.amount),
        "currency": transaction.currency,
        "channel": transaction.channel,
        "status": transaction.status,
        "fraud_score": float(transaction.fraud_score),
        "risk_level": transaction.risk_level,
        "source_country": transaction.source_country,
        "destination_country": transaction.destination_country,
    }

    neo4j_conn.execute_write(query, params)

    if device:
        device_query = """
        MATCH (trx:Transaction {id: $transaction_id})
        MERGE (device:Device {id: $device_id})
        SET device.fingerprint = $device_fingerprint,
            device.device_type = $device_type,
            device.os = $device_os,
            device.browser = $device_browser,
            device.ip_address = $device_ip_address,
            device.risk_level = $device_risk_level,
            device.is_blacklisted = $device_is_blacklisted
        MERGE (trx)-[:USED_DEVICE]->(device)
        """

        neo4j_conn.execute_write(
            device_query,
            {
                "transaction_id": str(transaction.id),
                "device_id": str(device.id),
                "device_fingerprint": device.device_fingerprint,
                "device_type": device.device_type,
                "device_os": device.os,
                "device_browser": device.browser,
                "device_ip_address": device.ip_address,
                "device_risk_level": device.risk_level,
                "device_is_blacklisted": device.is_blacklisted,
            },
        )

    if merchant:
        merchant_query = """
        MATCH (trx:Transaction {id: $transaction_id})
        MERGE (merchant:Merchant {id: $merchant_id})
        SET merchant.name = $merchant_name,
            merchant.category = $merchant_category,
            merchant.country_code = $merchant_country_code,
            merchant.risk_level = $merchant_risk_level,
            merchant.is_blacklisted = $merchant_is_blacklisted
        MERGE (trx)-[:PAID_TO]->(merchant)
        """

        neo4j_conn.execute_write(
            merchant_query,
            {
                "transaction_id": str(transaction.id),
                "merchant_id": str(merchant.id),
                "merchant_name": merchant.name,
                "merchant_category": merchant.category,
                "merchant_country_code": merchant.country_code,
                "merchant_risk_level": merchant.risk_level,
                "merchant_is_blacklisted": merchant.is_blacklisted,
            },
        )


def get_graph_data(limit: int = 50, risk_level: str | None = None):
    risk_filter = ""
    if risk_level:
        risk_filter = "WHERE trx.risk_level = $risk_level"

    query = f"""
    MATCH path = (a:Account)-[:SENT]->(trx:Transaction)-[:RECEIVED_BY]->(b:Account)
    {risk_filter}
    OPTIONAL MATCH (trx)-[:USED_DEVICE]->(d:Device)
    OPTIONAL MATCH (trx)-[:PAID_TO]->(m:Merchant)
    OPTIONAL MATCH (trx)-[:FROM_COUNTRY]->(sc:Country)
    OPTIONAL MATCH (trx)-[:TO_COUNTRY]->(dc:Country)
    RETURN a, trx, b, d, m, sc, dc
    ORDER BY trx.fraud_score DESC
    LIMIT $limit
    """

    records = neo4j_conn.execute_read(
        query,
        {
            "limit": limit,
            "risk_level": risk_level,
        },
    )

    nodes = {}
    edges = []

    def add_node(node_id: str, label: str, data: dict):
        if node_id not in nodes:
            nodes[node_id] = {
                "id": node_id,
                "label": label,
                **data,
            }

    def add_edge(source: str, target: str, label: str):
        edges.append(
            {
                "id": f"{source}-{label}-{target}",
                "source": source,
                "target": target,
                "label": label,
            }
        )

    for record in records:
        account_sender = record["a"]
        trx = record["trx"]
        account_receiver = record["b"]
        device = record["d"]
        merchant = record["m"]
        source_country = record["sc"]
        destination_country = record["dc"]

        sender_id = f"account-{account_sender['id']}"
        trx_id = f"transaction-{trx['id']}"
        receiver_id = f"account-{account_receiver['id']}"

        add_node(
            sender_id,
            "Account",
            {
                "title": account_sender.get("holder_name"),
                "risk_level": account_sender.get("risk_level"),
                "account_number": account_sender.get("account_number"),
            },
        )

        add_node(
            receiver_id,
            "Account",
            {
                "title": account_receiver.get("holder_name"),
                "risk_level": account_receiver.get("risk_level"),
                "account_number": account_receiver.get("account_number"),
            },
        )

        add_node(
            trx_id,
            "Transaction",
            {
                "title": trx.get("reference"),
                "amount": trx.get("amount"),
                "currency": trx.get("currency"),
                "fraud_score": trx.get("fraud_score"),
                "risk_level": trx.get("risk_level"),
                "status": trx.get("status"),
            },
        )

        add_edge(sender_id, trx_id, "SENT")
        add_edge(trx_id, receiver_id, "RECEIVED_BY")

        if device:
            device_id = f"device-{device['id']}"
            add_node(
                device_id,
                "Device",
                {
                    "title": device.get("fingerprint"),
                    "risk_level": device.get("risk_level"),
                    "is_blacklisted": device.get("is_blacklisted"),
                    "ip_address": device.get("ip_address"),
                },
            )
            add_edge(trx_id, device_id, "USED_DEVICE")

        if merchant:
            merchant_id = f"merchant-{merchant['id']}"
            add_node(
                merchant_id,
                "Merchant",
                {
                    "title": merchant.get("name"),
                    "risk_level": merchant.get("risk_level"),
                    "category": merchant.get("category"),
                    "country_code": merchant.get("country_code"),
                },
            )
            add_edge(trx_id, merchant_id, "PAID_TO")

        if source_country:
            source_country_id = f"country-{source_country['code']}"
            add_node(
                source_country_id,
                "Country",
                {
                    "title": source_country.get("code"),
                    "code": source_country.get("code"),
                },
            )
            add_edge(trx_id, source_country_id, "FROM_COUNTRY")

        if destination_country:
            destination_country_id = f"country-{destination_country['code']}"
            add_node(
                destination_country_id,
                "Country",
                {
                    "title": destination_country.get("code"),
                    "code": destination_country.get("code"),
                },
            )
            add_edge(trx_id, destination_country_id, "TO_COUNTRY")

    return {
        "nodes": list(nodes.values()),
        "edges": edges,
    }


def sync_payment_to_graph(payment: PaymentEvent):
    """Sync only pseudonymous QRIS entities; raw payer identifiers never enter Neo4j."""
    query = """
    MERGE (payer:Payer {id: $payer_id})
    MERGE (payment:Payment {id: $payment_id})
    SET payment.reference = $reference, payment.amount = $amount,
        payment.risk_level = $risk_level, payment.fraud_score = $fraud_score,
        payment.status = $status
    MERGE (merchant:Merchant {id: $merchant_id})
    SET merchant.name = $merchant_name, merchant.risk_level = $merchant_risk
    MERGE (outlet:Outlet {id: $outlet_id})
    SET outlet.name = $outlet_name, outlet.city = $outlet_city
    MERGE (qris:QRISProfile {id: $qris_id})
    SET qris.nmid = $nmid, qris.type = $qris_type
    MERGE (pjp:PJP {name: $acquirer})
    MERGE (region:Region {name: $source_region})
    MERGE (country:Country {code: $source_country})
    MERGE (payer)-[:PAYER_MADE_PAYMENT]->(payment)
    MERGE (payment)-[:PAYMENT_TO_MERCHANT]->(merchant)
    MERGE (merchant)-[:MERCHANT_HAS_OUTLET]->(outlet)
    MERGE (outlet)-[:OUTLET_USES_QRIS]->(qris)
    MERGE (payment)-[:PAYMENT_VIA_PJP]->(pjp)
    MERGE (payment)-[:PAYMENT_FROM_REGION]->(region)
    MERGE (payment)-[:PAYMENT_FROM_COUNTRY]->(country)
    """
    params = {
        "payer_id": payment.payer_pseudonym,
        "payment_id": str(payment.id), "reference": payment.provider_reference,
        "amount": float(payment.amount), "risk_level": payment.risk_level,
        "fraud_score": payment.fraud_score, "status": payment.payment_status,
        "merchant_id": str(payment.merchant_id), "merchant_name": payment.merchant.name,
        "merchant_risk": payment.merchant.risk_level, "outlet_id": str(payment.outlet_id),
        "outlet_name": payment.outlet.name, "outlet_city": payment.outlet.city,
        "qris_id": str(payment.qris_profile_id), "nmid": payment.qris_profile.nmid,
        "qris_type": payment.qris_type, "acquirer": payment.acquirer_name,
        "source_region": payment.source_region or "Tidak diketahui", "source_country": payment.source_country,
    }
    neo4j_conn.execute_write(query, params)
    if payment.order_id:
        neo4j_conn.execute_write(
            """MATCH (p:Payment {id: $payment_id}) MERGE (o:Order {id: $order_id})
            SET o.reference = $order_reference MERGE (p)-[:PAYMENT_FOR_ORDER]->(o)""",
            {"payment_id": str(payment.id), "order_id": str(payment.order_id), "order_reference": payment.order.order_reference},
        )
