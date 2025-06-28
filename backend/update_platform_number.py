import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import update
from sqlalchemy.future import select
from app.models.models import TelephonyConfiguration

async def update_platform_number():
    engine = create_async_engine('postgresql+asyncpg://postgres:postgres@localhost:5432/thanotopolis')
    async_session = sessionmaker(engine, class_=AsyncSession)
    
    actual_twilio_number = '+14243584857'  # Your newly purchased Twilio number
    
    async with async_session() as session:
        result = await session.execute(select(TelephonyConfiguration))
        configs = result.scalars().all()
        
        if not configs:
            print('No telephony configurations found')
            return
            
        print(f'Found {len(configs)} telephony configurations')
        print()
        
        for i, config in enumerate(configs, 1):
            print(f'Configuration {i}:')
            print(f'  Tenant ID: {config.tenant_id}')
            print(f'  Organization phone: {config.organization_phone_number}')
            print(f'  Current platform number: {config.platform_phone_number}')
            print(f'  Target Twilio number: {actual_twilio_number}')
            
            if config.platform_phone_number != actual_twilio_number:
                await session.execute(
                    update(TelephonyConfiguration)
                    .where(TelephonyConfiguration.id == config.id)
                    .values(platform_phone_number=actual_twilio_number)
                )
                print('  ✅ Updated platform number to match Twilio number')
            else:
                print('  ✅ Platform number already matches Twilio number')
            print()
        
        await session.commit()
        print('All updates completed!')
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(update_platform_number())