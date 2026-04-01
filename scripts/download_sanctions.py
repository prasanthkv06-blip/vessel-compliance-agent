"""Download latest sanctions lists from public sources.

Run this script periodically (daily/weekly) to keep sanctions data current.

Sources:
- OFAC SDN List: https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/SDN_ADVANCED.XML
- EU Consolidated List: https://webgate.ec.europa.eu/fsd/fsf/public/files/xmlFullSanctionsList_1_1/content
- UK Sanctions List: https://assets.publishing.service.gov.uk/media/UK_Sanctions_List.csv
"""
import os
import httpx
import asyncio
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data" / "sanctions"

SOURCES = {
    "ofac_sdn.xml": "https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/SDN_ADVANCED.XML",
    "eu_consolidated.xml": "https://webgate.ec.europa.eu/fsd/fsf/public/files/xmlFullSanctionsList_1_1/content?token=dG9rZW4tMjAxNw",
    "uk_sanctions.csv": "https://assets.publishing.service.gov.uk/media/UK_Sanctions_List.csv",
}


async def download_file(client: httpx.AsyncClient, filename: str, url: str):
    """Download a single sanctions list file."""
    filepath = DATA_DIR / filename
    print(f"Downloading {filename}...")
    try:
        response = await client.get(url, follow_redirects=True, timeout=60.0)
        if response.status_code == 200:
            filepath.write_bytes(response.content)
            size_kb = len(response.content) / 1024
            print(f"  ✓ {filename} ({size_kb:.0f} KB)")
        else:
            print(f"  ✗ {filename} - HTTP {response.status_code}")
    except Exception as e:
        print(f"  ✗ {filename} - {e}")


async def main():
    """Download all sanctions lists."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    print("=== Sanctions List Downloader ===\n")

    async with httpx.AsyncClient() as client:
        tasks = [download_file(client, name, url) for name, url in SOURCES.items()]
        await asyncio.gather(*tasks)

    print("\nDone. Files saved to:", DATA_DIR)


if __name__ == "__main__":
    asyncio.run(main())
