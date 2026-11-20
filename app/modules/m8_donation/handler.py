from fastapi import APIRouter, Body

from app.errors import object_payload
from app.modules.m8_donation import service, store

router = APIRouter()


@router.get("/api/8")
def overview():
    return service.overview()


@router.post("/api/8/libraries")
def register_library(payload: object = Body(...)):
    return service.register_library(object_payload(payload))


@router.get("/api/8/libraries")
def libraries():
    return {"rows": store.list_libraries()}


@router.post("/api/8/donations")
def register_donation(payload: object = Body(...)):
    return service.register_donation(object_payload(payload))


@router.get("/api/8/donations")
def donations():
    return {"rows": store.list_donations()}


@router.get("/api/8/donations/{ident}")
def donation(ident: str):
    return store.donation(ident)


@router.post("/api/8/claims")
def claim(payload: object = Body(...)):
    return service.claim(object_payload(payload))


@router.post("/api/8/review")
def review(payload: object = Body(...)):
    return service.confirm(object_payload(payload))


@router.post("/api/8/arrive")
def arrive(payload: object = Body(...)):
    return service.arrive(object_payload(payload))
