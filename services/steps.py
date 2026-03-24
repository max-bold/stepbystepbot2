from .db import DelayType, Step, StepChain, StepType, MessageType
from .utils import engine
from sqlmodel import Session


async def add_step(
    chain_id: int,
    step_type: StepType = StepType.NORMAL,
    name: str | None = None,
    description: str | None = None,
) -> int:
    with Session(engine) as session:
        chain = session.get(StepChain, chain_id)
        if chain is None:
            raise ValueError("No such chain")
        step_count = len(chain.steps)
        step = Step(
            chain_id=chain_id,
            step_number=step_count,
            step_type=step_type,
            name=name,
            description=description,
        )
        session.add(step)
        session.commit()
        session.refresh(step)
        if step.id is None:
            raise ValueError("Failed to create step")
        return step.id


async def setup_confirmation(step_id: int, prompt: str, btn_text: str):
    with Session(engine) as session:
        step = session.get(Step, step_id)
        if step is None:
            raise ValueError("No such step")
        step.confirm_before = True
        step.confirm_prompt = prompt
        step.confirm_btn_text = btn_text
        session.add(step)
        session.commit()


async def setup_delay(
    step_id: int,
    delay_type: DelayType,
    delay_value: int,
):
    with Session(engine) as session:
        step = session.get(Step, step_id)
        if step is None:
            raise ValueError("No such step")
        step.delay_type = delay_type
        step.delay_value = delay_value
        session.add(step)
        session.commit()
