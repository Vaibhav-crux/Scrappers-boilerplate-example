import asyncio
from fastapi import APIRouter
from config.loggers import logger
from . import (
    forbes, 
    ambCrypto, 
    blockWorks, 
    coinDesk, 
    coinGape, 
    coinTelegraph, 
    cryptoPotato, 
    watcherGuru, 
    beInCrypto, 
    theDefiant
)

router = APIRouter()

@router.get("/runAllEndpoints")
async def run_all_endpoints():
    # Create a list of tasks for concurrent execution
    tasks = [
        watcherGuru.watcher_guru_scrapped(),
        forbes.forbes_scrapped(),
        ambCrypto.ambcrypto_scrapped(),
        blockWorks.block_works_scrapped(),
        coinDesk.coin_desk_scrapped(),
        coinGape.coin_gape_scrapped(),
        coinTelegraph.coin_telegraph_scrapped(),
        cryptoPotato.crypto_potato_scrapped(),
        beInCrypto.bein_crypto_scrapped(),
        theDefiant.the_defiant_scrapped()
    ]

    try:
        # Run all tasks concurrently and flatten the results
        results = await asyncio.gather(*tasks)
        
        # Flatten the list of lists into a single list
        all_articles = [article for sublist in results for article in sublist]
        
        logger.info("All endpoints executed successfully")

        # Return results in a single flattened array
        return all_articles

    except Exception as e:
        logger.error(f"Error executing endpoints: {e}")
        return {"status": "Failed", "error": str(e)}
