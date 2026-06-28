from vinfast_callbot.models import Category, RoutingStatus, SessionState
from vinfast_callbot.post_call import PostCallBuilder


def test_post_call_builder_outputs_final_json_contract() -> None:
    state = SessionState(
        session_id="call-001",
        category=Category.G_1,
        routing_status=RoutingStatus.CONFIRMED,
        fields={
            "full_name": "Lê Phương",
            "phone": "0375889750",
            "current_location": "Lương Thế Vinh",
            "city_name": "Hà Nội",
            "vehicle_condition": "chết máy",
        },
    )

    data = PostCallBuilder().build_dict(state, partial=True)

    assert data is not None
    assert set(data) == {"category", "fields", "post_call"}
    assert data["category"] == "G_1"
    assert data["fields"]["full_name"] == "Lê Phương"
    assert data["fields"]["vehicle_model"] is None
    assert "candidate_categories" not in data
    assert data["post_call"]["sentimental_analysis"] == "urgent"
    assert data["post_call"]["emergency"] == "no"
