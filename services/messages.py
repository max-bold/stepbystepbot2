from .db import StepMessage, Step, MessageType
from .utils import engine
from sqlmodel import Session


async def add_message(
    step_id: int,
    content: str | None = None,
    caption: str | None = None,
    message_type: MessageType = MessageType.TEXT,
    tg_file_id: str | None = None,
    max_file_id: str | None = None,
    local_file_id: str | None = None,
) -> int:
    with Session(engine) as session:
        step = session.get(Step, step_id)
        if step is None:
            raise ValueError("No such step")
        message_count = len(step.messages)
        message = StepMessage(
            step_id=step_id,
            message_number=message_count,
            content=content,
            caption=caption,
            message_type=message_type,
            tg_file_id=tg_file_id,
            max_file_id=max_file_id,
            local_file_id=local_file_id,
        )
        session.add(message)
        session.commit()
        session.refresh(message)
        if message.id is None:
            raise ValueError("Failed to create message")
        return message.id
