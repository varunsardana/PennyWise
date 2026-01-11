from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Dict, Any

from receipt_story.api.routes_chatbot import get_db
from receipt_story.services.chatbot import ChatbotService
from receipt_story.services.planning import BudgetPlanningService

router = APIRouter(prefix="/message", tags=["dispatcher"])

chatbot = ChatbotService()
planner = BudgetPlanningService()


def detect_intent(message: str) -> str:
    msg = message.lower()

    if any(p in msg for p in [
        "create a budget", "help me budget", "make a budget",
        "plan my budget", "build a budget"
    ]):
        return "planning"

    if any(p in msg for p in [
        "what's my budget", "what is my budget",
        "budget summary", "budget status",
        "am i over budget", "am i on track"
    ]):
        return "budget_status"

    if any(p in msg for p in [
        "change my budget", "adjust my budget",
        "update my budget", "modify my budget"
    ]):
        return "budget_refine"

    return "chat"


@router.post("")
async def handle_message(payload: Dict[str, Any], db: Session = Depends(get_db)):
    message = payload["message"]
    history = payload.get("conversation_history")
    original_proposal = payload.get("original_proposal")

    intent = detect_intent(message)
    print(f"Received message: {message}")
    print(f"Detected intent: {intent}")

    response_payload = {"type": intent}

    try:
        if intent == "planning":
            result = planner.start_planning(message, db, history)
            response_payload.update(result)

            # Ensure there's always a response string
            if "response" not in response_payload:
                response_payload["response"] = "Let's start planning your budget!"

        elif intent == "budget_status":
            result = chatbot.get_budget_summary(db)
            response_payload.update(result)

            # Generate a friendly response string for the UI
            if result.get("has_budget"):
                plan = result["plan"]
                status = result["status"]
                summary_lines = [f"📊 Your {plan['period']} budget: ${plan['total_budget']}",
                                 f"Savings goal: ${plan['savings_goal']}",
                                 "\nCategory breakdown:"]
                for cat, info in status["by_category"].items():
                    summary_lines.append(
                        f"- {cat}: Budgeted ${info['budgeted']}, Spent ${info['actual']}, Remaining ${info['remaining']} ({info['percent_used']}%)"
                    )
                overall = status.get("overall", {})
                summary_lines.append(
                    f"\nOverall: Spent ${overall.get('actual',0)}, Remaining ${overall.get('remaining',0)} ({overall.get('percent_used',0)}%)"
                )
                response_payload["response"] = "\n".join(summary_lines)
            else:
                response_payload["response"] = result.get("message", "No active budget plan.")

        elif intent == "budget_refine":
            if not original_proposal:
                response_payload.update({
                    "response": "Missing original budget proposal to refine.",
                    "success": False
                })
            else:
                result = planner.refine_budget(original_proposal, message, db)
                response_payload.update(result)
                # Provide fallback response
                if "response" not in response_payload:
                    response_payload["response"] = "I tried to refine your budget but ran into an issue."

        else:
            # Default: chat
            result = chatbot.chat(message, db, history)
            response_payload.update(result)
            if "response" not in response_payload:
                response_payload["response"] = "I didn't understand that, could you clarify?"

    except Exception as e:
        response_payload.update({
            "response": f"Error processing message: {str(e)}",
            "type": "error"
        })

    print(f"Response payload: {response_payload}")
    return response_payload
