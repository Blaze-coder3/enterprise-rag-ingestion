import asyncio
import os
import sys

# Ensure project root is in pythonpath
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import httpx

async def main():
    print("Seeding demo data...")
    async with httpx.AsyncClient() as client:
        # Create some dummy files to upload
        doc1_content = b"This is a benefit summary. The deductible is $500. Copay is $20."
        doc2_content = b"This is clinical protocol 101. Standard procedure requires MRI for head trauma."
        
        # Upload doc 1
        res = await client.post(
            "http://localhost:8000/v1/ingest",
            data={"tenant_id": "tenant-acme"},
            files={"file": ("benefit_summary.txt", doc1_content, "text/plain")}
        )
        print(f"Doc 1 upload: {res.status_code}")
        
        # Upload doc 2
        res = await client.post(
            "http://localhost:8000/v1/ingest",
            data={"tenant_id": "tenant-medcorp"},
            files={"file": ("clinical_protocol.txt", doc2_content, "text/plain")}
        )
        print(f"Doc 2 upload: {res.status_code}")
        
        print("Demo seed complete!")

if __name__ == "__main__":
    asyncio.run(main())
