from typing import Final


PLAN_ORDER: Final = {"basic": 0, "growth": 1, "premium": 2}

PLAN_CATALOG: Final = {
    "basic": {
        "code": "basic",
        "name": "Basic",
        "monthly_price": 49_000,
        "transaction_limit": 500,
        "outlet_limit": 1,
        "seat_limit": 1,
    },
    "growth": {
        "code": "growth",
        "name": "Growth",
        "monthly_price": 99_000,
        "transaction_limit": 2_000,
        "outlet_limit": 3,
        "seat_limit": 3,
    },
    "premium": {
        "code": "premium",
        "name": "Premium",
        "monthly_price": 149_000,
        "transaction_limit": 5_000,
        "outlet_limit": None,
        "seat_limit": 5,
    },
}


def normalize_plan(value: str | None) -> str:
    return value if value in PLAN_ORDER else "basic"


def plan_payload(value: str | None) -> dict:
    return dict(PLAN_CATALOG[normalize_plan(value)])


def plan_allows(current: str | None, required: str) -> bool:
    return PLAN_ORDER[normalize_plan(current)] >= PLAN_ORDER[required]
