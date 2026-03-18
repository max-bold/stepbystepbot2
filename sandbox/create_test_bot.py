from dotenv import load_dotenv
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from services.user import create_user
from services.bot import create_bot, get_default_chain
from services.db import PaymentMethod, create_tables
from services.steps import (
    add_step,
    StepType,
    setup_confirmation,
    DelayType,
    setup_delay,
)
from services.messages import add_message, MessageType
from services.payments import add_payment_method, PaymentMethodType, setup_payment

load_dotenv()
TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
MAX_BOT_TOKEN = os.getenv("MAX_BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL is None:
    raise ValueError("DATABASE_URL environment variable not set")
YOO_STORE_ID = os.getenv("STORE_ID")
YOO_API_KEY = os.getenv("YKASSA_API_KEY")


async def main():

    create_tables()

    user_id = await create_user(
        username="testuser",
        password="testpassword",
        first_name="Test",
        last_name="User",
        e_mail="testuser@example.com",
    )

    bot_id = await create_bot(
        name="Test Bot",
        description="A bot for testing purposes",
        tg_token=TG_BOT_TOKEN,
        max_token=MAX_BOT_TOKEN,
        owner_id=user_id,
    )

    chain_id = await get_default_chain(bot_id)

    # Step 1: Welcome Step

    step_id = await add_step(
        chain_id=chain_id,
        name="Welcome Step",
        description="The first step of the bot",
    )

    await add_message(
        step_id=step_id,
        content="Welcome to the bot!",
        caption="This is the first message",
    )

    # Step 2: Ask for payment

    step_id = await add_step(
        chain_id=chain_id, name="Payment Step", description="Step to ask for payment"
    )

    await setup_confirmation(
        step_id=step_id,
        prompt="Are you sure you want to proceed with the payment?",
        btn_text="Confirm Payment",
    )

    if YOO_STORE_ID and YOO_API_KEY:
        await add_payment_method(
            bot_id=bot_id,
            method=PaymentMethodType.YOOKASSA,
            api_key=YOO_API_KEY,
            store_id=YOO_STORE_ID,
        )

    await setup_payment(
        step_id=step_id,
        prompt="Please proceed with the payment of $100 to access the next steps.",
        details={"amount": 100, "currency": "USD"},
    )

    # Step 3: First Step

    step_id = await add_step(
        chain_id=chain_id,
        name="First Step",
        description="The first step after payment",
    )

    await setup_confirmation(
        step_id=step_id,
        prompt="You have completed the payment! Click the button below to proceed.",
        btn_text="Go to First Step",
    )

    await add_message(
        step_id=step_id,
        content="This is the first step after payment. Congratulations!",
    )

    await add_message(
        step_id=step_id,
        message_type=MessageType.IMAGE,
        local_file_id="img1",
        caption="This is a photo message",
    )

    await setup_delay(
        step_id=step_id,
        delay_type=DelayType.PERIOD,
        delay_value=30,
    )

    # Step 4: Final Step

    step_id = await add_step(
        chain_id=chain_id,
        name="Final Step",
        description="The final step of the bot",
    )

    await add_message(
        step_id=step_id,
        content="This is the final step of the bot. Thank you for participating!",
    )


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
