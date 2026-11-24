"""
`compensate` and `final` are query parameters. Sent in the JSON body they used to be
dropped with the other unknown keys, and the write was served uncompensated with a
200. A body that has one of these keys is refused.
"""

import pytest

from .conftest import RIGHT, Q, goal, goal_writes, units
from .test_default_path import BASE_RESPONSE, BASE_UNITS_RAD


@pytest.mark.parametrize(
    "extra",
    [
        {"compensate": "full"},
        {"compensate": "static", "final": True},
        {"final": True},
        {"final": False},
        {"compensate": None},
    ],
)
@pytest.mark.parametrize("query", [{}, {"compensate": "full"}])
def test_compensate_or_final_in_the_body_is_refused(
    client, arms, config_file, extra, query
):
    arm = arms[1]
    r = client.post(
        "/joints/write",
        params={**RIGHT, **query},
        json={"angles": Q, "unit": "rad", **extra},
    )
    assert r.status_code == 400, r.text
    detail = r.json()["detail"]
    assert "query" in detail and all(key in detail for key in extra)
    assert arm.motors_bus.calls == [] and arm.servo_compensation is None


def test_other_unknown_keys_of_the_body_are_ignored_as_before(client, arms):
    r = client.post(
        "/joints/write",
        params={"robot_id": 1},
        json={"angles": Q, "unit": "rad", "speed": 3, "Compensate": "full"},
    )
    assert (r.status_code, r.content) == (200, BASE_RESPONSE)
    assert goal(arms[1]) == BASE_UNITS_RAD and goal_writes(arms[1]) == 1


def test_a_misspelt_query_key_cannot_be_caught_only_seen_in_the_response(
    client, arms, config_file
):
    """What a client must check: a compensated write answers with `compensation`."""
    arm = arms[1]
    for key in ("Compensate", "compensated", "compensate "):
        r = client.post(
            "/joints/write", params={**RIGHT, key: "full"}, json={"angles": Q, "unit": "rad"}
        )
        assert r.status_code == 200 and "compensation" not in r.json()
        assert goal(arm) == units(arm, Q)
    r = client.post(
        "/joints/write",
        params={**RIGHT, "compensate": "full"},
        json={"angles": Q, "unit": "rad"},
    )
    assert r.status_code == 200 and r.json()["compensation"]["terms"] == "full"
