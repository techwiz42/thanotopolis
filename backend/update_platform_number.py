import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import update
from sqlalchemy.future import select
from app.models.models import TelephonyConfiguration

async def update_platform_number():
    engine = create_async_engine('postgresql+asyncpg://postgres:postgres@localhost:5432/thanotopolis')
    async_session = sessionmaker(engine, class_=AsyncSession)
    
    actual_twilio_number = '+18884374952'  # From the Twilio account
    
    async with async_session() as session:
        result = await session.execute(select(TelephonyConfiguration))
        config = result.scalar_one_or_none()
        
        if config:
            print(f'Current platform number: {config.platform_phone_number}')
            print(f'Actual Twilio number: {actual_twilio_number}')
            
            if config.platform_phone_number != actual_twilio_number:
                await session.execute(
                    update(TelephonyConfiguration)
                    .values(platform_phone_number=actual_twilio_number)
                )
                await session.commit()
                print('✅ Updated platform number to match Twilio number')
                
                # Also update forwarding instructions
                from app.services.telephony_service import telephony_service
                new_instructions = telephony_service._generate_forwarding_instructions(actual_twilio_number)
                
                await session.execute(
                    update(TelephonyConfiguration)
                    .values(forwarding_instructions=new_instructions)
                )
                await session.commit()
                print('✅ Updated forwarding instructions')
            else:
                print('✅ Platform number already matches Twilio number')
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(update_platform_number())