from fastapi import FastAPI
from config.loggers import logger
from routers import (
    test, 
    forbes, 
    ambCrypto, 
    blockWorks, 
    coinDesk, 
    coinGape, 
    coinTelegraph, 
    cryptoPotato, 
    watcherGuru, 
    beInCrypto, 
    theDefiant,
    all_endpoints   # Import the new router
)

app = FastAPI()

# Include all routers
app.include_router(test.router)
app.include_router(forbes.router)
app.include_router(ambCrypto.router)
app.include_router(watcherGuru.router)
app.include_router(blockWorks.router)
app.include_router(coinDesk.router)
app.include_router(coinGape.router)
app.include_router(coinTelegraph.router)
app.include_router(cryptoPotato.router)
app.include_router(beInCrypto.router)
app.include_router(theDefiant.router)
app.include_router(all_endpoints.router)

# Define the startup event function
@app.on_event("startup")
async def startup_event():
    logger.info("FastAPI application started successfully")

    # If you had a database connection here, ensure it's removed
    # e.g., connect to database, initialize caches, etc.

# Example of logging in the main application
logger.info("FastAPI application setup complete")
