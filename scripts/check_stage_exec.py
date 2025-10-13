"""Check pipeline stage execution schema and data"""
import asyncio
import asyncpg

async def check():
    conn = await asyncpg.connect(
        host='localhost',
        port=5432,
        user='postgres',
        password='postgres',
        database='cognito-engine'
    )

    # Get the row
    row = await conn.fetchrow(
        "SELECT * FROM pipeline_stage_executions WHERE id = $1",
        '517a7cf8-2eda-4b9e-9284-27a41b4c935a'
    )

    if row:
        print("Columns in pipeline_stage_executions:")
        for key in row.keys():
            print(f"  - {key}: {row[key]}")
    else:
        print("No record found")

    await conn.close()

asyncio.run(check())
