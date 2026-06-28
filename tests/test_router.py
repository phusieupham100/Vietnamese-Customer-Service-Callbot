from vinfast_callbot.models import (
    Category,
    DialogueAction,
    RoutingStatus,
    VehicleMatchResult,
    VehicleMatchStatus,
    VehicleMatchType,
    VehicleType,
)
from vinfast_callbot.router import IntentRouter


def test_symptom_only_does_not_route_prematurely_and_asks_targeted_clarification() -> None:
    router = IntentRouter()

    result = router.route("Xe tôi hết pin")
    output = router.to_dialogue_output(result)

    assert result.category is None
    assert result.routing_status == RoutingStatus.NEEDS_CLARIFICATION
    assert result.missing_discriminator == "rescue_needed"
    assert result.candidate_categories == [Category.G_1, Category.G_2, Category.G_5]
    assert "G_1" not in result.clarification_question
    assert output.next_action == DialogueAction.ASK_INTENT_CLARIFICATION


def test_explicit_rescue_routes_g1() -> None:
    result = IntentRouter().route("Xe tôi hết pin, tôi cần cứu hộ")

    assert result.category == Category.G_1
    assert result.routing_status == RoutingStatus.CONFIRMED


def test_car_model_with_repair_request_routes_g2() -> None:
    result = IntentRouter().route("Xe VF8 bị lỗi, tôi muốn đặt lịch kiểm tra")

    assert result.category == Category.G_2


def test_order_request_routes_g3() -> None:
    result = IntentRouter().route("Bao giờ đơn xe được giao?")

    assert result.category == Category.G_3


def test_motorbike_model_with_warranty_request_routes_g4() -> None:
    result = IntentRouter().route("Xe Feliz cần bảo hành")

    assert result.category == Category.G_4


def test_remote_support_request_routes_g5() -> None:
    result = IntentRouter().route("Hướng dẫn tôi khởi động lại màn hình")

    assert result.category == Category.G_5


def test_vehicle_model_alone_does_not_route_to_rescue_or_remote_support() -> None:
    result = IntentRouter().route("VF 8 của tôi không khởi động")

    assert result.category is None
    assert result.routing_status == RoutingStatus.NEEDS_CLARIFICATION


def test_unclear_repair_request_asks_vehicle_type() -> None:
    result = IntentRouter().route("Xe tôi cần bảo hành")

    assert result.category is None
    assert result.missing_discriminator == "vehicle_type"
    assert result.candidate_categories == [Category.G_2, Category.G_4]
    assert "ô tô" in result.clarification_question
    assert "xe máy điện" in result.clarification_question


def test_unconfirmed_vehicle_match_is_not_used_to_confirm_category() -> None:
    fuzzy_match = VehicleMatchResult(
        raw_text="VF tam",
        canonical_name="VF 8",
        vehicle_type=VehicleType.CAR,
        match_type=VehicleMatchType.FUZZY,
        confidence=0.84,
        status=VehicleMatchStatus.NEEDS_CONFIRMATION,
        candidates=["VF 8"],
    )

    result = IntentRouter().route("Xe này cần bảo hành", vehicle_match_result=fuzzy_match)

    assert result.category is None
    assert result.missing_discriminator == "vehicle_type"


def test_routing_after_rescue_clarification_can_change_to_warranty() -> None:
    history = [
        {"role": "user", "content": "Xe tôi không khởi động"},
        {
            "role": "assistant",
            "content": "Dạ anh/chị có cần hỗ trợ cứu hộ ngay không ạ?",
        },
    ]

    result = IntentRouter().route(
        "Không, tôi đang ở nhà. Tôi muốn hỏi lỗi này có được bảo hành không.",
        history=history,
    )

    assert result.category == Category.G_2
    assert result.routing_status == RoutingStatus.CONFIRMED


def test_affirmative_after_rescue_clarification_routes_g1() -> None:
    history = [
        {
            "role": "assistant",
            "content": "Dạ anh/chị có cần hỗ trợ cứu hộ ngay không ạ?",
        },
    ]

    result = IntentRouter().route("Có, tôi cần", history=history)

    assert result.category == Category.G_1
