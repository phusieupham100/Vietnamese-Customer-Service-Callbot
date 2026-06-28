"""Prompt templates for LLM-first dialogue understanding and rendering.

The LLM owns semantic turn understanding, while backend modules still validate
JSON, normalize critical identifiers, merge state, choose actions, and build
final JSON.
"""

from __future__ import annotations


COMMON_RULES = """\
Vehicle symptoms are not the same as requested service.
Do not classify G_1 only because the vehicle is broken, cannot start, has no battery, or shows an error.
When requested service is unclear, return category = null.
Assess emergency from real-world safety risk and conversation context, not a single keyword.
Use pending_field to interpret short replies.
Do not invent customer information.
Do not overwrite confirmed fields unless the customer clearly corrects them.
Return valid JSON only.
"""


TURN_ANALYSIS_PROMPT = """\
Analyze the latest Vietnamese callbot turn semantically using transcript,
history, current state, pending_field, and category schema.

Return JSON keys:
- understood
- user_goal
- category
- routing_status
- candidate_categories
- pending_field
- emergency
- fields
- uncertain_fields
- corrections
- ambiguities
- intent_switch
- out_of_scope
- handoff_reason

Rules:
{common_rules}
""".format(common_rules=COMMON_RULES)


SIGNAL_EXTRACTION_PROMPT = """\
Extract internal routing signals from the latest Vietnamese transcript.
Output JSON keys:
- service_goal
- vehicle_type
- symptom
- explicit_rescue_request
- explicit_repair_request
- explicit_warranty_request
- explicit_order_request
- explicit_remote_support_request
- correction_detected

Rules:
{common_rules}
""".format(common_rules=COMMON_RULES)


FIELD_EXTRACTION_PROMPT = """\
Extract only fields that belong to the confirmed category schema.
Return fields explicitly provided by the customer only.
Put unclear critical values in uncertain_fields.

Rules:
{common_rules}
""".format(common_rules=COMMON_RULES)


POST_CALL_PROMPT = """\
Create post_call JSON with:
- short_summary
- sentimental_analysis
- emergency

Do not include internal state, candidates, action names, confidence, or failed_turn_count.
Use emergency = "yes" or "no".
""".format(common_rules=COMMON_RULES)
