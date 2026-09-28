from fastapi import FastAPI

from field_review_route import router

app = FastAPI(title="Field Service Dispatch Review")
app.include_router(router)
