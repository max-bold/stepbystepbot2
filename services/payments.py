from .db import Bot, PaymentMethod, PaymentMethodType, Step, StepType
from .utils import engine
from sqlmodel import Session


async def add_payment_method(
    bot_id: int,
    method: PaymentMethodType,
    api_key: str,
    store_id: str,
) -> int:
    with Session(engine) as session:
        payment_method = PaymentMethod(
            method=method,
            api_key=api_key,
            store_id=store_id,
            bot_id=bot_id,
        )
        session.add(payment_method)
        session.commit()
        session.refresh(payment_method)
        if payment_method.id is None:
            raise ValueError("Failed to create payment method")
        return payment_method.id

async def setup_payment(
    step_id: int,
    prompt: str | None,
    details: dict
):
    with Session(engine) as session:
        step = session.get(Step, step_id)
        if step is None:
            raise ValueError("No such step")
        step.payment_details = details
        step.payment_prompt = prompt
        step.step_type = StepType.PAYMENT
        session.add(step)
        session.commit()